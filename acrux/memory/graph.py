"""Graph mixin: relationships, trees, clusters, inheritance layers."""

from __future__ import annotations

import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from acrux.models import Fact

from acrux.utils import utcnow


class GraphStoreMixin:
    """Fact relationships, hierarchy trees, clustering, project inheritance layers.

    Expects the host class to provide ``db_path``, ``embedder``, ``dim``,
    fact accessors (``get_by_id``, ``list_facts``, ``_content_hash``) and a
    ``_connect()`` method (see SemanticStore).
    """

    # ------------------------------------------------------------------
    # Trees
    # ------------------------------------------------------------------

    def get_children(self, parent_id: int, project: str | None = None) -> list[Fact]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if project:
                rows = conn.execute(
                    "SELECT * FROM facts WHERE parent_id = ? AND project = ? ORDER BY timestamp DESC",
                    (parent_id, project),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM facts WHERE parent_id = ? ORDER BY timestamp DESC",
                    (parent_id,),
                ).fetchall()
        return [self._row_to_fact(row) for row in rows]

    def get_ancestors(self, fact_id: int) -> list[Fact]:
        ancestors: list[Fact] = []
        seen: set[int] = set()
        current_id = fact_id
        for _ in range(20):
            fact = self.get_by_id(current_id)
            if not fact or fact.parent_id is None or fact.parent_id in seen:
                break
            seen.add(fact.parent_id)
            parent = self.get_by_id(fact.parent_id)
            if not parent:
                break
            ancestors.append(parent)
            current_id = parent.id
        return ancestors

    def get_tree(self, fact_id: int, depth: int = 3) -> dict[str, Any]:
        fact = self.get_by_id(fact_id)
        if not fact:
            return {}
        return {
            "fact": fact.to_dict(),
            "ancestors": [a.to_dict() for a in self.get_ancestors(fact_id)],
            "children": [
                self._subtree(child.id, depth - 1)
                for child in self.get_children(fact_id, fact.project)
            ],
        }

    def _subtree(self, fact_id: int | None, depth: int) -> dict[str, Any] | None:
        if fact_id is None or depth <= 0:
            return None
        fact = self.get_by_id(fact_id)
        if not fact:
            return None
        return {
            "fact": fact.to_dict(),
            "children": [
                self._subtree(child.id, depth - 1)
                for child in self.get_children(fact_id, fact.project)
            ],
        }

    def link_facts(
        self,
        project: str,
        source_fact_id: int,
        target_fact_id: int,
        relation_type: str = "related",
        strength: float = 0.5,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO fact_relationships (project, source_fact_id, target_fact_id, relation_type, strength)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project, source_fact_id, target_fact_id, relation_type, strength),
            )
            conn.commit()
            return cursor.lastrowid

    # ------------------------------------------------------------------
    # Clustering
    # ------------------------------------------------------------------

    def cluster_facts(self, project: str, max_clusters: int = 20) -> dict[str, Any]:
        facts = self.list_facts(project, limit=2000)
        if not facts:
            return {"clusters": 0, "facts": 0, "method": "none"}

        # Try embedding + k-means if possible
        vectors: dict[int, list[float]] = {}
        if self.embedder and self.dim:
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT fact_id, vector FROM fact_embeddings WHERE fact_id IN ({})".format(
                        ",".join("?" for _ in facts)
                    ),
                    [f.id for f in facts],
                ).fetchall()
            vectors = {row["fact_id"]: json.loads(row["vector"]) for row in rows if row["vector"]}

        if len(vectors) >= 10:
            try:
                return self._cluster_kmeans(project, facts, vectors, max_clusters)
            except Exception:
                pass
        return self._cluster_keywords(project, facts, max_clusters)

    def _cluster_kmeans(
        self,
        project: str,
        facts: list[Fact],
        vectors: dict[int, list[float]],
        max_clusters: int,
    ) -> dict[str, Any]:
        import numpy as np

        ids = [f.id for f in facts if f.id in vectors]
        matrix = np.array([vectors[fid] for fid in ids])
        n = len(ids)
        k = max(2, min(max_clusters, int(math.sqrt(n / 2))))
        # K-means++ initialization (simplified)
        rng = np.random.default_rng(0)
        centroids = matrix[rng.choice(n, k, replace=False)].copy()
        labels = np.zeros(n, dtype=int)
        for _ in range(20):
            distances = np.linalg.norm(matrix[:, np.newaxis] - centroids[np.newaxis, :], axis=2)
            labels = np.argmin(distances, axis=1)
            new_centroids = np.array(
                [
                    matrix[labels == i].mean(axis=0) if np.any(labels == i) else centroids[i]
                    for i in range(k)
                ]
            )
            if np.allclose(centroids, new_centroids):
                break
            centroids = new_centroids

        # Persist clusters
        now = utcnow().isoformat()
        with self._connect() as conn:
            conn.execute("DELETE FROM clusters WHERE project = ?", (project,))
            cluster_id_map: dict[int, int] = {}
            for cid in range(k):
                members = [ids[i] for i in range(n) if labels[i] == cid]
                if not members:
                    continue
                centroid = centroids[cid].tolist()
                label_text = self._cluster_label(members, facts)
                cur = conn.execute(
                    "INSERT INTO clusters (project, label, centroid_vector, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (project, label_text, json.dumps(centroid), now, now),
                )
                cluster_id_map[cid] = cur.lastrowid
                for fid in members:
                    conn.execute(
                        "UPDATE facts SET cluster_id = ? WHERE id = ?", (cluster_id_map[cid], fid)
                    )
            conn.commit()
        return {"clusters": len(cluster_id_map), "facts": n, "method": "kmeans"}

    def _cluster_keywords(
        self, project: str, facts: list[Fact], max_clusters: int
    ) -> dict[str, Any]:
        def tokens(text: str) -> set[str]:
            return {t.lower() for t in text.split() if len(t) > 3 and t.isalnum()}

        fact_tokens = [(f, tokens(f.content)) for f in facts if f.id]
        n = len(fact_tokens)
        # Union-find
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for i in range(n):
            for j in range(i + 1, n):
                a, b = fact_tokens[i][1], fact_tokens[j][1]
                if not a or not b:
                    continue
                inter = len(a & b)
                union_size = len(a | b)
                if union_size and inter / union_size >= 0.3:
                    union(i, j)

        groups: dict[int, list[int]] = defaultdict(list)
        for idx in range(n):
            groups[find(idx)].append(idx)

        now = utcnow().isoformat()
        with self._connect() as conn:
            conn.execute("DELETE FROM clusters WHERE project = ?", (project,))
            cluster_count = 0
            for group in sorted(groups.values(), key=len, reverse=True)[:max_clusters]:
                members = [fact_tokens[i][0].id for i in group]
                if not members:
                    continue
                label_text = self._cluster_label(members, facts)
                cur = conn.execute(
                    "INSERT INTO clusters (project, label, centroid_vector, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (project, label_text, "[]", now, now),
                )
                cid = cur.lastrowid
                for fid in members:
                    conn.execute("UPDATE facts SET cluster_id = ? WHERE id = ?", (cid, fid))
                cluster_count += 1
            conn.commit()
        return {"clusters": cluster_count, "facts": n, "method": "keyword"}

    def _cluster_label(self, member_ids: list[int], facts: list[Fact]) -> str:
        from collections import Counter

        texts = [f.content for f in facts if f.id in member_ids]
        words: list[str] = []
        for text in texts:
            for w in text.split():
                w = w.lower().strip('.,;:!?()[]{}"')
                if len(w) > 4 and w.isalpha():
                    words.append(w)
        if not words:
            return "cluster"
        counter = Counter(words)
        top = [w for w, _ in counter.most_common(3)]
        return " / ".join(top) if top else "cluster"

    def list_clusters(self, project: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM clusters WHERE project = ? ORDER BY updated_at DESC",
                (project,),
            ).fetchall()
        result = []
        for row in rows:
            result.append(
                {
                    "id": row["id"],
                    "project": row["project"],
                    "label": row["label"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )
        # Add member counts
        for item in result:
            with self._connect() as conn:
                item["fact_count"] = conn.execute(
                    "SELECT COUNT(*) FROM facts WHERE cluster_id = ?", (item["id"],)
                ).fetchone()[0]
        return result

    def get_cluster(self, cluster_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "project": row["project"],
            "label": row["label"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    # ------------------------------------------------------------------
    # Inheritance
    # ------------------------------------------------------------------

    def list_project_layers(self, project: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM project_layers WHERE project = ? ORDER BY layer_order",
                (project,),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_project_layer(self, project: str, base_project: str, layer_order: int = 0) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT OR REPLACE INTO project_layers (project, base_project, layer_order) VALUES (?, ?, ?)",
                (project, base_project, layer_order),
            )
            conn.commit()
            return cur.lastrowid

    def remove_project_layer(self, project: str, base_project: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM project_layers WHERE project = ? AND base_project = ?",
                (project, base_project),
            )
            conn.commit()
            return cur.rowcount > 0

    def get_effective_facts(
        self,
        project: str,
        data_dir: Path,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Return local + inherited facts, marking inherited_from."""
        local = [f.to_dict() for f in self.list_facts(project, limit=limit)]
        for item in local:
            item["inherited_from"] = None
        seen_ids = {item["id"] for item in local}
        seen_content = {self._content_hash(item["content"]) for item in local}
        layers = self.list_project_layers(project)
        results = list(local)
        for layer in layers:
            base = layer["base_project"]
            base_path = data_dir / "projects" / base / "semantic.db"
            if base == "global":
                base_path = data_dir / "global" / "facts.db"
            if not base_path.exists():
                continue
            base_store = type(self)(base_path, embedder=self.embedder)
            for fact in base_store.list_facts(base if base != "global" else "global", limit=limit):
                h = self._content_hash(fact.content)
                if fact.id in seen_ids or h in seen_content:
                    continue
                d = fact.to_dict()
                d["inherited_from"] = base
                results.append(d)
                seen_content.add(h)
        results.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
        return results[:limit]

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    def get_relationships(
        self,
        project: str,
        source_fact_id: int | None = None,
        target_fact_id: int | None = None,
    ) -> list[dict[str, Any]]:
        base = "SELECT * FROM fact_relationships WHERE project = ?"
        params: list[Any] = [project]
        if source_fact_id is not None:
            base += " AND source_fact_id = ?"
            params.append(source_fact_id)
        if target_fact_id is not None:
            base += " AND target_fact_id = ?"
            params.append(target_fact_id)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(base, params).fetchall()
        return [dict(row) for row in rows]
