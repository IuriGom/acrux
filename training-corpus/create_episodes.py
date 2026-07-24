#!/usr/bin/env python3
"""Create synthetic training episodes from skills and add them to episodic memory.

Episodes are compact task traces derived from each skill. They give the Brain
concrete examples of how a procedure was applied, which satisfies the episodic
memory coverage requirement without bloating storage.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT.parent if (_ROOT.parent / "acrux").is_dir() else _ROOT.parent / "brain"))

from acrux.config import BrainConfig
from acrux.memory.episodic import EpisodicStore
from acrux.models import Action, Episode

CORPUS_DIR = Path(__file__).resolve().parent


def skill_to_episodes(project: str, skill: dict[str, Any]) -> list[Episode]:
    name = skill.get("name", "")
    preconditions = skill.get("preconditions", [])
    procedure = skill.get("procedure", [])
    tags = [project, "training", "synthetic"]
    if not procedure:
        return []

    actions = [
        Action(tool="reason", target=name, command=p, result="applied")
        for p in procedure[:5]
    ]
    precondition_text = preconditions[0] if preconditions else f"Working on {project} code"
    task = f"{name} in a {project} codebase"
    outcome = f"Successfully applied '{name}'."
    fix_pattern = "; ".join(procedure[:3]) if procedure else ""

    ep = Episode(
        session_id=str(uuid.uuid4()),
        task=task,
        project=project,
        context={"trigger": precondition_text, "domain": project},
        actions=actions,
        outcome=outcome,
        root_cause="",
        fix_pattern=fix_pattern,
        tags=tags,
        timestamp=datetime.utcnow().isoformat(),
        source="training",
    )
    return [ep]


def main() -> int:
    cfg = BrainConfig.load()
    store = EpisodicStore(cfg.data_dir / "global" / "episodes.db")

    total = 0
    for skills_file in sorted(CORPUS_DIR.glob("*/skills.yaml")):
        project = skills_file.parent.name
        data = yaml.safe_load(skills_file.read_text(encoding="utf-8")) or []
        added = 0
        for skill_data in data:
            for ep in skill_to_episodes(project, skill_data):
                store.add(ep)
                added += 1
        print(f"{project}: {added} episodes")
        total += added

    print(f"\nTotal episodes added: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
