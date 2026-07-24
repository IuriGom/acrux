"""Tests for episodic and semantic memory stores."""

from pathlib import Path

import pytest

from acrux.memory.episodic import EpisodicStore
from acrux.memory.semantic import SemanticStore
from acrux.models import Episode, Fact


def test_episodic_add_search_get(tmp_path: Path) -> None:
    store = EpisodicStore(tmp_path / "episodes.db")
    ep = Episode(
        session_id="ep1",
        task="Fix flaky test",
        project="test",
        outcome="success",
        root_cause="race condition",
        fix_pattern="add lock",
        tags=["rust"],
    )
    store.add(ep)
    results = store.search("test", "flaky test")
    assert results and results[0].session_id == "ep1"
    assert store.get_by_id("ep1") is not None


def test_episodic_unreflected(tmp_path: Path) -> None:
    store = EpisodicStore(tmp_path / "episodes.db")
    store.add(Episode(session_id="e1", task="t", project="test", outcome="ok"))
    store.add(Episode(session_id="e2", task="t", project="test", outcome="ok"))
    unreflected = store.get_unreflected("test")
    assert len(unreflected) == 2
    store.mark_compacted(["e1"])
    unreflected = store.get_unreflected("test")
    assert len(unreflected) == 1


@pytest.mark.asyncio
async def test_semantic_add_search(tmp_path: Path) -> None:
    store = SemanticStore(tmp_path / "semantic.db", embedder=None)
    fact = Fact(project="test", content="The project uses async/await patterns.")
    await store.add(fact)
    results = await store.search("test", "async/await")
    assert results
    assert "async/await" in results[0].content


def test_semantic_list_facts(tmp_path: Path) -> None:
    import asyncio

    store = SemanticStore(tmp_path / "semantic.db", embedder=None)
    fact = Fact(project="test", content="Fact one")
    asyncio.run(store.add(fact))
    facts = store.list_facts("test")
    assert facts and facts[0].content == "Fact one"
