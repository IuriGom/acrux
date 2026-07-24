"""Tests for continuous evaluation and code dependency edges."""

from pathlib import Path

import pytest

from acrux.ingest import ingest_file
from acrux.memory.semantic import SemanticStore
from acrux.models import Fact


def test_record_outcome(tmp_path: Path) -> None:
    import asyncio

    store = SemanticStore(tmp_path / "semantic.db", embedder=None)
    fact = Fact(project="test", content="Useful fact")
    asyncio.run(store.add(fact))
    fact_id = fact.id
    store.record_outcome(fact_id, success=True)
    updated = store.get_by_id(fact_id)
    assert updated.verified_count == 1
    store.record_outcome(fact_id, success=False)
    updated = store.get_by_id(fact_id)
    assert updated.contradicted_count == 1


@pytest.mark.asyncio
async def test_ingest_dependency_edges(tmp_path: Path) -> None:
    code = """import os
import sys
from pathlib import Path

def main():
    pass
"""
    py_file = tmp_path / "deps.py"
    py_file.write_text(code)
    store = SemanticStore(tmp_path / "semantic.db", embedder=None)
    await ingest_file(py_file, "test", store)
    deps = store.get_dependencies("test")
    assert deps
    targets = {d["target_ref"] for d in deps}
    assert "os" in targets
    assert "sys" in targets
    assert "pathlib.Path" in targets
