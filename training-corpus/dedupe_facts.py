#!/usr/bin/env python3
"""Remove duplicate facts from the Brain semantic store.

Keeps the earliest fact per (project, content_hash) and deletes the rest,
then rebuilds the vector index once.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT.parent if (_ROOT.parent / "acrux").is_dir() else _ROOT.parent / "brain"))

DB_PATH = Path.home() / ".acrux/data/global/facts.db"


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def main() -> int:
    if not DB_PATH.exists():
        print("No facts DB found.")
        return 0

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, project, content FROM facts").fetchall()

    groups: dict[tuple[str, str], list[int]] = {}
    for row in rows:
        key = (row["project"], _content_hash(row["content"] or ""))
        groups.setdefault(key, []).append(row["id"])

    to_delete: list[int] = []
    for _key, ids in groups.items():
        if len(ids) > 1:
            to_delete.extend(sorted(ids)[1:])

    if not to_delete:
        print("No duplicate facts found.")
        return 0

    print(f"Found {len(to_delete)} duplicate facts to remove.")
    placeholders = ", ".join("?" for _ in to_delete)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f"DELETE FROM facts WHERE id IN ({placeholders})", to_delete)
        conn.execute(f"DELETE FROM fact_embeddings WHERE fact_id IN ({placeholders})", to_delete)
        conn.execute(f"DELETE FROM fact_versions WHERE fact_id IN ({placeholders})", to_delete)
        conn.execute(f"DELETE FROM fact_relationships WHERE source_fact_id IN ({placeholders}) OR target_fact_id IN ({placeholders})", to_delete + to_delete)
        conn.commit()

    from acrux.config import BrainConfig
    from acrux.embeddings import OllamaEmbedder
    from acrux.memory.semantic import SemanticStore

    cfg = BrainConfig.load()
    embedder = cfg.create_embedder()
    store = SemanticStore(DB_PATH, embedder=embedder)
    store.vector_index.rebuild_hnsw()
    print("Vector index rebuilt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
