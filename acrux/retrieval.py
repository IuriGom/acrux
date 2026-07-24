"""Unified retrieval: hybrid search, ranking, inheritance, and budgeted packing."""

from __future__ import annotations

import re
import time
from typing import Any, Protocol

from acrux.models import Fact


class Stores(Protocol):
    semantic: Any
    episodic: Any
    procedural: Any


def rank_skills(skills: list[Any]) -> list[Any]:
    """Rank skills by verification status and success rate."""
    return sorted(skills, key=lambda s: (not s.verified, -s.success_rate, s.name))


async def hybrid_facts(semantic: Any, project: str, query: str, k: int) -> list[Fact]:
    """Vector + FTS5 fusion with reciprocal-rank fusion and outcome re-rank."""
    vector_results = await semantic.search(project, query, k * 2)
    fts_results = semantic.search_fts(project, query, k * 2)

    rrf: dict[int, float] = {}
    for rank, fact in enumerate(vector_results):
        rrf[fact.id] = rrf.get(fact.id, 0.0) + 1.0 / (rank + 60)
    for rank, fact in enumerate(fts_results):
        rrf[fact.id] = rrf.get(fact.id, 0.0) + 1.0 / (rank + 60)

    by_id = {f.id: f for f in vector_results + fts_results}
    scored = []
    for fact_id, score in rrf.items():
        fact = by_id.get(fact_id)
        if not fact:
            continue
        boost = fact.confidence + min(fact.recall_count, 10) * 0.02
        penalty = 0.3 if fact.stale else 0.0
        scored.append((score + boost - penalty, fact))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in scored[:k]]


def inherited_skills(
    procedural_resolver: Any, semantic: Any, project: str, query: str, k: int
) -> list[tuple[str, Any]]:
    """Search skills from base projects and global for cross-project transfer."""
    inherited: list[tuple[str, Any]] = []
    seen: set[str] = set()
    for layer in semantic.list_project_layers(project):
        base = layer["base_project"]
        if base == project:
            continue
        base_proc = procedural_resolver(base)
        for skill in base_proc.search(base, query, k):
            if skill.id in seen:
                continue
            seen.add(skill.id)
            inherited.append((base, skill))
    if project != "global":
        global_proc = procedural_resolver("global")
        for skill in global_proc.search("global", query, k):
            if skill.id in seen:
                continue
            seen.add(skill.id)
            inherited.append(("global", skill))
    return sorted(inherited, key=lambda x: (not x[1].verified, -x[1].success_rate, x[1].name))


def inherited_facts(semantic: Any, project: str, query: str, k: int) -> list[dict[str, Any]]:
    """Return inherited facts from project layers, tagged with source layer."""
    try:
        effective = semantic.get_effective_facts(project, semantic.db_path.parent.parent, limit=k * 4)
    except Exception:
        return []
    terms = [t.lower() for t in query.split() if len(t) > 2]
    if not terms:
        return effective[:k]
    scored = []
    for item in effective:
        content = item.get("content", "").lower()
        score = sum(1 for t in terms if t in content)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:k]]


def pack_context(
    facts: list[Fact],
    episodes: list[Any],
    skills: list[Any],
    inherited_skills: list[tuple[str, Any]],
    inherited_facts: list[dict[str, Any]],
    header_lines: list[str],
    budget_tokens: int = 800,
) -> str:
    """Pack memory into a token budget, highest-value items first, with citations."""
    budget_chars = budget_tokens * 4
    lines = list(header_lines)
    used = sum(len(line) for line in lines)
    overflow = 0

    def try_add(line: str) -> bool:
        nonlocal used, overflow
        if used + len(line) + 1 <= budget_chars:
            lines.append(line)
            used += len(line) + 1
            return True
        overflow += 1
        return False

    if skills:
        lines.append("[Procedural memory]")
        for s in skills:
            proc = " -> ".join(s.procedure[:5])
            if not try_add(f"- [memory:skill:{s.id}] {s.name}: {proc}"):
                break
    if inherited_skills:
        lines.append("[Inherited memory]")
        for base, s in inherited_skills:
            proc = " -> ".join(s.procedure[:5])
            if not try_add(f"- [memory:skill:{s.id}] (from {base}) {s.name}: {proc}"):
                break
    if facts:
        lines.append("[Semantic memory]")
        for f in facts:
            if not try_add(f"- [memory:fact:{f.id}] {f.content}"):
                break
    if inherited_facts:
        for item in inherited_facts:
            src = item.get("inherited_from") or "inherited"
            if not try_add(f"- [memory:fact:{item.get('id')}] (from {src}) {item.get('content', '')}"):
                break
    if episodes:
        lines.append("[Episodic memory]")
        for e in episodes:
            summary = e.fix_pattern or e.root_cause or e.outcome
            if not try_add(f"- [memory:episode:{e.session_id}] {e.task}: {summary}"):
                break

    if overflow:
        lines.append(f"... and {overflow} more memories (truncated to fit token budget)")
    return "\n".join(lines)


async def recall_context(
    stores: Stores,
    procedural_resolver: Any,
    project: str,
    query: str,
    limit: int = 8,
    budget_tokens: int = 800,
) -> str:
    """Build a tagged, budgeted memory context block."""
    if not query.strip():
        return ""
    start = time.time()
    semantic = stores.semantic
    episodic = stores.episodic
    procedural = stores.procedural
    k = max(1, limit // 2)

    facts = await hybrid_facts(semantic, project, query, k)
    episodes = episodic.search_fts(project, query, k) if hasattr(episodic, "search_fts") else episodic.search(project, query, k)
    skills = rank_skills(procedural.search_fts(project, query, k) if hasattr(procedural, "search_fts") else procedural.search(project, query, k))
    inh_skills = inherited_skills(procedural_resolver, semantic, project, query, k)
    inh_facts = inherited_facts(semantic, project, query, k)

    latency_ms = (time.time() - start) * 1000
    try:
        semantic.record_metric(project, "recall_latency_ms", latency_ms)
    except Exception:
        pass

    total = len(facts) + len(episodes) + len(skills) + len(inh_skills) + len(inh_facts)
    if total == 0:
        return (
            "[Memory confidence: low]\n"
            "No relevant memories found. Consider asking the user for more context "
            "or running a quick experiment before proceeding."
        )
    header = ["[Memory confidence: low]"] if total < 2 else []
    return pack_context(facts, episodes, skills, inh_skills, inh_facts, header, budget_tokens)


def record_memory_outcomes(semantic: Any, procedural: Any, memory_context: str, success: bool = True) -> None:
    """Update memory confidence/success rates based on whether they helped."""
    if not memory_context:
        return
    for kind, raw_id in re.findall(r"\[memory:(fact|skill|episode):([^\]]+)\]", memory_context):
        try:
            if kind == "fact":
                semantic.record_outcome(int(raw_id), success)
            elif kind == "skill":
                procedural.update_success(raw_id, success)
        except Exception:
            pass
