#!/usr/bin/env python3
"""Verify Brain recall across all training topics.

Runs one semantic recall query per topic and prints top results.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT.parent if (_ROOT.parent / "acrux").is_dir() else _ROOT.parent / "brain"))

from acrux.config import BrainConfig
from acrux.embeddings import OllamaEmbedder
from acrux.memory.semantic import SemanticStore
from acrux.memory.procedural import ProceduralStore

QUERIES = {
    "swift": "How do I safely unwrap an optional in Swift?",
    "rust": "How do I handle ownership and borrowing in Rust?",
    "python": "What are Python list comprehensions best practices?",
    "cpp": "When should I use move semantics in C++?",
    "vision": "How do I preprocess images for a neural network?",
    "general-coding": "What makes code maintainable and readable?",
    "algorithms": "Explain dynamic programming with memoization.",
    "debugging": "How do I debug a race condition?",
    "security": "What are common web application vulnerabilities?",
    "tools": "How do I resolve a Git merge conflict?",
}


async def main() -> int:
    cfg = BrainConfig.load()
    embedder = cfg.create_embedder()
    if not embedder:
        print("No embedder configured")
        return 1

    semantic = SemanticStore(cfg.data_dir / "global" / "facts.db", embedder=embedder)
    procedural = ProceduralStore(cfg.data_dir / "global" / "skills.yaml")

    print(f"{'Topic':<18} {'Facts':>8} {'Skills':>8}")
    print("-" * 38)
    for topic in sorted(QUERIES):
        facts = semantic.list_facts(project=topic, limit=1)
        skills = procedural.get_all(project=topic)
        print(f"{topic:<18} {len(facts):>8} {len(skills):>8}")

    print("\nRecall verification:")
    for topic, query in QUERIES.items():
        results = await semantic.search(project=topic, query=query, limit=3)
        print(f"\n[{topic}] query: {query}")
        if not results:
            print("  ⚠️  no results")
            continue
        for i, fact in enumerate(results, 1):
            preview = fact.content.replace("\n", " ")[:160]
            print(f"  {i}. {preview}...")

    await embedder.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
