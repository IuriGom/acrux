"""Tests for metrics and code ingestion."""

from pathlib import Path

import pytest

from acrux.ingest import ingest_file
from acrux.memory.semantic import SemanticStore


def test_metrics(tmp_path: Path) -> None:
    store = SemanticStore(tmp_path / "semantic.db", embedder=None)
    store.record_metric("test", "recall_latency_ms", 12.5)
    store.record_metric("test", "recall_latency_ms", 25.0)
    summary = store.get_metric_summary("test", "recall_latency_ms")
    assert summary["count"] == 2
    assert summary["avg"] == pytest.approx(18.75)
    assert summary["min"] == 12.5
    assert summary["max"] == 25.0


@pytest.mark.asyncio
async def test_ingest_python_file(tmp_path: Path) -> None:
    code = '''"""Test module docstring."""

class MyClass:
    """Class docstring."""
    pass

def my_function():
    """Function docstring."""
    return 42
'''
    py_file = tmp_path / "example.py"
    py_file.write_text(code)
    store = SemanticStore(tmp_path / "semantic.db", embedder=None)
    added = await ingest_file(py_file, "test", store)
    assert added >= 3  # module + class + function
    facts = store.list_facts("test")
    contents = [f.content for f in facts]
    assert any("Module example.py" in c for c in contents)
    assert any("Class MyClass" in c for c in contents)
    assert any("Function my_function" in c for c in contents)
