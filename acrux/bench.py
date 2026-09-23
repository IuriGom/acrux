"""Public benchmark suite for the Acrux."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from acrux.config import AcruxConfig
from acrux.memory.procedural_db import ProceduralDBStore
from acrux.memory.semantic import SemanticStore

from acrux.utils import utcnow


async def run_benchmark(
    cfg: AcruxConfig, project: str | None = None, k: int = 10, limit: int = 50
) -> dict[str, Any]:
    """Run recall and skill-retrieval benchmarks.

    Returns a JSON-serializable report.
    """
    if project:
        projects = [project]
    else:
        projects = [
            p.name
            for p in cfg.projects_dir.iterdir()
            if p.is_dir() and not p.name.startswith("_")
        ]

    report: dict[str, Any] = {
        "timestamp": utcnow().isoformat(),
        "k": k,
        "limit": limit,
        "projects": {},
    }

    all_fact_recall1: list[float] = []
    all_fact_recall5: list[float] = []
    all_fact_recallk: list[float] = []
    all_skill_recall1: list[float] = []
    all_skill_recall5: list[float] = []
    all_skill_recallk: list[float] = []

    for proj in projects:
        semantic = SemanticStore(
            cfg.projects_dir / proj / "semantic.db", embedder=cfg.create_embedder()
        )
        procedural = ProceduralDBStore(cfg.projects_dir / proj / "skills.db")

        # Fact recall
        facts = semantic.list_facts(proj, limit=limit)
        fact_hits1 = fact_hits5 = fact_hitsk = 0
        for fact in facts:
            query = fact.content[:300]
            results = await semantic.search(proj, query, k)
            ids = [f.id for f in results]
            if fact.id in ids:
                idx = ids.index(fact.id)
                if idx == 0:
                    fact_hits1 += 1
                if idx < 5:
                    fact_hits5 += 1
                fact_hitsk += 1
        fact_total = len(facts)
        fact_metrics = {
            "n": fact_total,
            "recall_at_1": fact_hits1 / fact_total if fact_total else 0.0,
            "recall_at_5": fact_hits5 / fact_total if fact_total else 0.0,
            f"recall_at_{k}": fact_hitsk / fact_total if fact_total else 0.0,
        }

        # Skill retrieval
        skills = procedural.get_all(proj)
        skill_hits1 = skill_hits5 = skill_hitsk = 0
        for skill in skills:
            query = " ".join([skill.name] + skill.preconditions[:3])
            results = procedural.search(proj, query, k)
            ids = [s.id for s in results]
            if skill.id in ids:
                idx = ids.index(skill.id)
                if idx == 0:
                    skill_hits1 += 1
                if idx < 5:
                    skill_hits5 += 1
                skill_hitsk += 1
        skill_total = len(skills)
        skill_metrics = {
            "n": skill_total,
            "recall_at_1": skill_hits1 / skill_total if skill_total else 0.0,
            "recall_at_5": skill_hits5 / skill_total if skill_total else 0.0,
            f"recall_at_{k}": skill_hitsk / skill_total if skill_total else 0.0,
        }

        report["projects"][proj] = {"facts": fact_metrics, "skills": skill_metrics}

        if fact_total:
            all_fact_recall1.append(fact_metrics["recall_at_1"])
            all_fact_recall5.append(fact_metrics["recall_at_5"])
            all_fact_recallk.append(fact_metrics[f"recall_at_{k}"])
        if skill_total:
            all_skill_recall1.append(skill_metrics["recall_at_1"])
            all_skill_recall5.append(skill_metrics["recall_at_5"])
            all_skill_recallk.append(skill_metrics[f"recall_at_{k}"])

    def _avg(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    report["overall"] = {
        "fact_recall_at_1": _avg(all_fact_recall1),
        "fact_recall_at_5": _avg(all_fact_recall5),
        f"fact_recall_at_{k}": _avg(all_fact_recallk),
        "skill_recall_at_1": _avg(all_skill_recall1),
        "skill_recall_at_5": _avg(all_skill_recall5),
        f"skill_recall_at_{k}": _avg(all_skill_recallk),
    }

    return report


def save_report(report: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = report["timestamp"][:10]
    path = out_dir / f"benchmark-{date_str}.json"
    path.write_text(json.dumps(report, indent=2))
    return path
