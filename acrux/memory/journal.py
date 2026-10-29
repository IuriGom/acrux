"""Durable mutation batches and recovery images."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from acrux.memory.locks import project_write_lock
from acrux.utils import utcnow


@dataclass
class BatchInfo:
    id: str
    project: str
    operation: str
    created_at: str
    completed: bool
    undone: bool
    undone_at: str | None
    last_sequence: int


class IncompleteBatchError(RuntimeError):
    pass


class MutationJournal:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = project_dir / "journal.db"
        self.project = project_dir.name
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mutation_batches (
                    id TEXT PRIMARY KEY,
                    project TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed INTEGER DEFAULT 0,
                    undone INTEGER DEFAULT 0,
                    undone_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mutation_entries (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT NOT NULL,
                    store_path TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    key_column TEXT NOT NULL,
                    key_json TEXT NOT NULL,
                    before_json TEXT,
                    after_json TEXT,
                    after_recorded INTEGER DEFAULT 0
                )
                """
            )
            entry_columns = {row[1] for row in conn.execute("PRAGMA table_info(mutation_entries)")}
            if "after_recorded" not in entry_columns:
                conn.execute("ALTER TABLE mutation_entries ADD COLUMN after_recorded INTEGER DEFAULT 0")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mutation_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT NOT NULL,
                    restored_entries INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mutation_entries_batch ON mutation_entries(batch_id, sequence)"
            )
            conn.commit()

    def begin(self, operation: str) -> str:
        batch_id = uuid.uuid4().hex
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO mutation_batches (id, project, operation, created_at) VALUES (?, ?, ?, ?)",
                (batch_id, self.project, operation, utcnow().isoformat()),
            )
            conn.commit()
        return batch_id

    def record_before(
        self,
        batch_id: str,
        store_path: Path,
        table_name: str,
        key_column: str,
        key: Any,
        before: dict[str, Any] | None,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO mutation_entries
                (batch_id, store_path, table_name, key_column, key_json, before_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    batch_id,
                    str(store_path),
                    table_name,
                    key_column,
                    json.dumps(key),
                    json.dumps(before) if before is not None else None,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def record_after(self, sequence: int, after: dict[str, Any] | None) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE mutation_entries SET after_json = ?, after_recorded = 1 WHERE sequence = ?",
                (json.dumps(after) if after is not None else None, sequence),
            )
            conn.commit()

    def complete(self, batch_id: str) -> None:
        with self._connect() as conn:
            missing = conn.execute(
                "SELECT COUNT(*) FROM mutation_entries WHERE batch_id = ? AND after_recorded = 0",
                (batch_id,),
            ).fetchone()[0]
            if missing:
                raise IncompleteBatchError(f"Batch {batch_id} has {missing} entries without after-images")
            conn.execute("UPDATE mutation_batches SET completed = 1 WHERE id = ?", (batch_id,))
            conn.commit()

    def _batch_info(self, conn, row) -> BatchInfo:
        last_sequence = conn.execute(
            "SELECT COALESCE(MAX(sequence), 0) FROM mutation_entries WHERE batch_id = ?",
            (row["id"],),
        ).fetchone()[0]
        return BatchInfo(
            id=row["id"],
            project=row["project"],
            operation=row["operation"],
            created_at=row["created_at"],
            completed=bool(row["completed"]),
            undone=bool(row["undone"]),
            undone_at=row["undone_at"],
            last_sequence=last_sequence,
        )

    def incomplete(self) -> list[BatchInfo]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM mutation_batches WHERE completed = 0 AND undone = 0 ORDER BY created_at"
            ).fetchall()
            return [self._batch_info(conn, row) for row in rows]

    def latest(self) -> BatchInfo | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM mutation_batches WHERE completed = 1 AND undone = 0 ORDER BY created_at DESC, rowid DESC LIMIT 1"
            ).fetchone()
            return self._batch_info(conn, row) if row else None

    def get(self, batch_id: str) -> BatchInfo | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM mutation_batches WHERE id = ?", (batch_id,)).fetchone()
            return self._batch_info(conn, row) if row else None

    def entries(self, batch_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM mutation_entries WHERE batch_id = ? ORDER BY sequence",
                (batch_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def mark_undone(self, batch_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE mutation_batches SET undone = 1, undone_at = ? WHERE id = ?",
                (utcnow().isoformat(), batch_id),
            )
            conn.commit()

    def record_undo(self, batch_id: str, restored_entries: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO mutation_audit (batch_id, restored_entries, created_at) VALUES (?, ?, ?)",
                (batch_id, restored_entries, utcnow().isoformat()),
            )
            conn.commit()


class MutationBatch:
    def __init__(self, project_dir: Path, operation: str):
        self.project_dir = project_dir
        self.operation = operation
        self.journal = MutationJournal(project_dir)
        self.id: str | None = None
        self._lock = None

    def __enter__(self):
        self._lock = project_write_lock(self.project_dir)
        self._lock.__enter__()
        try:
            incomplete = self.journal.incomplete()
            if incomplete:
                batch = incomplete[0]
                raise IncompleteBatchError(
                    f"Incomplete batch {batch.id} for {batch.project}; recover with: "
                    f"acrux undo {batch.id} --project {batch.project}"
                )
            self.id = self.journal.begin(self.operation)
            return self
        except Exception:
            self._lock.__exit__(None, None, None)
            self._lock = None
            raise

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type is None and self.id is not None:
                self.journal.complete(self.id)
        finally:
            if self._lock is not None:
                self._lock.__exit__(exc_type, exc_value, traceback)
                self._lock = None
        return False


class JoinedMutation:
    def __init__(self, journal: MutationJournal, batch_id: str):
        self.journal = journal
        self.batch_id = batch_id

    def __enter__(self):
        return self.journal, self.batch_id

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class ScopedMutation:
    def __init__(self, batch: MutationBatch):
        self.batch = batch

    def __enter__(self):
        self.batch.__enter__()
        return self.batch.journal, self.batch.id

    def __exit__(self, exc_type, exc_value, traceback):
        return self.batch.__exit__(exc_type, exc_value, traceback)


def mutation_scope(store, batch_id: str | None, operation: str):
    if batch_id is not None:
        return JoinedMutation(MutationJournal(store.db_path.parent), batch_id)
    return ScopedMutation(MutationBatch(store.db_path.parent, operation))


def sanitize_row(table_name: str, row: dict[str, Any] | None):
    if row is None:
        return None
    sanitized = dict(row)
    if table_name == "facts":
        sanitized.pop("recall_count", None)
        sanitized.pop("last_recalled_at", None)
    return sanitized


def row_image(conn: sqlite3.Connection, table_name: str, key_column: str, key: Any):
    conn.row_factory = sqlite3.Row
    row = conn.execute(f"SELECT * FROM {table_name} WHERE {key_column} = ?", (key,)).fetchone()
    return sanitize_row(table_name, dict(row) if row else None)


def record_before(store, journal: MutationJournal, batch_id: str, conn, table_name: str, key_column: str, key: Any) -> int:
    before = row_image(conn, table_name, key_column, key)
    return journal.record_before(
        batch_id,
        store.db_path,
        table_name,
        key_column,
        key,
        before,
    )


def record_after(store, journal: MutationJournal, conn, table_name: str, key_column: str, key: Any, sequence: int) -> None:
    after = row_image(conn, table_name, key_column, key)
    journal.record_after(sequence, after)
