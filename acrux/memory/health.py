"""Health mixin: health checks and storage checksums."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from acrux.utils import utcnow


class HealthStoreMixin:
    """Health checks and storage-integrity checksums.

    Expects the host class to provide ``db_path`` and a ``_connect()``
    method (see SemanticStore).
    """

    # ------------------------------------------------------------------
    # Health checks
    # ------------------------------------------------------------------

    def add_health_check(self, check: dict[str, Any]) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO health_checks (project, check_type, severity, message, created_at, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    check.get("project"),
                    check.get("check_type"),
                    check.get("severity"),
                    check.get("message"),
                    utcnow().isoformat(),
                    check.get("resolved_at"),
                ),
            )
            conn.commit()
            return cur.lastrowid

    def get_health_checks(
        self,
        project: str | None = None,
        check_type: str | None = None,
        severity: str | None = None,
        unresolved_only: bool = False,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        base = "SELECT * FROM health_checks WHERE 1=1"
        params: list[Any] = []
        if project is not None:
            base += " AND project = ?"
            params.append(project)
        if check_type:
            base += " AND check_type = ?"
            params.append(check_type)
        if severity:
            base += " AND severity = ?"
            params.append(severity)
        if unresolved_only:
            base += " AND resolved_at IS NULL"
        base += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(base, params).fetchall()
        return [dict(row) for row in rows]

    def resolve_health_checks(
        self, project: str | None = None, check_type: str | None = None
    ) -> int:
        base = "UPDATE health_checks SET resolved_at = ? WHERE resolved_at IS NULL"
        params: list[Any] = [utcnow().isoformat()]
        if project is not None:
            base += " AND project = ?"
            params.append(project)
        if check_type:
            base += " AND check_type = ?"
            params.append(check_type)
        with self._connect() as conn:
            cur = conn.execute(base, params)
            conn.commit()
            return cur.rowcount

    # ------------------------------------------------------------------
    # Storage checksums (global scope)
    # ------------------------------------------------------------------

    def set_storage_checksum(self, file_path: str, checksum: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO storage_checksums (file_path, checksum, checked_at)
                VALUES (?, ?, ?)
                """,
                (file_path, checksum, utcnow().isoformat()),
            )
            conn.commit()

    def get_storage_checksums(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM storage_checksums ORDER BY file_path").fetchall()
        return [dict(row) for row in rows]

    def verify_storage_checksums(self, data_dir: Path) -> dict[str, Any]:
        mismatches = []
        missing = []
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT file_path, checksum FROM storage_checksums").fetchall()
        for row in rows:
            full = data_dir / row["file_path"]
            if not full.exists():
                missing.append(row["file_path"])
                continue
            current = self._file_checksum(full)
            if current != row["checksum"]:
                mismatches.append(
                    {"file_path": row["file_path"], "expected": row["checksum"], "actual": current}
                )
        return {"ok": not mismatches and not missing, "mismatches": mismatches, "missing": missing}

    @staticmethod
    def _file_checksum(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
