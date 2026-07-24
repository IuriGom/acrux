"""Tests for W5: test-file 'tests' edges and same-file 'calls' edges."""

from pathlib import Path

import pytest

from acrux.ingest import _is_test_file, _load_ts_parser, ingest_file
from acrux.memory.semantic import SemanticStore


def _require(lang: str) -> None:
    if _load_ts_parser(lang) is None:
        pytest.skip(f"tree-sitter grammar for {lang} not available")


async def _ingest(tmp_path: Path, name: str, code: str) -> SemanticStore:
    src = tmp_path / name
    src.write_text(code)
    store = SemanticStore(tmp_path / f"{name.replace('.', '_')}.db", embedder=None)
    await ingest_file(src, "test", store)
    return store


def _deps(store: SemanticStore, dependency_type: str) -> list[dict]:
    return [d for d in store.get_dependencies("test") if d["dependency_type"] == dependency_type]


def _call_pairs(store: SemanticStore) -> set[tuple[str, str]]:
    return {(d["source_ref"], d["target_ref"]) for d in _deps(store, "calls")}


def _test_targets(store: SemanticStore) -> set[str]:
    return {d["target_ref"] for d in _deps(store, "tests")}


def test_is_test_file() -> None:
    assert _is_test_file(Path("test_ingest.py"))
    assert not _is_test_file(Path("ingest.py"))
    assert not _is_test_file(Path("contest.py"))
    assert _is_test_file(Path("widget.test.ts"))
    assert _is_test_file(Path("widget.test.tsx"))
    assert _is_test_file(Path("widget.test.js"))
    assert not _is_test_file(Path("widget.ts"))
    assert not _is_test_file(Path("latest.ts"))
    assert _is_test_file(Path("server_test.go"))
    assert not _is_test_file(Path("server.go"))


@pytest.mark.asyncio
async def test_python_test_file_records_tests_edges(tmp_path: Path) -> None:
    code = """import os
from pkg import mod

def test_something():
    assert mod.run()
"""
    store = await _ingest(tmp_path, "test_mod.py", code)
    assert {"os", "pkg.mod"} <= _test_targets(store)
    # Test files record 'tests' edges, not 'imports' edges.
    assert _deps(store, "imports") == []
    for dep in _deps(store, "tests"):
        assert dep["source_ref"].endswith("test_mod.py")
        assert dep["source_type"] == "file"
        assert dep["target_type"] == "module"


@pytest.mark.asyncio
async def test_python_non_test_file_keeps_imports_edges(tmp_path: Path) -> None:
    store = await _ingest(tmp_path, "mod.py", "import os\n")
    assert _test_targets(store) == set()
    assert {d["target_ref"] for d in _deps(store, "imports")} == {"os"}


@pytest.mark.asyncio
async def test_python_calls_edges(tmp_path: Path) -> None:
    code = """import os

def helper():
    return 1

def main():
    print(helper())
    os.getcwd()

class Service:
    def run(self):
        self.load()
        helper()

    def load(self):
        pass
"""
    store = await _ingest(tmp_path, "app.py", code)
    pairs = _call_pairs(store)
    assert ("main", "helper") in pairs
    assert ("main", "print") in pairs
    assert ("main", "getcwd") in pairs  # os.getcwd() -> getcwd
    assert ("run", "load") in pairs  # self.load() -> load
    assert ("run", "helper") in pairs
    # helper() makes no calls
    assert not any(src == "helper" for src, _ in pairs)
    for dep in _deps(store, "calls"):
        assert dep["source_type"] == "function"
        assert dep["target_type"] == "function"


@pytest.mark.asyncio
async def test_python_calls_respect_nested_scopes(tmp_path: Path) -> None:
    code = """def inner_target():
    pass

def outer():
    def inner():
        inner_target()
    inner()
"""
    store = await _ingest(tmp_path, "nested.py", code)
    pairs = _call_pairs(store)
    assert ("inner", "inner_target") in pairs
    assert ("outer", "inner") in pairs
    # The call inside inner() belongs to inner, not outer.
    assert ("outer", "inner_target") not in pairs


@pytest.mark.asyncio
async def test_javascript_calls_edges(tmp_path: Path) -> None:
    _require("javascript")
    code = """
function helper() { return 1; }

function main() {
  const x = helper();
  console.log(x);
  obj.method(x);
}

const add = (a, b) => a + b;

function outer() {
  add(1, 2);
  function inner() { helper(); }
  inner();
}
"""
    store = await _ingest(tmp_path, "app.js", code)
    pairs = _call_pairs(store)
    assert ("main", "helper") in pairs
    assert ("main", "log") in pairs  # console.log() -> log
    assert ("main", "method") in pairs  # obj.method() -> method
    assert ("outer", "add") in pairs  # arrow function assigned to const
    assert ("outer", "inner") in pairs
    assert ("inner", "helper") in pairs
    # Nested function body is not attributed to the outer function.
    assert ("outer", "helper") not in pairs


@pytest.mark.asyncio
async def test_ts_test_file_records_tests_edges(tmp_path: Path) -> None:
    _require("typescript")
    code = """
import { render } from "./render";

function spec(): void {
  render();
}
"""
    store = await _ingest(tmp_path, "widget.test.ts", code)
    assert "./render" in _test_targets(store)
    assert _deps(store, "imports") == []
    assert ("spec", "render") in _call_pairs(store)


@pytest.mark.asyncio
async def test_go_test_file_records_tests_edges(tmp_path: Path) -> None:
    _require("go")
    code = """
package main

import "testing"

func helper() {}

func TestServer(t *testing.T) {
    helper()
}
"""
    store = await _ingest(tmp_path, "server_test.go", code)
    assert "testing" in _test_targets(store)
    assert _deps(store, "imports") == []
    assert ("TestServer", "helper") in _call_pairs(store)


@pytest.mark.asyncio
async def test_go_calls_edges(tmp_path: Path) -> None:
    _require("go")
    code = """
package main

import "fmt"

func helper() int { return 1 }

func main() {
    fmt.Println(helper())
}
"""
    store = await _ingest(tmp_path, "main.go", code)
    pairs = _call_pairs(store)
    assert ("main", "helper") in pairs
    assert ("main", "Println") in pairs  # fmt.Println() -> Println


@pytest.mark.asyncio
async def test_rust_calls_edges(tmp_path: Path) -> None:
    _require("rust")
    code = """
struct Config {}

impl Config {
    fn new() -> Self { Config {} }
}

fn helper() {}

fn main() {
    let _c = Config::new();
    helper();
}
"""
    store = await _ingest(tmp_path, "main.rs", code)
    pairs = _call_pairs(store)
    assert ("main", "helper") in pairs
    assert ("main", "new") in pairs  # Config::new() -> new
