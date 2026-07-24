"""Artifacts mixin: tests, reviews, dependencies, file summaries, watcher state.

Also hosts other auxiliary per-project records (chat pins, system prompts).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any


class ArtifactsStoreMixin:
    """Test results, code reviews, dependencies, file summaries, watcher state.

    Expects the host class to provide ``db_path`` and a ``_connect()``
    method (see SemanticStore).
    """

    # ------------------------------------------------------------------
    # Dependencies
    # ------------------------------------------------------------------

    def add_dependencies(self, project: str, deps: list[dict[str, Any]]) -> int:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            for dep in deps:
                conn.execute(
                    """
                    INSERT INTO dependencies
                    (project, source_ref, source_type, target_ref, target_type, dependency_type, detected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project,
                        dep.get("source_ref"),
                        dep.get("source_type"),
                        dep.get("target_ref"),
                        dep.get("target_type"),
                        dep.get("dependency_type"),
                        now,
                    ),
                )
            conn.commit()
        return len(deps)

    def get_dependencies(
        self,
        project: str,
        source: str | None = None,
        target: str | None = None,
        source_type: str | None = None,
        target_type: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        base = "SELECT * FROM dependencies WHERE project = ?"
        params: list[Any] = [project]
        if source:
            base += " AND source_ref = ?"
            params.append(source)
        if target:
            base += " AND target_ref = ?"
            params.append(target)
        if source_type:
            base += " AND source_type = ?"
            params.append(source_type)
        if target_type:
            base += " AND target_type = ?"
            params.append(target_type)
        base += " ORDER BY detected_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(base, params).fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Code reviews
    # ------------------------------------------------------------------

    def add_review(self, project: str, review: dict[str, Any]) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO code_reviews (project, file_path, line_range, comment, resolution, reviewer, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project,
                    review.get("file_path"),
                    review.get("line_range"),
                    review.get("comment"),
                    review.get("resolution", "pending"),
                    review.get("reviewer", "user"),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
            return cur.lastrowid

    def get_reviews(
        self,
        project: str,
        file_path: str | None = None,
        resolution: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        base = "SELECT * FROM code_reviews WHERE project = ?"
        params: list[Any] = [project]
        if file_path:
            base += " AND file_path = ?"
            params.append(file_path)
        if resolution:
            base += " AND resolution = ?"
            params.append(resolution)
        base += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(base, params).fetchall()
        return [dict(row) for row in rows]

    def update_review_resolution(self, project: str, review_id: int, resolution: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE code_reviews SET resolution = ? WHERE id = ? AND project = ?",
                (resolution, review_id, project),
            )
            conn.commit()
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Test results
    # ------------------------------------------------------------------

    def add_test_result(self, project: str, result: dict[str, Any]) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO test_results
                (project, test_name, file_path, passed, output, duration_ms, root_cause, run_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project,
                    result.get("test_name"),
                    result.get("file_path"),
                    1 if result.get("passed") else 0,
                    result.get("output", ""),
                    result.get("duration_ms", 0),
                    result.get("root_cause"),
                    result.get("run_at") or datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
            return cur.lastrowid

    def get_test_results(
        self,
        project: str,
        passed: bool | None = None,
        file_path: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        base = "SELECT * FROM test_results WHERE project = ?"
        params: list[Any] = [project]
        if passed is not None:
            base += " AND passed = ?"
            params.append(1 if passed else 0)
        if file_path:
            base += " AND file_path = ?"
            params.append(file_path)
        base += " ORDER BY run_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(base, params).fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # File summaries
    # ------------------------------------------------------------------

    def add_file_summary(self, project: str, summary: dict[str, Any]) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT OR REPLACE INTO file_summaries
                (project, path, summary, content_hash, last_modified, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    project,
                    summary.get("path"),
                    summary.get("summary"),
                    summary.get("content_hash"),
                    summary.get("last_modified"),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
            return cur.lastrowid

    def get_file_summaries(
        self, project: str, path: str | None = None, limit: int = 500
    ) -> list[dict[str, Any]]:
        base = "SELECT * FROM file_summaries WHERE project = ?"
        params: list[Any] = [project]
        if path:
            base += " AND path = ?"
            params.append(path)
        base += " ORDER BY indexed_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(base, params).fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Watcher state
    # ------------------------------------------------------------------

    def get_watcher_state(self, project: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM workspace_watcher_state WHERE project = ? ORDER BY path",
                (project,),
            ).fetchall()
        return [dict(row) for row in rows]

    def set_watcher_state(
        self, project: str, path: str, mtime: str, file_hash: str, diff: str | None = None
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO workspace_watcher_state
                (project, path, last_seen_mtime, last_seen_hash, last_diff)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project, path, mtime, file_hash, diff),
            )
            conn.commit()

    def clear_watcher_state(self, project: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM workspace_watcher_state WHERE project = ?", (project,))
            conn.commit()

    # ------------------------------------------------------------------
    # Chat pins (global scope)
    # ------------------------------------------------------------------

    def add_chat_pin(self, chat_id: str, message_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO chat_pins (chat_id, message_id, created_at) VALUES (?, ?, ?)",
                (chat_id, message_id, datetime.utcnow().isoformat()),
            )
            conn.commit()

    def remove_chat_pin(self, chat_id: str, message_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM chat_pins WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def get_chat_pins(self, chat_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM chat_pins WHERE chat_id = ? ORDER BY created_at",
                (chat_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Project system prompts
    # ------------------------------------------------------------------

    def set_system_prompt(self, project: str, prompt_text: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO project_system_prompts (project, prompt_text, updated_at)
                VALUES (?, ?, ?)
                """,
                (project, prompt_text, datetime.utcnow().isoformat()),
            )
            conn.commit()

    def get_system_prompt(self, project: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM project_system_prompts WHERE project = ?",
                (project,),
            ).fetchone()
        if not row:
            return None
        row = dict(row)
        return {
            "project": row.get("project"),
            "promptText": row.get("prompt_text"),
            "updatedAt": row.get("updated_at"),
        }
