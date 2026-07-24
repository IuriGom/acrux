"""SQLite-vec backed vector index (incremental, no full rebuilds)."""

from __future__ import annotations

import sqlite3
from array import array
from pathlib import Path

try:
    import sqlite_vec

    SQLITE_VEC_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    SQLITE_VEC_AVAILABLE = False


class SqliteVecIndex:
    """Persistent vector index using the sqlite-vec extension."""

    def __init__(self, db_path: Path, dim: int | None = None, enabled: bool = True):
        self.db_path = db_path
        self.dim = dim
        self.enabled = enabled and SQLITE_VEC_AVAILABLE and dim is not None and dim > 0
        if self.enabled:
            self._init_db()

    @property
    def loaded_from_disk(self) -> bool:
        return self.enabled

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        return conn

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_items USING vec0(fact_id INTEGER PRIMARY KEY, embedding FLOAT[{self.dim}])"
            )

    def _to_blob(self, vector: list[float]) -> bytes:
        return array("f", vector).tobytes()

    def add(self, fact_id: int, vector: list[float]) -> None:
        if not self.enabled or not vector or len(vector) != self.dim:
            return
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO vec_items(fact_id, embedding) VALUES (?, ?)",
                (fact_id, self._to_blob(vector)),
            )

    def load_vector(self, fact_id: int, vector: list[float]) -> None:
        """Restore a vector from persistent storage. For sqlite-vec this just inserts it."""
        self.add(fact_id, vector)

    def remove(self, fact_id: int) -> None:
        if not self.enabled:
            return
        with self._connect() as conn:
            conn.execute("DELETE FROM vec_items WHERE fact_id = ?", (fact_id,))

    def rebuild_hnsw(self) -> None:
        """No-op for sqlite-vec; the index is maintained incrementally."""
        return

    def search(
        self,
        query_vec: list[float],
        k: int = 20,
        filter_ids: set[int] | None = None,
    ) -> list[tuple[int, float]]:
        if not self.enabled or not query_vec or len(query_vec) != self.dim:
            return []
        query_blob = self._to_blob(query_vec)
        with self._connect() as conn:
            if filter_ids:
                placeholders = ",".join("?" for _ in filter_ids)
                rows = conn.execute(
                    f"SELECT fact_id, vec_distance_cosine(embedding, ?) AS distance FROM vec_items WHERE fact_id IN ({placeholders}) ORDER BY distance LIMIT ?",
                    (query_blob, *filter_ids, k),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT fact_id, vec_distance_cosine(embedding, ?) AS distance FROM vec_items ORDER BY distance LIMIT ?",
                    (query_blob, k),
                ).fetchall()
        results = [(row[0], max(0.0, 1.0 - row[1])) for row in rows]
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    @classmethod
    def load_or_init(
        cls,
        index_path: Path,
        dim: int | None,
        enabled: bool = True,
    ) -> "SqliteVecIndex":
        return cls(index_path, dim=dim, enabled=enabled)
