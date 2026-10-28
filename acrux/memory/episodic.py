"""Episodic memory store backed by SQLite."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from typing import Any

from acrux.memory.journal import mutation_scope, record_after, record_before
from acrux.models import Action, Episode

from acrux.utils import utcnow


class EpisodicStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    session_id TEXT PRIMARY KEY,
                    task TEXT,
                    project TEXT,
                    context TEXT,
                    actions TEXT,
                    outcome TEXT,
                    root_cause TEXT,
                    fix_pattern TEXT,
                    tags TEXT,
                    timestamp TEXT,
                    corrected INTEGER,
                    compacted INTEGER DEFAULT 0,
                    source TEXT,
                    git_info TEXT
                )
            """)
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(
                    task, outcome, root_cause, fix_pattern, tags,
                    content='episodes',
                    content_rowid='rowid'
                )
                """
            )
            self._migrate_columns(conn)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_project ON episodes(project)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON episodes(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tags ON episodes(tags)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON episodes(source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_compacted ON episodes(compacted)")
            conn.commit()

    def _migrate_columns(self, conn: sqlite3.Connection) -> None:
        columns = [r[1] for r in conn.execute("PRAGMA table_info(episodes)").fetchall()]
        migrations = {
            "compacted": "ALTER TABLE episodes ADD COLUMN compacted INTEGER DEFAULT 0",
            "source": "ALTER TABLE episodes ADD COLUMN source TEXT",
            "git_info": "ALTER TABLE episodes ADD COLUMN git_info TEXT",
        }
        for column, sql in migrations.items():
            if column not in columns:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError:
                    pass

    def get_episodes_timeline(
        self,
        project: str,
        since: str | None = None,
        until: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM episodes WHERE project = ?"
        params: list[Any] = [project]
        if since:
            sql += " AND timestamp >= ?"
            params.append(since)
        if until:
            sql += " AND timestamp <= ?"
            params.append(until)
        sql += " ORDER BY timestamp DESC"
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
        return [
            {
                "type": "episode",
                "timestamp": row["timestamp"],
                "data": self._row_to_episode(row).to_dict(),
            }
            for row in rows
        ]

    def add(self, episode: Episode, batch_id: str | None = None) -> None:
        self._tag_errors(episode)
        self._tag_source(episode)
        with mutation_scope(self, batch_id, "episode.add") as (journal, active_batch):
            with sqlite3.connect(self.db_path) as conn:
                sequence = record_before(
                    self, journal, active_batch, conn, "episodes", "session_id", episode.session_id
                )
                existing = conn.execute(
                    "SELECT * FROM episodes WHERE session_id = ?", (episode.session_id,)
                ).fetchone()
                conn.execute(
                    """
                    INSERT OR REPLACE INTO episodes
                    (session_id, task, project, context, actions, outcome, root_cause,
                     fix_pattern, tags, timestamp, corrected, compacted, source, git_info)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        episode.session_id,
                        episode.task,
                        episode.project,
                        json.dumps(episode.context),
                        json.dumps([a.to_dict() for a in episode.actions]),
                        episode.outcome,
                        episode.root_cause,
                        episode.fix_pattern,
                        json.dumps(episode.tags),
                        episode.timestamp,
                        1 if episode.corrected else 0,
                        1 if episode.compacted else 0,
                        episode.source,
                        json.dumps(episode.git_info) if episode.git_info is not None else None,
                    ),
                )
                rowid = conn.execute(
                    "SELECT rowid FROM episodes WHERE session_id = ?", (episode.session_id,)
                ).fetchone()[0]
                if existing:
                    conn.execute(
                        "INSERT INTO episodes_fts(episodes_fts, rowid, task, outcome, root_cause, fix_pattern, tags) VALUES ('delete', ?, ?, ?, ?, ?, ?)",
                        (rowid, existing["task"], existing["outcome"], existing["root_cause"], existing["fix_pattern"], existing["tags"]),
                    )
                conn.execute(
                    "INSERT INTO episodes_fts(rowid, task, outcome, root_cause, fix_pattern, tags) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        rowid,
                        episode.task,
                        episode.outcome,
                        episode.root_cause,
                        episode.fix_pattern,
                        " ".join(episode.tags),
                    ),
                )
                conn.commit()
                record_after(
                    self, journal, conn, "episodes", "session_id", episode.session_id, sequence
                )

    def _tag_source(self, episode: Episode) -> None:
        if episode.source and episode.source.lower() == "kimi" and "kimi" not in episode.tags:
            episode.tags.append("kimi")

    def _tag_errors(self, episode: Episode) -> None:
        outcome_lower = (episode.outcome or "").lower()
        if any(word in outcome_lower for word in ("error", "fail", "exception", "traceback")):
            if "error" not in episode.tags:
                episode.tags.append("error")

    def get_recent(
        self,
        project: str,
        limit: int = 50,
        since: str | None = None,
        until: str | None = None,
    ) -> list[Episode]:
        sql = "SELECT * FROM episodes WHERE project = ?"
        params: list[Any] = [project]
        if since:
            sql += " AND timestamp >= ?"
            params.append(since)
        if until:
            sql += " AND timestamp <= ?"
            params.append(until)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_episode(row) for row in rows]

    def search(
        self, project: str, query: str, limit: int = 20, error_only: bool = False
    ) -> list[Episode]:
        """Simple keyword search over task, outcome, root_cause, fix_pattern, tags."""
        terms = [t.strip().lower() for t in query.split() if t.strip()]
        if not terms:
            if error_only:
                return self.get_failed(project, limit)
            return self.get_recent(project, limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            sql = "SELECT * FROM episodes WHERE project = ?"
            params: list[Any] = [project]
            if error_only:
                sql += " AND (tags LIKE ? OR outcome LIKE ?)"
                params.extend(["%error%", "%error%"])
            sql += " ORDER BY timestamp DESC LIMIT 500"
            rows = conn.execute(sql, params).fetchall()

        results = []
        for row in rows:
            text = " ".join(
                [
                    row["task"] or "",
                    row["outcome"] or "",
                    row["root_cause"] or "",
                    row["fix_pattern"] or "",
                    row["tags"] or "",
                ]
            ).lower()
            score = sum(1 for t in terms if t in text)
            if score > 0:
                results.append((score, row))

        results.sort(key=lambda x: x[0], reverse=True)
        return [self._row_to_episode(row) for _, row in results[:limit]]

    def get_by_id(self, session_id: str) -> Episode | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM episodes WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return self._row_to_episode(row) if row else None

    def search_fts(self, project: str, query: str, limit: int = 20) -> list[Episode]:
        """Full-text search with BM25 ranking via FTS5."""
        if not query.strip():
            return []
        terms = [t.replace('"', '""') for t in query.split() if t]
        if not terms:
            return []
        match_query = " AND ".join(f'"{t}"' for t in terms)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT e.*, bm25(episodes_fts) AS rank
                FROM episodes_fts
                JOIN episodes e ON e.rowid = episodes_fts.rowid
                WHERE episodes_fts MATCH ? AND e.project = ?
                ORDER BY rank LIMIT ?
                """,
                (match_query, project, limit),
            ).fetchall()
        return [self._row_to_episode(row) for row in rows]

    def delete_by_id(self, session_id: str, batch_id: str | None = None) -> bool:
        with mutation_scope(self, batch_id, "episode.delete") as (journal, active_batch):
            with sqlite3.connect(self.db_path) as conn:
                sequence = record_before(
                    self, journal, active_batch, conn, "episodes", "session_id", session_id
                )
                row = conn.execute(
                    "SELECT rowid AS episode_rowid, * FROM episodes WHERE session_id = ?", (session_id,)
                ).fetchone()
                if row:
                    conn.execute(
                        "INSERT INTO episodes_fts(episodes_fts, rowid, task, outcome, root_cause, fix_pattern, tags) VALUES ('delete', ?, ?, ?, ?, ?, ?)",
                        (row["episode_rowid"], row["task"], row["outcome"], row["root_cause"], row["fix_pattern"], row["tags"]),
                    )
                cursor = conn.execute("DELETE FROM episodes WHERE session_id = ?", (session_id,))
                conn.commit()
                record_after(self, journal, conn, "episodes", "session_id", session_id, sequence)
        return cursor.rowcount > 0

    def list_episodes(
        self,
        project: str,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "timestamp DESC",
    ) -> list[Episode]:
        base = "SELECT * FROM episodes WHERE project = ?"
        params: list[Any] = [project]
        if tags:
            conditions = []
            for tag in tags:
                conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
            base += " AND (" + " OR ".join(conditions) + ")"
        base += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(base, params).fetchall()
        return [self._row_to_episode(row) for row in rows]

    def get_old(self, project: str, days: int) -> list[Episode]:
        cutoff = (utcnow() - timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM episodes WHERE project = ? AND timestamp < ? AND compacted = 0 ORDER BY timestamp DESC",
                (project, cutoff),
            ).fetchall()
        return [self._row_to_episode(row) for row in rows]

    def mark_compacted(self, session_ids: list[str], batch_id: str | None = None) -> None:
        if not session_ids:
            return
        with mutation_scope(self, batch_id, "episode.mark_compacted") as (journal, active_batch):
            placeholders = ", ".join("?" for _ in session_ids)
            with sqlite3.connect(self.db_path) as conn:
                sequences = {
                    session_id: record_before(
                        self, journal, active_batch, conn, "episodes", "session_id", session_id
                    )
                    for session_id in session_ids
                }
                conn.execute(
                    f"UPDATE episodes SET compacted = 1 WHERE session_id IN ({placeholders})",
                    session_ids,
                )
                conn.commit()
                for session_id, sequence in sequences.items():
                    record_after(
                        self, journal, conn, "episodes", "session_id", session_id, sequence
                    )

    def get_failed(self, project: str, limit: int = 100) -> list[Episode]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM episodes WHERE project = ? AND (tags LIKE ? OR outcome LIKE ?) ORDER BY timestamp DESC LIMIT ?",
                (project, "%error%", "%error%", limit),
            ).fetchall()
        return [self._row_to_episode(row) for row in rows]

    def get_unreflected(self, project: str, limit: int = 100) -> list[Episode]:
        # Non-compacted episodes are candidates for reflection.
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM episodes WHERE project = ? AND compacted = 0 ORDER BY timestamp DESC LIMIT ?",
                (project, limit),
            ).fetchall()
        return [self._row_to_episode(row) for row in rows]

    def count_unreflected(self, project: str | None = None) -> int:
        with sqlite3.connect(self.db_path) as conn:
            if project:
                row = conn.execute(
                    "SELECT COUNT(*) FROM episodes WHERE project = ? AND compacted = 0",
                    (project,),
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM episodes WHERE compacted = 0").fetchone()
        return row[0] if row else 0

    def prune_old(self, days: int) -> int:
        cutoff = (utcnow() - timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM episodes WHERE timestamp < ?", (cutoff,))
            conn.commit()
        return cursor.rowcount

    def count(self, project: str | None = None) -> int:
        with sqlite3.connect(self.db_path) as conn:
            if project:
                row = conn.execute(
                    "SELECT COUNT(*) FROM episodes WHERE project = ?", (project,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()
        return row[0] if row else 0

    def _row_to_episode(self, row: sqlite3.Row) -> Episode:
        return Episode(
            session_id=row["session_id"],
            task=row["task"] or "",
            project=row["project"] or "default",
            context=json.loads(row["context"] or "{}"),
            actions=[Action.from_dict(a) for a in json.loads(row["actions"] or "[]")],
            outcome=row["outcome"] or "",
            root_cause=row["root_cause"] or "",
            fix_pattern=row["fix_pattern"] or "",
            tags=json.loads(row["tags"] or "[]"),
            timestamp=row["timestamp"] or utcnow().isoformat(),
            corrected=bool(row["corrected"]),
            compacted=bool(row["compacted"]),
            source=row["source"] or "",
            git_info=json.loads(row["git_info"]) if row["git_info"] else None,
        )
