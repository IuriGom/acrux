"""Tests for unified recall and context packing."""

import asyncio
from pathlib import Path
from types import SimpleNamespace

from acrux.models import Fact
from acrux.retrieval import recall_context

LOCAL_FACT = Fact(
    id=18,
    project="brain",
    content="Brain data is stored under ~/.brain with per-project folders",
    source="s1",
    confidence=0.9,
)
INHERITED_FACT = Fact(
    id=99,
    project="brain",
    content="Brain debug workflow starts with the log tail command",
    source="s2",
    confidence=0.7,
)


class FakeSemantic:
    db_path = Path("/tmp/acrux-test/semantic.db")

    async def search(self, project: str, query: str, k: int) -> list[Fact]:
        return [LOCAL_FACT]

    def search_fts(self, project: str, query: str, k: int) -> list[Fact]:
        return []

    def list_project_layers(self, project: str) -> list[dict]:
        return []

    def get_effective_facts(self, project: str, root: Path, limit: int) -> list[dict]:
        return [
            {"id": LOCAL_FACT.id, "content": LOCAL_FACT.content, "inherited_from": "base"},
            {"id": INHERITED_FACT.id, "content": INHERITED_FACT.content, "inherited_from": "base"},
        ]

    def record_metric(self, *args) -> None:
        pass


class FakeEpisodic:
    def search(self, project: str, query: str, k: int) -> list:
        return []


class FakeProcedural:
    def search(self, project: str, query: str, k: int) -> list:
        return []


def test_recall_context_dedupes_inherited_facts() -> None:
    stores = SimpleNamespace(
        semantic=FakeSemantic(), episodic=FakeEpisodic(), procedural=FakeProcedural()
    )
    context = asyncio.run(
        recall_context(stores, lambda p: FakeProcedural(), "brain", "brain data", 8)
    )
    assert context.count("[memory:fact:18]") == 1
    assert "[memory:fact:99]" in context
