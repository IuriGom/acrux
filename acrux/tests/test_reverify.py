"""Tests for fact re-verification selection and stale-fact rehabilitation."""

import asyncio

from acrux.memory.semantic import SemanticStore
from acrux.models import Fact


def _seed(tmp_path) -> SemanticStore:
    store = SemanticStore(tmp_path / "semantic.db", embedder=None)
    for content, confidence in [
        ("Old confident fact about the deploy pipeline", 0.9),
        ("New low-confidence fact about the cache layer", 0.3),
        ("Middle confidence fact about the retry logic", 0.6),
    ]:
        fact = Fact(project="test", content=content, source="s", confidence=confidence)
        asyncio.run(store.add(fact))
    return store


def _find_id(store: SemanticStore, content: str) -> int:
    for fact in store.list_facts("test", limit=100):
        if fact.content == content:
            return fact.id
    raise AssertionError(f"fact not found: {content}")


def test_reverify_targets_stale_then_least_confident(tmp_path) -> None:
    store = _seed(tmp_path)
    stale_id = _find_id(store, "Old confident fact about the deploy pipeline")
    store.record_verification(stale_id, "uncertain")

    candidates = store.get_facts_for_reverify("test", limit=10)

    assert candidates[0].id == stale_id
    assert candidates[0].stale is True
    assert candidates[1].confidence < candidates[2].confidence


def test_yes_verdict_rehabilitates_stale_fact(tmp_path) -> None:
    store = _seed(tmp_path)
    fact_id = _find_id(store, "Old confident fact about the deploy pipeline")
    store.record_verification(fact_id, "uncertain")
    assert store.get_by_id(fact_id).stale is True

    store.record_verification(fact_id, "yes")

    rechecked = store.get_by_id(fact_id)
    assert rechecked.stale is False
    assert rechecked.verified_count == 1
