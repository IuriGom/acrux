"""Tests for FTS5 retrieval, skill rendering, and context packing."""

from pathlib import Path

import pytest

from acrux.memory.procedural_db import ProceduralDBStore
from acrux.memory.semantic import SemanticStore
from acrux.models import Fact, Skill
from acrux.skills import expand_composition, render_skill


@pytest.mark.asyncio
async def test_fts5_search(tmp_path: Path) -> None:
    store = SemanticStore(tmp_path / "semantic.db", embedder=None)
    await store.add(Fact(project="test", content="Race conditions in auth modules are fixed with locks."))
    await store.add(Fact(project="test", content="Database connections should use context managers."))
    results = store.search_fts("test", "race conditions locks")
    assert results
    assert "Race conditions" in results[0].content


def test_render_skill_parameters() -> None:
    skill = Skill(
        project="test",
        name="run_tests",
        procedure=["run {test_command} in {dir}"],
        parameters={"test_command": "pytest tests/", "dir": "."},
    )
    rendered = render_skill(skill, {"test_command": "make test", "dir": "src"})
    assert rendered.procedure == ["run make test in src"]


def test_expand_composition(tmp_path: Path) -> None:
    store = ProceduralDBStore(tmp_path / "skills.db")
    child = Skill(project="test", name="child", procedure=["step A", "step B"])
    store.add(child)
    parent = Skill(project="test", name="parent", procedure=["step 1"], composition=[child.id])
    store.add(parent)
    expanded = expand_composition(parent, store)
    assert "step 1" in expanded.procedure
    assert "step A" in expanded.procedure
    assert "step B" in expanded.procedure
