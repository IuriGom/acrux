"""Tests for cross-file call graph resolution in the Python AST ingestion.

Calls to imported functions record additional 'calls' edges whose targets are
module-qualified (``module.func``), while same-file bare-name edges are kept
as-is.
"""

from pathlib import Path

import pytest

from acrux.ingest import _py_import_map, ingest_file
from acrux.memory.semantic import SemanticStore


async def _ingest(tmp_path: Path, name: str, code: str) -> SemanticStore:
    src = tmp_path / name
    src.write_text(code)
    store = SemanticStore(tmp_path / f"{name.replace('.', '_')}.db", embedder=None)
    await ingest_file(src, "test", store)
    return store


def _call_pairs(store: SemanticStore) -> set[tuple[str, str]]:
    return {
        (d["source_ref"], d["target_ref"])
        for d in store.get_dependencies("test")
        if d["dependency_type"] == "calls"
    }


@pytest.mark.asyncio
async def test_from_import_call_resolves_to_module_func(tmp_path: Path) -> None:
    code = """from helpers import compute

def main():
    compute()
"""
    store = await _ingest(tmp_path, "app.py", code)
    pairs = _call_pairs(store)
    assert ("main", "helpers.compute") in pairs
    # Same-file bare-name edge is kept as-is.
    assert ("main", "compute") in pairs


@pytest.mark.asyncio
async def test_plain_import_attribute_call_resolves(tmp_path: Path) -> None:
    code = """import helpers

def main():
    helpers.compute()
"""
    store = await _ingest(tmp_path, "app.py", code)
    pairs = _call_pairs(store)
    assert ("main", "helpers.compute") in pairs
    assert ("main", "compute") in pairs


@pytest.mark.asyncio
async def test_aliased_import_resolves_to_real_module(tmp_path: Path) -> None:
    code = """import helpers as h

def main():
    h.compute()
"""
    store = await _ingest(tmp_path, "app.py", code)
    pairs = _call_pairs(store)
    assert ("main", "helpers.compute") in pairs
    assert ("main", "h.compute") not in pairs


@pytest.mark.asyncio
async def test_from_import_alias_resolves_to_module_func(tmp_path: Path) -> None:
    code = """from helpers import compute as run

def main():
    run()
"""
    store = await _ingest(tmp_path, "app.py", code)
    pairs = _call_pairs(store)
    assert ("main", "helpers.compute") in pairs


@pytest.mark.asyncio
async def test_dotted_import_call_resolves_full_chain(tmp_path: Path) -> None:
    code = """import pkg.sub

def main():
    pkg.sub.compute()
"""
    store = await _ingest(tmp_path, "app.py", code)
    pairs = _call_pairs(store)
    assert ("main", "pkg.sub.compute") in pairs


@pytest.mark.asyncio
async def test_from_import_module_then_attribute_call(tmp_path: Path) -> None:
    code = """from pkg import sub

def main():
    sub.compute()
"""
    store = await _ingest(tmp_path, "app.py", code)
    pairs = _call_pairs(store)
    assert ("main", "pkg.sub.compute") in pairs


@pytest.mark.asyncio
async def test_same_file_calls_unchanged(tmp_path: Path) -> None:
    code = """from helpers import compute

def local():
    return 1

def main():
    local()
    obj.method()
    compute()
"""
    store = await _ingest(tmp_path, "app.py", code)
    pairs = _call_pairs(store)
    # Same-file calls stay bare.
    assert ("main", "local") in pairs
    assert ("main", "method") in pairs  # obj.method() -> method
    # Non-imported attribute roots are not module-qualified.
    assert ("main", "obj.method") not in pairs
    # No spurious qualified edge for a locally-defined name.
    assert not any(target.endswith(".local") for _, target in pairs)


@pytest.mark.asyncio
async def test_local_definition_shadows_import(tmp_path: Path) -> None:
    code = """from helpers import compute

def compute():
    return 2

def main():
    compute()
"""
    store = await _ingest(tmp_path, "app.py", code)
    pairs = _call_pairs(store)
    assert ("main", "compute") in pairs
    # The local def shadows the import; no cross-file edge.
    assert ("main", "helpers.compute") not in pairs


@pytest.mark.asyncio
async def test_methods_and_nested_scopes_resolve(tmp_path: Path) -> None:
    code = """from helpers import compute

class Service:
    def run(self):
        compute()

def outer():
    def inner():
        compute()
    inner()
"""
    store = await _ingest(tmp_path, "app.py", code)
    pairs = _call_pairs(store)
    assert ("run", "helpers.compute") in pairs
    assert ("inner", "helpers.compute") in pairs
    # The call inside inner() is not attributed to outer().
    assert ("outer", "helpers.compute") not in pairs
    assert ("outer", "inner") in pairs


@pytest.mark.asyncio
async def test_relative_from_import_falls_back_to_bare_name(tmp_path: Path) -> None:
    code = """from . import sibling

def main():
    sibling()
"""
    store = await _ingest(tmp_path, "app.py", code)
    pairs = _call_pairs(store)
    # No module prefix available; the bare-name edge is kept and nothing breaks.
    assert ("main", "sibling") in pairs


@pytest.mark.asyncio
async def test_import_edges_still_recorded(tmp_path: Path) -> None:
    code = """import os
from helpers import compute

def main():
    compute()
"""
    store = await _ingest(tmp_path, "app.py", code)
    imports = {
        d["target_ref"]
        for d in store.get_dependencies("test")
        if d["dependency_type"] == "imports"
    }
    assert {"os", "helpers.compute"} <= imports


def test_py_import_map() -> None:
    import ast

    tree = ast.parse(
        "import os\n"
        "import pkg.sub as ps\n"
        "import a.b\n"
        "from helpers import compute\n"
        "from utils import run as go\n"
        "from . import sibling\n"
    )
    mapping = _py_import_map(tree)
    assert mapping["os"] == "os"
    assert mapping["ps"] == "pkg.sub"
    assert mapping["a"] == "a"
    assert mapping["compute"] == "helpers.compute"
    assert mapping["go"] == "utils.run"
    assert mapping["sibling"] == "sibling"
