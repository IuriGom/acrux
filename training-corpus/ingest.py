#!/usr/bin/env python3
"""Ingest brain-training-corpus markdown into the Brain memory stores.

Usage:
    cd brain-training-corpus
    python ingest.py
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
for _candidate in (_ROOT.parent, _ROOT.parent / "brain"):
    if (_candidate / "acrux").is_dir():
        sys.path.insert(0, str(_candidate))
        break

from acrux.config import BrainConfig
from acrux.embeddings import OllamaEmbedder
from acrux.memory.episodic import EpisodicStore
from acrux.memory.procedural import ProceduralStore
from acrux.memory.semantic import SemanticStore
from acrux.models import Fact, Skill, Episode

CORPUS_DIR = Path(__file__).resolve().parent
MAX_FACT_BYTES = 4000
BATCH_SIZE = 64


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def _chunk_markdown(path: Path, max_bytes: int = MAX_FACT_BYTES) -> list[dict[str, Any]]:
    """Split a markdown file into chunks preserving headings as context."""
    text = path.read_text(encoding="utf-8", errors="replace")
    chunks: list[dict[str, Any]] = []
    current_heading = ""
    current_body: list[str] = []

    def flush():
        if not current_body:
            return
        body = "\n".join(current_body).strip()
        if not body:
            return
        prefix = f"{current_heading}\n\n" if current_heading else ""
        full = f"{prefix}{body}"
        # Split oversized bodies by paragraphs.
        if len(full.encode("utf-8")) > max_bytes:
            parts: list[str] = []
            buf = prefix
            for para in body.split("\n\n"):
                if not para.strip():
                    continue
                if len((buf + para).encode("utf-8")) > max_bytes and buf.strip():
                    parts.append(buf.strip())
                    buf = f"{current_heading}\n\n" if current_heading else ""
                buf += para + "\n\n"
            if buf.strip():
                parts.append(buf.strip())
            for part in parts:
                chunks.append({"content": part, "heading": current_heading})
        else:
            chunks.append({"content": full, "heading": current_heading})
        current_body.clear()

    for line in text.splitlines():
        if line.startswith("#"):
            flush()
            current_heading = line.lstrip("# ").strip()
        else:
            current_body.append(line)
    flush()
    return chunks


def _load_skills_yaml(path: Path) -> list[Skill]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [Skill.from_dict(item) for item in data]


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _known_hashes(semantic: SemanticStore) -> set[str]:
    """Load all existing content hashes from the semantic store."""
    with sqlite3.connect(semantic.db_path) as conn:
        rows = conn.execute("SELECT content_hash FROM fact_embeddings").fetchall()
    return {r[0] for r in rows if r[0]}


async def ingest_topic(
    topic_dir: Path,
    semantic: SemanticStore,
    procedural: ProceduralStore,
    episodic: EpisodicStore,
    existing_hashes: set[str],
) -> dict[str, int]:
    topic = topic_dir.name
    facts_added = 0
    skills_added = 0
    episodes_added = 0

    # Ingest markdown facts.
    md_files = sorted(topic_dir.glob("*.md"))
    for md in md_files:
        if md.name == "README.md":
            continue
        chunks = _chunk_markdown(md)
        for i, chunk in enumerate(chunks):
            content = chunk["content"]
            if len(content.encode("utf-8")) < 40:
                continue
            chash = _content_hash(content)
            if chash in existing_hashes:
                continue
            fact = Fact(
                project=topic,
                content=content,
                source=f"training:{topic}/{md.name}:chunk{i}",
                tags=[topic, _slug(chunk["heading"])] if chunk["heading"] else [topic],
                timestamp=datetime.utcnow().isoformat(),
            )
            await semantic.add(fact)
            existing_hashes.add(chash)
            facts_added += 1

    # Ingest skills.
    skills_file = topic_dir / "skills.yaml"
    if skills_file.exists():
        for skill in _load_skills_yaml(skills_file):
            skill.project = topic
            procedural.add(skill)
            skills_added += 1

    # Ingest episodes (task traces) if present.
    episodes_file = topic_dir / "episodes.yaml"
    if episodes_file.exists():
        import yaml

        for ep_data in yaml.safe_load(episodes_file.read_text(encoding="utf-8")) or []:
            ep = Episode.from_dict(ep_data)
            ep.project = topic
            episodic.add(ep)
            episodes_added += 1

    return {"facts": facts_added, "skills": skills_added, "episodes": episodes_added}


async def main() -> int:
    cfg = BrainConfig.load()
    embedder = cfg.create_embedder()

    semantic = SemanticStore(cfg.data_dir / "global" / "facts.db", embedder=embedder)
    episodic = EpisodicStore(cfg.data_dir / "global" / "episodes.db")
    procedural = ProceduralStore(cfg.data_dir / "global" / "skills.yaml")

    totals = {"facts": 0, "skills": 0, "episodes": 0}
    start = time.time()

    topic_dirs = [d for d in sorted(CORPUS_DIR.iterdir()) if d.is_dir()]
    print(f"Ingesting {len(topic_dirs)} topics into {cfg.data_dir} ...")

    existing_hashes = _known_hashes(semantic)
    print(f"  {len(existing_hashes)} existing fact hashes; skipping duplicates.")

    for topic_dir in topic_dirs:
        topic = topic_dir.name
        print(f"  {topic} ...", end="", flush=True)
        counts = await ingest_topic(topic_dir, semantic, procedural, episodic, existing_hashes)
        print(
            f" facts={counts['facts']}, skills={counts['skills']}, episodes={counts['episodes']}"
        )
        for k in totals:
            totals[k] += counts[k]

    await embedder.close()
    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.1f}s: {totals}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
