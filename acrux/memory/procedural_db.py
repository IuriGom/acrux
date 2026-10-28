"""Procedural memory store backed by SQLite (replaces YAML)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import yaml

from acrux.memory.journal import mutation_scope, record_after, record_before
from acrux.models import Skill


class ProceduralDBStore:
    """SQLite-backed procedural memory store.

    Keeps the same public interface as the old YAML-backed ProceduralStore so
    callers can be switched over without changing logic.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_table()
        self._migrate_yaml()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS skills (
                    id TEXT PRIMARY KEY,
                    project TEXT NOT NULL,
                    name TEXT NOT NULL,
                    preconditions TEXT,
                    procedure TEXT,
                    evidence TEXT,
                    success_rate REAL DEFAULT 0,
                    verified INTEGER DEFAULT 0,
                    tags TEXT,
                    timestamp TEXT,
                    UNIQUE(project, name)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_skills_project ON skills(project)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_skills_verified ON skills(verified)")
            # Migration: add extended capability columns if missing.
            existing = {row[1] for row in conn.execute("PRAGMA table_info(skills)").fetchall()}
            migrations = {
                "parameters": "ALTER TABLE skills ADD COLUMN parameters TEXT",
                "composition": "ALTER TABLE skills ADD COLUMN composition TEXT",
                "precondition_checks": "ALTER TABLE skills ADD COLUMN precondition_checks TEXT",
                "cost": "ALTER TABLE skills ADD COLUMN cost TEXT DEFAULT 'unknown'",
                "risk": "ALTER TABLE skills ADD COLUMN risk TEXT DEFAULT 'unknown'",
            }
            for column, sql in migrations.items():
                if column not in existing:
                    conn.execute(sql)
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(
                    name, preconditions, procedure, tags,
                    content='skills',
                    content_rowid='rowid'
                )
                """
            )

    def _migrate_yaml(self) -> None:
        yaml_path = self.db_path.with_name("skills.yaml")
        if not yaml_path.exists():
            return
        try:
            with open(yaml_path) as f:
                data = yaml.safe_load(f) or []
            if isinstance(data, list):
                self.import_skills(data)
        except Exception:
            pass

    def _row_to_skill(self, row: sqlite3.Row) -> Skill:
        return Skill(
            id=row["id"],
            project=row["project"],
            name=row["name"],
            preconditions=json.loads(row["preconditions"] or "[]"),
            procedure=json.loads(row["procedure"] or "[]"),
            evidence=json.loads(row["evidence"] or "[]"),
            success_rate=row["success_rate"],
            verified=bool(row["verified"]),
            tags=json.loads(row["tags"] or "[]"),
            timestamp=row["timestamp"],
            parameters=json.loads(row["parameters"] or "{}"),
            composition=json.loads(row["composition"] or "[]"),
            precondition_checks=json.loads(row["precondition_checks"] or "[]"),
            cost=row["cost"] or "unknown",
            risk=row["risk"] or "unknown",
        )

    def add(self, skill: Skill, batch_id: str | None = None) -> None:
        with mutation_scope(self, batch_id, "skill.add") as (journal, active_batch):
            with self._connect() as conn:
                sequence = record_before(self, journal, active_batch, conn, "skills", "id", skill.id)
                existing = conn.execute("SELECT * FROM skills WHERE id = ?", (skill.id,)).fetchone()
                conn.execute(
                    """
                    INSERT INTO skills
                    (id, project, name, preconditions, procedure, evidence, success_rate, verified, tags, timestamp, parameters, composition, precondition_checks, cost, risk)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(project, name) DO UPDATE SET
                        id=excluded.id,
                        preconditions=excluded.preconditions,
                        procedure=excluded.procedure,
                        evidence=excluded.evidence,
                        success_rate=excluded.success_rate,
                        verified=excluded.verified,
                        tags=excluded.tags,
                        timestamp=excluded.timestamp,
                        parameters=excluded.parameters,
                        composition=excluded.composition,
                        precondition_checks=excluded.precondition_checks,
                        cost=excluded.cost,
                        risk=excluded.risk
                    """,
                    (
                        skill.id,
                        skill.project,
                        skill.name,
                        json.dumps(skill.preconditions),
                        json.dumps(skill.procedure),
                        json.dumps(skill.evidence),
                        skill.success_rate,
                        int(skill.verified),
                        json.dumps(skill.tags),
                        skill.timestamp,
                        json.dumps(skill.parameters),
                        json.dumps(skill.composition),
                        json.dumps(skill.precondition_checks),
                        skill.cost,
                        skill.risk,
                    ),
                )
                rowid = conn.execute("SELECT rowid FROM skills WHERE id = ?", (skill.id,)).fetchone()[0]
                if existing:
                    conn.execute(
                        "INSERT INTO skills_fts(skills_fts, rowid, name, preconditions, procedure, tags) VALUES ('delete', ?, ?, ?, ?, ?)",
                        (rowid, existing["name"], existing["preconditions"], existing["procedure"], existing["tags"]),
                    )
                conn.execute(
                    "INSERT INTO skills_fts(rowid, name, preconditions, procedure, tags) VALUES (?, ?, ?, ?, ?)",
                    (
                        rowid,
                        skill.name,
                        " ".join(skill.preconditions),
                        " ".join(skill.procedure),
                        " ".join(skill.tags),
                    ),
                )
                conn.commit()
                record_after(self, journal, conn, "skills", "id", skill.id, sequence)

    def get_all(self, project: str | None = None) -> list[Skill]:
        with self._connect() as conn:
            if project:
                rows = conn.execute(
                    "SELECT * FROM skills WHERE project = ? ORDER BY timestamp DESC", (project,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM skills ORDER BY timestamp DESC").fetchall()
        return [self._row_to_skill(r) for r in rows]

    def list_skills(self, project: str, limit: int = 100, offset: int = 0) -> list[Skill]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM skills WHERE project = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (project, limit, offset),
            ).fetchall()
        return [self._row_to_skill(r) for r in rows]

    def delete_by_id(self, skill_id: str, batch_id: str | None = None) -> bool:
        with mutation_scope(self, batch_id, "skill.delete") as (journal, active_batch):
            with self._connect() as conn:
                sequence = record_before(self, journal, active_batch, conn, "skills", "id", skill_id)
                row = conn.execute("SELECT rowid AS skill_rowid, * FROM skills WHERE id = ?", (skill_id,)).fetchone()
                if row:
                    conn.execute(
                        "INSERT INTO skills_fts(skills_fts, rowid, name, preconditions, procedure, tags) VALUES ('delete', ?, ?, ?, ?, ?)",
                        (row["skill_rowid"], row["name"], row["preconditions"], row["procedure"], row["tags"]),
                    )
                cur = conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
                conn.commit()
                record_after(self, journal, conn, "skills", "id", skill_id, sequence)
                return cur.rowcount > 0

    def search_fts(self, project: str, query: str, limit: int = 20) -> list[Skill]:
        """Full-text search with BM25 ranking via FTS5."""
        if not query.strip():
            return []
        terms = [t.replace('"', '""') for t in query.split() if t]
        if not terms:
            return []
        match_query = " AND ".join(f'"{t}"' for t in terms)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT s.*, bm25(skills_fts) AS rank
                FROM skills_fts
                JOIN skills s ON s.rowid = skills_fts.rowid
                WHERE skills_fts MATCH ? AND s.project = ?
                ORDER BY rank LIMIT ?
                """,
                (match_query, project, limit),
            ).fetchall()
        return [self._row_to_skill(row) for row in rows]

    def search(self, project: str, query: str, limit: int = 20) -> list[Skill]:
        terms = [t.strip().lower() for t in query.split() if t.strip()]
        skills = self.get_all(project)
        if not terms:
            return skills[:limit]
        results = []
        for skill in skills:
            text = " ".join(
                [skill.name]
                + skill.preconditions
                + skill.procedure
                + [str(e) for e in skill.evidence]
            ).lower()
            score = sum(1 for t in terms if t in text)
            if score > 0:
                results.append((score, skill))
        results.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in results[:limit]]

    def get_by_id(self, skill_id: str) -> Skill | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
        return self._row_to_skill(row) if row else None

    def update(self, skill: Skill, batch_id: str | None = None) -> None:
        with mutation_scope(self, batch_id, "skill.update") as (journal, active_batch):
            with self._connect() as conn:
                sequence = record_before(self, journal, active_batch, conn, "skills", "id", skill.id)
                existing = conn.execute("SELECT * FROM skills WHERE id = ?", (skill.id,)).fetchone()
                conn.execute(
                    """
                    UPDATE skills SET
                        project = ?, name = ?, preconditions = ?, procedure = ?,
                        evidence = ?, success_rate = ?, verified = ?, tags = ?, timestamp = ?,
                        parameters = ?, composition = ?, precondition_checks = ?, cost = ?, risk = ?
                    WHERE id = ?
                    """,
                    (
                        skill.project,
                        skill.name,
                        json.dumps(skill.preconditions),
                        json.dumps(skill.procedure),
                        json.dumps(skill.evidence),
                        skill.success_rate,
                        int(skill.verified),
                        json.dumps(skill.tags),
                        skill.timestamp,
                        json.dumps(skill.parameters),
                        json.dumps(skill.composition),
                        json.dumps(skill.precondition_checks),
                        skill.cost,
                        skill.risk,
                        skill.id,
                    ),
                )
                rowid = conn.execute("SELECT rowid FROM skills WHERE id = ?", (skill.id,)).fetchone()[0]
                if existing:
                    conn.execute(
                        "INSERT INTO skills_fts(skills_fts, rowid, name, preconditions, procedure, tags) VALUES ('delete', ?, ?, ?, ?, ?)",
                        (rowid, existing["name"], existing["preconditions"], existing["procedure"], existing["tags"]),
                    )
                conn.execute(
                    "INSERT INTO skills_fts(rowid, name, preconditions, procedure, tags) VALUES (?, ?, ?, ?, ?)",
                    (rowid, skill.name, " ".join(skill.preconditions), " ".join(skill.procedure), " ".join(skill.tags)),
                )
                conn.commit()
                record_after(self, journal, conn, "skills", "id", skill.id, sequence)

    def update_success(self, skill_id: str, success: bool = True) -> None:
        skill = self.get_by_id(skill_id)
        if not skill:
            return
        total = sum(1 for _ in skill.evidence) + 1
        successes = sum(1 for e in skill.evidence if e.get("success")) + (1 if success else 0)
        skill.success_rate = successes / total if total > 0 else 0.0
        self.update(skill)

    def import_skills(self, skills: list[dict[str, Any]]) -> int:
        added = 0
        for data in skills:
            skill = Skill.from_dict(data)
            self.add(skill)
            added += 1
        return added

    def export_skills(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self.get_all()]

    def count(self, project: str | None = None) -> int:
        with self._connect() as conn:
            if project:
                row = conn.execute(
                    "SELECT COUNT(*) FROM skills WHERE project = ?", (project,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM skills").fetchone()
        return row[0] if row else 0

    def get_skills_timeline(
        self,
        project: str,
        since: str | None = None,
        until: str | None = None,
    ) -> list[dict[str, Any]]:
        skills = self.get_all(project)
        result = []
        for skill in skills:
            ts = skill.timestamp
            if since and ts < since:
                continue
            if until and ts > until:
                continue
            result.append({"type": "skill", "timestamp": ts, "data": skill.to_dict()})
        result.sort(key=lambda x: x["timestamp"], reverse=True)
        return result

    # Review queue -----------------------------------------------------------

    def _ensure_pending_table(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_skills (
                    id TEXT PRIMARY KEY,
                    project TEXT NOT NULL,
                    name TEXT NOT NULL,
                    preconditions TEXT,
                    procedure TEXT,
                    evidence TEXT,
                    success_rate REAL DEFAULT 0,
                    verified INTEGER DEFAULT 0,
                    tags TEXT,
                    timestamp TEXT,
                    parameters TEXT,
                    composition TEXT,
                    precondition_checks TEXT,
                    cost TEXT DEFAULT 'unknown',
                    risk TEXT DEFAULT 'unknown'
                )
                """
            )

    def add_pending(self, skill: Skill, batch_id: str | None = None) -> None:
        self._ensure_pending_table()
        with mutation_scope(self, batch_id, "skill.add_pending") as (journal, active_batch):
            with self._connect() as conn:
                sequence = record_before(self, journal, active_batch, conn, "pending_skills", "id", skill.id)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO pending_skills
                    (id, project, name, preconditions, procedure, evidence, success_rate, verified, tags, timestamp, parameters, composition, precondition_checks, cost, risk)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        skill.id,
                        skill.project,
                        skill.name,
                        json.dumps(skill.preconditions),
                        json.dumps(skill.procedure),
                        json.dumps(skill.evidence),
                        skill.success_rate,
                        int(skill.verified),
                        json.dumps(skill.tags),
                        skill.timestamp,
                        json.dumps(skill.parameters),
                        json.dumps(skill.composition),
                        json.dumps(skill.precondition_checks),
                        skill.cost,
                        skill.risk,
                    ),
                )
                conn.commit()
                record_after(self, journal, conn, "pending_skills", "id", skill.id, sequence)

    def list_pending(self, project: str | None = None) -> list[Skill]:
        self._ensure_pending_table()
        with self._connect() as conn:
            if project:
                rows = conn.execute(
                    "SELECT * FROM pending_skills WHERE project = ? ORDER BY timestamp DESC",
                    (project,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM pending_skills ORDER BY timestamp DESC"
                ).fetchall()
        return [self._row_to_skill(r) for r in rows]

    def promote_pending(self, skill_id: str, batch_id: str | None = None) -> bool:
        self._ensure_pending_table()
        with mutation_scope(self, batch_id, "skill.promote_pending") as (journal, active_batch):
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM pending_skills WHERE id = ?", (skill_id,)).fetchone()
                if not row:
                    return False
                sequence = record_before(
                    self, journal, active_batch, conn, "pending_skills", "id", skill_id
                )
                skill = self._row_to_skill(row)
                self.add(skill, batch_id=active_batch)
                conn.execute("DELETE FROM pending_skills WHERE id = ?", (skill_id,))
                conn.commit()
                record_after(self, journal, conn, "pending_skills", "id", skill_id, sequence)
                return True

    def reject_pending(self, skill_id: str, batch_id: str | None = None) -> bool:
        self._ensure_pending_table()
        with mutation_scope(self, batch_id, "skill.reject_pending") as (journal, active_batch):
            with self._connect() as conn:
                sequence = record_before(
                    self, journal, active_batch, conn, "pending_skills", "id", skill_id
                )
                cur = conn.execute("DELETE FROM pending_skills WHERE id = ?", (skill_id,))
                conn.commit()
                record_after(self, journal, conn, "pending_skills", "id", skill_id, sequence)
                return cur.rowcount > 0
