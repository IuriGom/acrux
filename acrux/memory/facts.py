"""Fact storage mixin: CRUD, confidence, decay, versioning, pending facts, metrics."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta

from acrux.utils import utcnow
from typing import Any

from acrux.models import Fact


class FactStoreMixin:
    """Fact CRUD, search, confidence, decay, versioning, pending facts, metrics.

    Expects the host class to provide ``db_path``, ``embedder``, ``dim``,
    ``vector_index`` and a ``_connect()`` method (see SemanticStore).
    """

    @staticmethod
    def _content_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _fact_checksum(self, fact: Fact) -> str:
        payload = json.dumps(
            {
                "content": fact.content,
                "source": fact.source,
                "tags": fact.tags,
                "project": fact.project,
                "fact_type": fact.fact_type,
                "inheritance_mode": fact.inheritance_mode,
                "parent_id": fact.parent_id,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def add(self, fact: Fact) -> None:
        if fact.confidence == 0:
            fact.confidence = fact.default_confidence()
        if not fact.checksum:
            fact.checksum = self._fact_checksum(fact)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO facts
                (project, content, source, tags, timestamp, confidence, verified_count,
                 contradicted_count, stale, git_info, parent_id, version_group_id,
                 is_current, fact_type, cluster_id, inheritance_mode, decay_score,
                 last_recalled_at, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact.project,
                    fact.content,
                    fact.source,
                    json.dumps(fact.tags),
                    fact.timestamp,
                    fact.confidence,
                    fact.verified_count,
                    fact.contradicted_count,
                    1 if fact.stale else 0,
                    json.dumps(fact.git_info) if fact.git_info is not None else None,
                    fact.parent_id,
                    fact.version_group_id,
                    1 if fact.is_current else 0,
                    fact.fact_type,
                    fact.cluster_id,
                    fact.inheritance_mode,
                    fact.decay_score,
                    fact.last_recalled_at,
                    fact.checksum,
                ),
            )
            fact_id = cursor.lastrowid
            fact.id = fact_id
            conn.execute(
                "INSERT INTO facts_fts(rowid, content) VALUES (?, ?)",
                (fact_id, fact.content),
            )
            if fact.version_group_id is None:
                fact.version_group_id = fact_id
                conn.execute(
                    "UPDATE facts SET version_group_id = ? WHERE id = ?", (fact_id, fact_id)
                )
            conn.commit()

        if self.embedder:
            try:
                content_hash = self._content_hash(fact.content)
                existing_vector = self._find_embedding_by_hash(content_hash)
                if existing_vector is not None:
                    vector = existing_vector
                else:
                    vector = await self.embedder.embed(fact.content)
                with self._connect() as conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO fact_embeddings (fact_id, content_hash, vector) VALUES (?, ?, ?)",
                        (fact_id, content_hash, json.dumps(vector)),
                    )
                    conn.commit()
                self.vector_index.add(fact_id, vector)
            except Exception:
                pass

    def _find_embedding_by_hash(self, content_hash: str) -> list[float] | None:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT vector FROM fact_embeddings WHERE content_hash = ? LIMIT 1",
                (content_hash,),
            ).fetchone()
        if row and row["vector"]:
            return json.loads(row["vector"])
        return None

    def get_recent(self, project: str, limit: int = 100) -> list[Fact]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM facts WHERE project = ? ORDER BY timestamp DESC LIMIT ?",
                (project, limit),
            ).fetchall()
        return [self._row_to_fact(row) for row in rows]

    def get_by_id(self, fact_id: int) -> Fact | None:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM facts WHERE id = ?",
                (fact_id,),
            ).fetchone()
        return self._row_to_fact(row) if row else None

    def delete_by_id(self, fact_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
            conn.execute("DELETE FROM fact_embeddings WHERE fact_id = ?", (fact_id,))
            conn.execute("DELETE FROM fact_versions WHERE fact_id = ?", (fact_id,))
            conn.execute("DELETE FROM facts_fts WHERE rowid = ?", (fact_id,))
            conn.commit()
        if cursor.rowcount > 0:
            self.vector_index.remove(fact_id)
            return True
        return False

    async def update_fact(
        self,
        fact_id: int,
        content: str | None = None,
        tags: list[str] | None = None,
        parent_id: int | None = None,
        fact_type: str | None = None,
        inheritance_mode: str | None = None,
    ) -> Fact | None:
        existing = self.get_by_id(fact_id)
        if not existing:
            return None

        changed = False
        if content is not None and content != existing.content:
            # Snapshot current version before overwriting
            self._create_version(existing, "user")
            existing.content = content
            existing.timestamp = utcnow().isoformat()
            existing.checksum = self._fact_checksum(existing)
            changed = True
            if self.embedder:
                try:
                    new_vector = await self.embedder.embed(existing.content)
                    content_hash = self._content_hash(existing.content)
                    with self._connect() as conn:
                        conn.execute(
                            "INSERT OR REPLACE INTO fact_embeddings (fact_id, content_hash, vector) VALUES (?, ?, ?)",
                            (fact_id, content_hash, json.dumps(new_vector)),
                        )
                        conn.commit()
                    self.vector_index.add(fact_id, new_vector)
                except Exception:
                    pass
        if tags is not None:
            existing.tags = tags
            changed = True
        if parent_id is not None:
            existing.parent_id = parent_id
            changed = True
        if fact_type is not None:
            existing.fact_type = fact_type
            changed = True
        if inheritance_mode is not None:
            existing.inheritance_mode = inheritance_mode
            changed = True

        if changed:
            existing.checksum = self._fact_checksum(existing)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE facts SET
                    content = ?, source = ?, tags = ?, timestamp = ?, confidence = ?,
                    verified_count = ?, contradicted_count = ?, stale = ?, git_info = ?,
                    parent_id = ?, version_group_id = ?, is_current = ?, fact_type = ?,
                    cluster_id = ?, inheritance_mode = ?, decay_score = ?, last_recalled_at = ?,
                    checksum = ?
                WHERE id = ?
                """,
                (
                    existing.content,
                    existing.source,
                    json.dumps(existing.tags),
                    existing.timestamp,
                    existing.confidence,
                    existing.verified_count,
                    existing.contradicted_count,
                    1 if existing.stale else 0,
                    json.dumps(existing.git_info) if existing.git_info is not None else None,
                    existing.parent_id,
                    existing.version_group_id,
                    1 if existing.is_current else 0,
                    existing.fact_type,
                    existing.cluster_id,
                    existing.inheritance_mode,
                    existing.decay_score,
                    existing.last_recalled_at,
                    existing.checksum,
                    fact_id,
                ),
            )
            conn.commit()
        return existing

    def _create_version(self, fact: Fact, edited_by: str = "reflection") -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO fact_versions (fact_id, content, tags, edited_at, edited_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    fact.id,
                    fact.content,
                    json.dumps(fact.tags),
                    fact.timestamp or utcnow().isoformat(),
                    edited_by,
                ),
            )
            # Cap versions per fact
            conn.execute(
                """
                DELETE FROM fact_versions
                WHERE id NOT IN (
                    SELECT id FROM fact_versions WHERE fact_id = ? ORDER BY edited_at DESC LIMIT 50
                ) AND fact_id = ?
                """,
                (fact.id, fact.id),
            )
            conn.commit()

    def get_versions(self, fact_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM fact_versions WHERE fact_id = ? ORDER BY edited_at DESC",
                (fact_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    async def restore_version(self, fact_id: int, version_id: int) -> Fact | None:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM fact_versions WHERE id = ? AND fact_id = ?",
                (version_id, fact_id),
            ).fetchone()
        if not row:
            return None
        existing = self.get_by_id(fact_id)
        if not existing:
            return None
        self._create_version(existing, "restore")
        existing.content = row["content"]
        existing.tags = json.loads(row["tags"] or "[]")
        existing.timestamp = utcnow().isoformat()
        existing.checksum = self._fact_checksum(existing)
        return await self.update_fact(fact_id)

    async def create_child_fact(self, parent_id: int, fact: Fact) -> Fact:
        fact.parent_id = parent_id
        parent = self.get_by_id(parent_id)
        if parent:
            fact.project = parent.project
            fact.version_group_id = None
        await self.add(fact)
        return fact

    async def search(
        self,
        project: str,
        query: str,
        limit: int = 20,
        tags: list[str] | None = None,
        since: str | None = None,
        until: str | None = None,
        fact_type: str | None = None,
    ) -> list[Fact]:
        if self.embedder and query.strip():
            try:
                query_vec = await self.embedder.embed(query)
                vector_results = self._vector_search(
                    project,
                    query_vec,
                    limit,
                    tags=tags,
                    since=since,
                    until=until,
                    fact_type=fact_type,
                )
                if vector_results:
                    return vector_results
            except Exception:
                pass
        return self._keyword_search(
            project, query, limit, tags=tags, since=since, until=until, fact_type=fact_type
        )

    def search_fts(
        self,
        project: str,
        query: str,
        limit: int = 20,
        tags: list[str] | None = None,
        fact_type: str | None = None,
    ) -> list[Fact]:
        """Full-text search with BM25 ranking via FTS5."""
        if not query.strip():
            return []
        # Escape FTS5 special characters by quoting each term
        terms = [t.replace('"', '""') for t in query.split() if t]
        if not terms:
            return []
        match_query = " AND ".join(f'"{t}"' for t in terms)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            sql = """
                SELECT f.*, bm25(facts_fts) AS rank
                FROM facts_fts
                JOIN facts f ON f.id = facts_fts.rowid
                WHERE facts_fts MATCH ? AND f.project = ?
            """
            params: list[Any] = [match_query, project]
            if fact_type:
                sql += " AND f.fact_type = ?"
                params.append(fact_type)
            sql += " ORDER BY rank LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
        facts = [self._row_to_fact(row) for row in rows]
        if tags:
            facts = [f for f in facts if self._matches_tags(json.dumps(f.tags), tags)]
        return facts

    def _matches_tags(
        self, row_tags_json: str | None, tags: list[str] | None, match_all: bool = False
    ) -> bool:
        if not tags:
            return True
        row_tags = set(json.loads(row_tags_json or "[]"))
        if match_all:
            return all(t in row_tags for t in tags)
        return any(t in row_tags for t in tags)

    def _bump_recall_counts(self, fact_ids: list[int]) -> None:
        if not fact_ids:
            return
        placeholders = ", ".join("?" for _ in fact_ids)
        now = utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                f"UPDATE facts SET recall_count = recall_count + 1, last_recalled_at = ? WHERE id IN ({placeholders})",
                [now, *fact_ids],
            )
            conn.commit()

    def _recency_score(self, timestamp: str) -> float:
        try:
            ts = datetime.fromisoformat(timestamp)
        except Exception:
            ts = utcnow()
        days_old = max(0, (utcnow() - ts).total_seconds() / 86400)
        return math.exp(-days_old / 30)

    def _build_filters(
        self,
        project: str,
        tags: list[str] | None,
        since: str | None,
        until: str | None,
        fact_type: str | None,
    ) -> tuple[str, list[Any]]:
        base = "SELECT * FROM facts WHERE project = ?"
        params: list[Any] = [project]
        if tags:
            conditions = []
            for tag in tags:
                conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
            base += " AND (" + " OR ".join(conditions) + ")"
        if since:
            base += " AND timestamp >= ?"
            params.append(since)
        if until:
            base += " AND timestamp <= ?"
            params.append(until)
        if fact_type:
            base += " AND fact_type = ?"
            params.append(fact_type)
        return base, params

    def _keyword_search(
        self,
        project: str,
        query: str,
        limit: int,
        tags: list[str] | None = None,
        since: str | None = None,
        until: str | None = None,
        fact_type: str | None = None,
    ) -> list[Fact]:
        terms = [t.strip().lower() for t in query.split() if t.strip()]
        if not terms:
            rows = self._list_facts(
                project, tags=tags, limit=limit, since=since, until=until, fact_type=fact_type
            )
            return [self._row_to_fact(row) for row in rows]

        base, params = self._build_filters(project, tags, since, until, fact_type)
        base += " ORDER BY timestamp DESC LIMIT 500"
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(base, params).fetchall()

        results = []
        max_score = len(terms)
        for row in rows:
            text = " ".join([row["content"] or "", row["tags"] or ""]).lower()
            hits = sum(1 for t in terms if t in text)
            if hits > 0:
                keyword_score = hits / max_score
                recency = self._recency_score(row["timestamp"] or utcnow().isoformat())
                final = 0.7 * keyword_score + 0.3 * recency
                results.append((final, row))

        results.sort(key=lambda x: x[0], reverse=True)
        selected = results[:limit]
        self._bump_recall_counts([row["id"] for _, row in selected])
        return [self._row_to_fact(row) for _, row in selected]

    def _vector_search(
        self,
        project: str,
        query_vec: list[float],
        limit: int,
        tags: list[str] | None = None,
        since: str | None = None,
        until: str | None = None,
        fact_type: str | None = None,
    ) -> list[Fact]:
        base, params = self._build_filters(project, None, since, until, fact_type)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(base, params).fetchall()

        id_to_tags = {row["id"]: row["tags"] for row in rows}
        allowed = None
        if tags:
            allowed = {
                fid for fid, tags_json in id_to_tags.items() if self._matches_tags(tags_json, tags)
            }
            if not allowed:
                return []

        index_results = self.vector_index.search(query_vec, k=limit * 4, filter_ids=allowed)
        if not index_results:
            return []

        selected_ids = [fid for fid, _ in index_results[:limit]]
        placeholders = ", ".join("?" for _ in selected_ids)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM facts WHERE id IN ({placeholders})",
                selected_ids,
            ).fetchall()

        by_id = {row["id"]: row for row in rows}
        ordered_rows = [by_id[fid] for fid in selected_ids if fid in by_id]
        self._bump_recall_counts([row["id"] for row in ordered_rows])
        return [self._row_to_fact(row) for row in ordered_rows]

    def _list_facts(
        self,
        project: str,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "timestamp DESC",
        since: str | None = None,
        until: str | None = None,
        fact_type: str | None = None,
        cluster_id: int | None = None,
    ) -> list[sqlite3.Row]:
        base, params = self._build_filters(project, tags, since, until, fact_type)
        if cluster_id is not None:
            base += " AND cluster_id = ?"
            params.append(cluster_id)
        allowed_orders = {
            "timestamp DESC",
            "timestamp ASC",
            "confidence DESC",
            "confidence ASC, timestamp ASC",
            "stale DESC, confidence ASC, timestamp ASC",
            "decay_score DESC",
        }
        if order_by not in allowed_orders:
            order_by = "timestamp DESC"
        base += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(base, params).fetchall()

    def list_facts(
        self,
        project: str,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "timestamp DESC",
        since: str | None = None,
        until: str | None = None,
        fact_type: str | None = None,
        cluster_id: int | None = None,
    ) -> list[Fact]:
        rows = self._list_facts(
            project,
            tags=tags,
            limit=limit,
            offset=offset,
            order_by=order_by,
            since=since,
            until=until,
            fact_type=fact_type,
            cluster_id=cluster_id,
        )
        return [self._row_to_fact(row) for row in rows]

    def get_duplicate_facts(self, project: str, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, content, timestamp FROM facts WHERE project = ? ORDER BY timestamp DESC",
                (project,),
            ).fetchall()

        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            h = self._content_hash(row["content"] or "")
            groups[h].append(
                {
                    "id": row["id"],
                    "content": row["content"],
                    "timestamp": row["timestamp"],
                    "content_hash": h,
                }
            )

        dups = []
        for h, items in groups.items():
            if len(items) > 1:
                dups.append({**items[0], "count": len(items)})
            if len(dups) >= limit:
                break
        return dups

    def get_old_unrecalled_facts(
        self, project: str, days: int, limit: int = 50
    ) -> list[dict[str, Any]]:
        cutoff = (utcnow() - timedelta(days=days)).isoformat()
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, content, timestamp, recall_count FROM facts WHERE project = ? AND timestamp < ? AND recall_count = 0 ORDER BY timestamp ASC LIMIT ?",
                (project, cutoff, limit),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "content": row["content"],
                "timestamp": row["timestamp"],
                "recall_count": row["recall_count"],
            }
            for row in rows
        ]

    def get_facts_for_reverify(self, project: str, limit: int = 10) -> list[Fact]:
        """Return facts to re-check: stale first, then least-confident, oldest first."""
        rows = self._list_facts(
            project,
            limit=limit,
            order_by="stale DESC, confidence ASC, timestamp ASC",
        )
        return [self._row_to_fact(row) for row in rows]

    def record_verification(self, fact_id: int, verdict: str) -> Fact | None:
        fact = self.get_by_id(fact_id)
        if not fact:
            return None
        verdict_lower = verdict.lower()
        if verdict_lower == "yes":
            fact.verified_count += 1
            # A fresh confirmation rehabilitates a stale fact.
            fact.stale = False
        elif verdict_lower == "no":
            fact.contradicted_count += 1
        elif verdict_lower == "uncertain":
            fact.stale = True
        fact.update_confidence()
        with self._connect() as conn:
            conn.execute(
                "UPDATE facts SET verified_count = ?, contradicted_count = ?, confidence = ?, stale = ? WHERE id = ?",
                (
                    fact.verified_count,
                    fact.contradicted_count,
                    fact.confidence,
                    1 if fact.stale else 0,
                    fact_id,
                ),
            )
            conn.commit()
        return fact

    def record_conflict(self, fact_id: int) -> Fact | None:
        fact = self.get_by_id(fact_id)
        if not fact:
            return None
        fact.contradicted_count += 1
        fact.update_confidence()
        with self._connect() as conn:
            conn.execute(
                "UPDATE facts SET contradicted_count = ?, confidence = ? WHERE id = ?",
                (fact.contradicted_count, fact.confidence, fact_id),
            )
            conn.commit()
        return fact

    def record_outcome(self, fact_id: int, success: bool = True) -> Fact | None:
        """Record that a memory helped (or hurt) a task outcome."""
        fact = self.get_by_id(fact_id)
        if not fact:
            return None
        if success:
            fact.verified_count += 1
        else:
            fact.contradicted_count += 1
        fact.update_confidence()
        with self._connect() as conn:
            conn.execute(
                "UPDATE facts SET verified_count = ?, contradicted_count = ?, confidence = ? WHERE id = ?",
                (fact.verified_count, fact.contradicted_count, fact.confidence, fact_id),
            )
            conn.commit()
        return fact

    def prune_old(self, days: int) -> int:
        cutoff = (utcnow() - timedelta(days=days)).isoformat()
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM facts WHERE timestamp < ?", (cutoff,))
            conn.commit()
        return cursor.rowcount

    def count(self, project: str | None = None) -> int:
        with self._connect() as conn:
            if project:
                row = conn.execute(
                    "SELECT COUNT(*) FROM facts WHERE project = ?", (project,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM facts").fetchone()
        return row[0] if row else 0

    # ------------------------------------------------------------------
    # Pending facts (review queue)
    # ------------------------------------------------------------------

    def _ensure_pending_facts_table(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT,
                    content TEXT,
                    source TEXT,
                    tags TEXT,
                    timestamp TEXT,
                    confidence REAL DEFAULT 0.0,
                    verified_count INTEGER DEFAULT 0,
                    contradicted_count INTEGER DEFAULT 0,
                    stale INTEGER DEFAULT 0,
                    git_info TEXT,
                    fact_type TEXT DEFAULT 'positive',
                    cluster_id INTEGER
                )
                """
            )

    def add_pending_fact(self, fact: Fact) -> int:
        self._ensure_pending_facts_table()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO pending_facts
                (project, content, source, tags, timestamp, confidence, verified_count, contradicted_count, stale, git_info, fact_type, cluster_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact.project,
                    fact.content,
                    fact.source,
                    json.dumps(fact.tags),
                    fact.timestamp,
                    fact.confidence,
                    fact.verified_count,
                    fact.contradicted_count,
                    1 if fact.stale else 0,
                    json.dumps(fact.git_info) if fact.git_info else None,
                    fact.fact_type,
                    fact.cluster_id,
                ),
            )
            conn.commit()
            return cur.lastrowid

    def list_pending_facts(self, project: str, limit: int = 100) -> list[Fact]:
        self._ensure_pending_facts_table()
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM pending_facts WHERE project = ? ORDER BY timestamp DESC LIMIT ?",
                (project, limit),
            ).fetchall()
        return [self._row_to_fact(row) for row in rows]

    def promote_pending_fact(self, pending_id: int) -> bool:
        self._ensure_pending_facts_table()
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM pending_facts WHERE id = ?", (pending_id,)
            ).fetchone()
            if not row:
                return False
            fact = self._row_to_fact(row)
            self.add(fact)
            conn.execute("DELETE FROM pending_facts WHERE id = ?", (pending_id,))
            conn.commit()
            return True

    def reject_pending_fact(self, pending_id: int) -> bool:
        self._ensure_pending_facts_table()
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM pending_facts WHERE id = ?", (pending_id,))
            conn.commit()
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def _ensure_metrics_table(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT,
                    metric TEXT,
                    value REAL,
                    timestamp TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_project_metric ON metrics(project, metric)")

    def record_metric(self, project: str, metric: str, value: float) -> None:
        self._ensure_metrics_table()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO metrics (project, metric, value, timestamp) VALUES (?, ?, ?, ?)",
                (project, metric, value, utcnow().isoformat()),
            )
            conn.commit()

    def get_metrics(
        self, project: str, metric: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        self._ensure_metrics_table()
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if metric:
                rows = conn.execute(
                    "SELECT * FROM metrics WHERE project = ? AND metric = ? ORDER BY timestamp DESC LIMIT ?",
                    (project, metric, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM metrics WHERE project = ? ORDER BY timestamp DESC LIMIT ?",
                    (project, limit),
                ).fetchall()
        return [dict(row) for row in rows]

    def get_metric_summary(self, project: str, metric: str) -> dict[str, float]:
        rows = self.get_metrics(project, metric, limit=1000)
        if not rows:
            return {"count": 0, "avg": 0.0, "min": 0.0, "max": 0.0}
        values = [r["value"] for r in rows]
        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }

    # ------------------------------------------------------------------
    # Versioning helpers
    # ------------------------------------------------------------------

    def create_version(self, fact_id: int, edited_by: str = "reflection") -> None:
        fact = self.get_by_id(fact_id)
        if fact:
            self._create_version(fact, edited_by)

    # ------------------------------------------------------------------
    # Hierarchy helpers
    # ------------------------------------------------------------------

    def set_parent(self, fact_id: int, parent_id: int | None) -> Fact | None:
        return None  # placeholder; use update_fact with parent_id

    # ------------------------------------------------------------------
    # Decay
    # ------------------------------------------------------------------

    def compute_decay_scores(self, project: str, half_life_days: float = 30.0) -> int:
        now = utcnow()
        facts = self.list_facts(project, limit=100000)
        updated = 0
        for fact in facts:
            ts = fact.timestamp
            if fact.last_recalled_at:
                ts = fact.last_recalled_at
            try:
                dt = datetime.fromisoformat(ts)
            except Exception:
                dt = now
            age_days = max(0, (now - dt).total_seconds() / 86400)
            recall_boost = 1.0 / (1.0 + fact.recall_count)
            confidence_factor = 1.0 - fact.confidence
            decay = 1.0 - math.exp(-age_days / half_life_days) * confidence_factor * recall_boost
            decay = max(0.0, min(1.0, decay))
            fact.decay_score = decay
            with self._connect() as conn:
                conn.execute("UPDATE facts SET decay_score = ? WHERE id = ?", (decay, fact.id))
                conn.commit()
            updated += 1
        return updated

    def list_stale_facts(
        self, project: str, threshold: float = 0.7, limit: int = 100
    ) -> list[Fact]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM facts WHERE project = ? AND decay_score >= ? ORDER BY decay_score DESC LIMIT ?",
                (project, threshold, limit),
            ).fetchall()
        return [self._row_to_fact(row) for row in rows]

    # ------------------------------------------------------------------
    # Timeline helpers
    # ------------------------------------------------------------------

    def get_facts_timeline(
        self,
        project: str,
        since: str | None = None,
        until: str | None = None,
    ) -> list[dict[str, Any]]:
        base = "SELECT * FROM facts WHERE project = ?"
        params: list[Any] = [project]
        if since:
            base += " AND timestamp >= ?"
            params.append(since)
        if until:
            base += " AND timestamp <= ?"
            params.append(until)
        base += " ORDER BY timestamp DESC"
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(base, params).fetchall()
        return [
            {
                "type": "fact",
                "timestamp": row["timestamp"],
                "data": self._row_to_fact(row).to_dict(),
            }
            for row in rows
        ]

    def get_versions_timeline(
        self,
        project: str,
        since: str | None = None,
        until: str | None = None,
    ) -> list[dict[str, Any]]:
        base = """
            SELECT v.* FROM fact_versions v
            JOIN facts f ON f.id = v.fact_id
            WHERE f.project = ?
        """
        params: list[Any] = [project]
        if since:
            base += " AND v.edited_at >= ?"
            params.append(since)
        if until:
            base += " AND v.edited_at <= ?"
            params.append(until)
        base += " ORDER BY v.edited_at DESC"
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(base, params).fetchall()
        return [
            {"type": "version", "timestamp": row["edited_at"], "data": dict(row)} for row in rows
        ]

    # ------------------------------------------------------------------
    # Row conversion
    # ------------------------------------------------------------------

    def _row_to_fact(self, row: sqlite3.Row) -> Fact:
        # pending_facts has a narrower schema than facts; default missing columns.
        keys = set(row.keys())

        def get(key: str, default: Any = None) -> Any:
            return row[key] if key in keys else default

        return Fact(
            id=row["id"],
            project=row["project"] or "default",
            content=row["content"] or "",
            source=row["source"] or "",
            tags=json.loads(row["tags"] or "[]"),
            timestamp=row["timestamp"] or utcnow().isoformat(),
            confidence=row["confidence"] if row["confidence"] is not None else 0.0,
            verified_count=row["verified_count"] or 0,
            contradicted_count=row["contradicted_count"] or 0,
            stale=bool(row["stale"]),
            git_info=json.loads(row["git_info"]) if row["git_info"] else None,
            parent_id=get("parent_id"),
            version_group_id=get("version_group_id"),
            is_current=bool(get("is_current", 1)),
            fact_type=row["fact_type"] or "positive",
            cluster_id=row["cluster_id"],
            inheritance_mode=get("inheritance_mode") or "none",
            decay_score=get("decay_score") or 0.0,
            last_recalled_at=get("last_recalled_at"),
            checksum=get("checksum"),
            recall_count=get("recall_count") or 0,
        )
