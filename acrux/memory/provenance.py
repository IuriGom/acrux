"""Code-change provenance storage."""

from __future__ import annotations

import sqlite3

from acrux.models import CodeChange


class ProvenanceStoreMixin:
    def _init_code_changes(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS code_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT NOT NULL,
                session_id TEXT,
                commit_sha TEXT,
                file_path TEXT NOT NULL,
                change_type TEXT NOT NULL,
                diff TEXT,
                truncated INTEGER DEFAULT 0,
                source TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                content_hash TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_code_changes_session ON code_changes(project, session_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_code_changes_commit ON code_changes(project, commit_sha)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_code_changes_path ON code_changes(project, file_path)"
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_code_changes_identity
            ON code_changes(project, IFNULL(commit_sha, ''), file_path, content_hash)
            """
        )

    def add_code_change(self, change: CodeChange) -> int:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO code_changes
                (project, session_id, commit_sha, file_path, change_type, diff,
                 truncated, source, timestamp, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    change.project,
                    change.session_id,
                    change.commit_sha,
                    change.file_path,
                    change.change_type,
                    change.diff,
                    int(change.truncated),
                    change.source,
                    change.timestamp,
                    change.content_hash,
                ),
            )
            row = conn.execute(
                """
                SELECT id FROM code_changes
                WHERE project = ? AND IFNULL(commit_sha, '') = IFNULL(?, '')
                  AND file_path = ? AND content_hash = ?
                """,
                (change.project, change.commit_sha, change.file_path, change.content_hash),
            ).fetchone()
            conn.commit()
            return int(row[0])

    def list_code_changes(
        self,
        project: str,
        session_id: str | None = None,
        commit_sha: str | None = None,
        file_path: str | None = None,
        limit: int = 100,
    ) -> list[CodeChange]:
        clauses = ["project = ?"]
        params = [project]
        for column, value in (
            ("session_id", session_id),
            ("commit_sha", commit_sha),
            ("file_path", file_path),
        ):
            if value is not None:
                clauses.append(f"{column} = ?")
                params.append(value)
        params.append(limit)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""
                SELECT * FROM code_changes
                WHERE {' AND '.join(clauses)}
                ORDER BY timestamp DESC, id DESC LIMIT ?
                """,
                params,
            ).fetchall()
        return [
            CodeChange(
                project=row["project"],
                session_id=row["session_id"] or "",
                commit_sha=row["commit_sha"],
                file_path=row["file_path"],
                change_type=row["change_type"],
                diff=row["diff"] or "",
                truncated=bool(row["truncated"]),
                source=row["source"],
                timestamp=row["timestamp"],
                content_hash=row["content_hash"],
            )
            for row in rows
        ]
