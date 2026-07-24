"""Skill preparation: parameter filling, composition, and executable preconditions."""

from __future__ import annotations

from acrux.memory.procedural_db import ProceduralDBStore
from acrux.memory.semantic import SemanticStore
from acrux.models import Skill
from acrux.sandbox import run_sandboxed


def render_skill(skill: Skill, parameters: dict[str, str]) -> Skill:
    """Return a copy of the skill with parameter slots filled."""
    rendered = Skill.from_dict(skill.to_dict())
    rendered.procedure = [
        step.format(**parameters) if parameters else step for step in rendered.procedure
    ]
    rendered.preconditions = [
        pre.format(**parameters) if parameters else pre for pre in rendered.preconditions
    ]
    return rendered


def expand_composition(skill: Skill, procedural: ProceduralDBStore, depth: int = 0) -> Skill:
    """Expand a skill's composition into a flat procedure."""
    if depth > 3 or not skill.composition:
        return skill
    expanded = Skill.from_dict(skill.to_dict())
    new_procedure: list[str] = []
    for step in expanded.procedure:
        new_procedure.append(step)
    for child_id in skill.composition:
        child = procedural.get_by_id(child_id)
        if not child:
            continue
        child_expanded = expand_composition(child, procedural, depth + 1)
        new_procedure.append(f"# from {child.name}")
        new_procedure.extend(child_expanded.procedure)
    expanded.procedure = new_procedure
    return expanded


async def check_preconditions(skill: Skill, workspace: str) -> tuple[bool, list[str]]:
    """Run executable precondition checks in a sandbox."""
    errors: list[str] = []
    for check in skill.precondition_checks:
        exit_code, output = await run_sandboxed(check, workspace, timeout=30)
        if exit_code != 0:
            errors.append(f"precondition failed: {check} ({output[:100]})")
    return not errors, errors


async def prepare_skill_for_use(
    skill: Skill,
    project: str,
    semantic: SemanticStore,
    procedural: ProceduralDBStore,
    workspace: str = ".",
) -> Skill:
    """Fill parameters from project facts, expand composition, and check preconditions."""
    # Fill parameters from project facts matching parameter names
    parameters: dict[str, str] = {}
    for name in skill.parameters:
        facts = await semantic.search(project, name, 1)
        if facts:
            parameters[name] = facts[0].content
        else:
            parameters[name] = skill.parameters[name]
    rendered = render_skill(skill, parameters)
    expanded = expand_composition(rendered, procedural)
    if skill.precondition_checks:
        ok, errors = await check_preconditions(expanded, workspace)
        if not ok:
            # Mark as failed precondition without changing the stored skill
            expanded.verified = False
            expanded.evidence.append({"precondition_errors": errors})
    return expanded
