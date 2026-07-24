"""Optional persistent vector index backed by hnswlib with brute-force fallback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import hnswlib

    HNSWLIB_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    HNSWLIB_AVAILABLE = False


class VectorIndex:
    """In-memory vector index for facts with optional hnswlib acceleration.

    Falls back to brute-force cosine search when hnswlib is unavailable,
    indexing is disabled, or the dimensionality is unknown.
    """

    def __init__(
        self,
        index_path: Path | None = None,
        dim: int | None = None,
        enabled: bool = True,
    ):
        self.index_path = index_path
        self.dim = dim
        self.enabled = enabled and HNSWLIB_AVAILABLE and dim is not None and dim > 0
        self._id_to_index: dict[int, int] = {}
        self._index_to_id: dict[int, int] = {}
        self._vectors: dict[int, list[float]] = {}
        self._index: Any | None = None
        self._loaded_from_disk = False
        if self.enabled:
            self._init_hnsw()

    @property
    def loaded_from_disk(self) -> bool:
        return self._loaded_from_disk

    def _init_hnsw(self) -> None:
        if self.index_path and self.index_path.exists():
            try:
                index = hnswlib.Index(space="cosine", dim=self.dim)
                index.load_index(str(self.index_path), max_elements=0)
                self._index = index
                self._load_metadata()
                self._loaded_from_disk = True
                return
            except Exception:
                self._loaded_from_disk = False
        self._index = hnswlib.Index(space="cosine", dim=self.dim)
        self._index.init_index(max_elements=10000, ef_construction=200, M=16)
        self._index.set_ef(50)

    def _load_metadata(self) -> None:
        meta_path = self._metadata_path()
        if not meta_path or not meta_path.exists():
            return
        try:
            data = json.loads(meta_path.read_text())
            self._id_to_index = {int(k): int(v) for k, v in data.get("id_to_index", {}).items()}
            self._index_to_id = {int(k): int(v) for k, v in data.get("index_to_id", {}).items()}
        except Exception:
            self._id_to_index = {}
            self._index_to_id = {}

    def _save_metadata(self) -> None:
        meta_path = self._metadata_path()
        if not meta_path:
            return
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(
            json.dumps(
                {
                    "id_to_index": {str(k): v for k, v in self._id_to_index.items()},
                    "index_to_id": {str(k): v for k, v in self._index_to_id.items()},
                    "dim": self.dim,
                }
            )
        )

    def _metadata_path(self) -> Path | None:
        if not self.index_path:
            return None
        return self.index_path.with_suffix(self.index_path.suffix + ".meta")

    def add(self, fact_id: int, vector: list[float]) -> None:
        """Add or update a vector in the index."""
        if not vector:
            return
        if fact_id in self._vectors and self.enabled:
            # Replacing an existing vector requires a rebuild because hnswlib
            # does not support deletion.
            self._vectors[fact_id] = vector
            self._rebuild()
            self._persist()
            return
        self._vectors[fact_id] = vector
        if self.enabled and self._index is not None and len(vector) == self.dim:
            idx = len(self._id_to_index)
            self._index.add_items([vector], [idx])
            self._id_to_index[fact_id] = idx
            self._index_to_id[idx] = fact_id
        self._persist()

    def load_vector(self, fact_id: int, vector: list[float]) -> None:
        """Restore a vector from persistent storage without touching hnswlib.

        Used by SemanticStore during startup so that hnswlib mappings loaded
        from disk remain valid.
        """
        if vector:
            self._vectors[fact_id] = vector

    def remove(self, fact_id: int) -> None:
        """Remove a vector from the index.

        hnswlib does not support true deletion, so we rebuild the hnswlib
        index from the remaining vectors when enabled.
        """
        self._vectors.pop(fact_id, None)
        if fact_id in self._id_to_index:
            del self._index_to_id[self._id_to_index[fact_id]]
            del self._id_to_index[fact_id]
            if self.enabled and self._index is not None:
                self._rebuild()
        self._persist()

    def rebuild_hnsw(self) -> None:
        """Rebuild the hnswlib index from the current ``_vectors``."""
        self._rebuild()
        self._persist()

    def _rebuild(self) -> None:
        if not self.enabled or self._index is None:
            return
        self._index = hnswlib.Index(space="cosine", dim=self.dim)
        size = max(10000, len(self._vectors) + 100)
        self._index.init_index(max_elements=size, ef_construction=200, M=16)
        self._index.set_ef(50)
        new_id_to_index: dict[int, int] = {}
        new_index_to_id: dict[int, int] = {}
        vectors: list[list[float]] = []
        labels: list[int] = []
        for fact_id, vector in self._vectors.items():
            # Skip vectors from older embedding models whose dimension no
            # longer matches; hnswlib rejects inhomogeneous arrays.
            if self.dim and len(vector) != self.dim:
                continue
            idx = len(new_id_to_index)
            new_id_to_index[fact_id] = idx
            new_index_to_id[idx] = fact_id
            vectors.append(vector)
            labels.append(idx)
        if vectors:
            self._index.add_items(vectors, labels)
        self._id_to_index = new_id_to_index
        self._index_to_id = new_index_to_id

    def search(
        self,
        query_vec: list[float],
        k: int = 20,
        filter_ids: set[int] | None = None,
    ) -> list[tuple[int, float]]:
        """Return up to ``k`` (fact_id, score) tuples ordered by descending score.

        Score is cosine similarity for brute-force and 1 - distance for hnswlib.
        """
        if not query_vec:
            return []
        if self.enabled and self._index is not None and len(query_vec) == self.dim:
            return self._hnsw_search(query_vec, k, filter_ids)
        return self._brute_search(query_vec, k, filter_ids)

    def _hnsw_search(
        self,
        query_vec: list[float],
        k: int,
        filter_ids: set[int] | None,
    ) -> list[tuple[int, float]]:
        num_elements = len(self._id_to_index)
        query_k = min(k * 4, num_elements) if num_elements > 0 else k
        ef = max(query_k, 50)
        self._index.set_ef(ef)
        labels, distances = self._index.knn_query(query_vec, k=query_k)
        results = []
        for idx, dist in zip(labels[0], distances[0]):
            fact_id = self._index_to_id.get(int(idx))
            if fact_id is None:
                continue
            if filter_ids is not None and fact_id not in filter_ids:
                continue
            score = max(0.0, 1.0 - float(dist))
            results.append((fact_id, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]

    def _brute_search(
        self,
        query_vec: list[float],
        k: int,
        filter_ids: set[int] | None,
    ) -> list[tuple[int, float]]:
        from acrux.embeddings import cosine_similarity

        candidates = self._vectors
        if filter_ids is not None:
            candidates = {fid: vec for fid, vec in self._vectors.items() if fid in filter_ids}
        results = [
            (fid, cosine_similarity(query_vec, vec))
            for fid, vec in candidates.items()
            if len(vec) == len(query_vec)
        ]
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]

    def _persist(self) -> None:
        if not self.index_path:
            return
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        if self.enabled and self._index is not None:
            try:
                self._index.save_index(str(self.index_path))
            except Exception:
                return
        self._save_metadata()

    @classmethod
    def load_or_init(
        cls,
        index_path: Path,
        dim: int | None,
        enabled: bool = True,
    ) -> "VectorIndex":
        return cls(index_path=index_path, dim=dim, enabled=enabled)
