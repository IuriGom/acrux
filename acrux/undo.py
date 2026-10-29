"""Exact journaled batch restoration."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from acrux.memory.journal import MutationJournal, sanitize_row
from acrux.memory.locks import project_write_lock


class UndoError(RuntimeError):
    pass


class UndoConflictError(UndoError):
    pass


@dataclass
class UndoResult:
    batch_id: str
    restored_entries: int


class UndoCoordinator:
    _TABLES: ClassVar[set[str]] = {
        "facts",
        "pending_facts",
        "fact_embeddings",
        "fact_versions",
        "episodes",
        "skills",
        "pending_skills",
    }
    _DATABASES: ClassVar[set[str]] = {"episodes.db", "semantic.db", "skills.db"}

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.journal = MutationJournal(project_dir)

    def undo(self, batch_id: str | None = None, last: bool = False) -> UndoResult:
        if last:
            batch = self.journal.latest()
        elif batch_id:
            batch = self.journal.get(batch_id)
        else:
            raise UndoError("Provide a batch ID or --last")
        if batch is None:
            raise UndoError("Batch not found or already undone")
        if batch.undone:
            raise UndoError(f"Batch {batch.id} is already undone")

        with project_write_lock(self.project_dir):
            entries = self.journal.entries(batch.id)
            prepared = [self._prepare(entry) for entry in entries]
            conflicts = [entry for entry in prepared if entry["conflict"]]
            if conflicts:
                keys = ", ".join(str(entry["key"]) for entry in conflicts)
                raise UndoConflictError(f"Batch {batch.id} has later changes: {keys}")

            affected = sorted({entry["store_path"] for entry in prepared})
            with tempfile.TemporaryDirectory(prefix="acrux-undo-") as temporary:
                safety = Path(temporary)
                try:
                    for store_path in affected:
                        self._backup_database(Path(store_path), safety / Path(store_path).name)
                    for entry in reversed(prepared):
                        self._restore_entry(entry)
                    for store_path in affected:
                        self._rebuild_fts(Path(store_path))
                    for store_path in affected:
                        path = Path(store_path)
                        if path.name == "semantic.db":
                            vector_path = path.with_suffix(path.suffix + ".vec")
                            vector_path.unlink(missing_ok=True)
                            vector_path.with_suffix(vector_path.suffix + ".meta").unlink(missing_ok=True)
                except Exception:
                    for store_path in affected:
                        backup = safety / Path(store_path).name
                        if backup.exists():
                            self._backup_database(backup, Path(store_path))
                    raise
            self.journal.mark_undone(batch.id)
            self.journal.record_undo(batch.id, len(entries))
            return UndoResult(batch.id, len(entries))

    def _prepare(self, entry: dict) -> dict:
        table = entry["table_name"]
        store_path = Path(entry["store_path"])
        if table not in self._TABLES or store_path.name not in self._DATABASES:
            raise UndoError("Journal contains an unsupported restore target")
        if store_path.resolve().parent != self.project_dir.resolve():
            raise UndoError("Journal restore target escapes the project")
        key = json.loads(entry["key_json"])
        before = json.loads(entry["before_json"]) if entry["before_json"] is not None else None
        after = json.loads(entry["after_json"]) if entry["after_json"] is not None else None
        current = self._row(store_path, table, entry["key_column"], key)
        raw_current = self._row(store_path, table, entry["key_column"], key, sanitize=False)
        conflict = bool(entry["after_recorded"]) and current != after and current != before
        return {
            **entry,
            "key": key,
            "before": before,
            "after": after,
            "current": current,
            "raw_current": raw_current,
            "conflict": conflict,
        }

    @staticmethod
    def _row(store_path: Path, table: str, key_column: str, key, sanitize: bool = True):
        with sqlite3.connect(store_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                f"SELECT * FROM {table} WHERE {key_column} = ?", (key,)
            ).fetchone()
            if not row:
                return None
            return sanitize_row(table, dict(row)) if sanitize else dict(row)

    @staticmethod
    def _backup_database(source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
            src.backup(dst)

    def _restore_entry(self, entry: dict) -> None:
        store_path = Path(entry["store_path"])
        table = entry["table_name"]
        key_column = entry["key_column"]
        with sqlite3.connect(store_path) as conn:
            if entry["before"] is None:
                conn.execute(f"DELETE FROM {table} WHERE {key_column} = ?", (entry["key"],))
            else:
                before = dict(entry["before"])
                if table == "facts" and entry["raw_current"] is not None:
                    for column in ("recall_count", "last_recalled_at"):
                        if column in entry["raw_current"]:
                            before[column] = entry["raw_current"][column]
                columns = list(before)
                placeholders = ", ".join("?" for _ in columns)
                conn.execute(
                    f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                    [before[column] for column in columns],
                )
            conn.commit()

    @staticmethod
    def _rebuild_fts(store_path: Path) -> None:
        with sqlite3.connect(store_path) as conn:
            if store_path.name == "episodes.db":
                conn.execute("INSERT INTO episodes_fts(episodes_fts) VALUES ('rebuild')")
            elif store_path.name == "skills.db":
                conn.execute("INSERT INTO skills_fts(skills_fts) VALUES ('rebuild')")
            elif store_path.name == "semantic.db":
                conn.execute("INSERT INTO facts_fts(facts_fts) VALUES ('rebuild')")
            conn.commit()
