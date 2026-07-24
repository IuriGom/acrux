"""Tests for tree-sitter based code ingestion (JS/TS, Go, Rust, Java, C/C++, Swift)."""

from pathlib import Path

import pytest

from acrux.ingest import _load_ts_parser, ingest_directory, ingest_file
from acrux.memory.semantic import SemanticStore


def _require(lang: str) -> None:
    if _load_ts_parser(lang) is None:
        pytest.skip(f"tree-sitter grammar for {lang} not available")


async def _ingest(tmp_path: Path, name: str, code: str) -> tuple[int, SemanticStore]:
    src = tmp_path / name
    src.write_text(code)
    store = SemanticStore(tmp_path / "semantic.db", embedder=None)
    added = await ingest_file(src, "test", store)
    return added, store


def _contents(store: SemanticStore) -> list[str]:
    return [f.content for f in store.list_facts("test")]


def _dep_targets(store: SemanticStore) -> set[str]:
    return {d["target_ref"] for d in store.get_dependencies("test")}


@pytest.mark.asyncio
async def test_ingest_javascript(tmp_path: Path) -> None:
    _require("javascript")
    code = """
import React from "react";
import { helper } from "./util";

export class App extends React.Component {
  render() { return null; }
}

function helper() { return 42; }
const add = (a, b) => a + b;
const mul = function(a, b) { return a * b; };
"""
    added, store = await _ingest(tmp_path, "app.js", code)
    assert added >= 5
    contents = _contents(store)
    assert any("Class App in app.js" in c for c in contents)
    assert any("Method render in app.js" in c for c in contents)
    assert any("Function helper in app.js" in c for c in contents)
    assert any("Function add in app.js" in c for c in contents)
    assert any("Function mul in app.js" in c for c in contents)
    assert {"react", "./util"} <= _dep_targets(store)


@pytest.mark.asyncio
async def test_ingest_typescript(tmp_path: Path) -> None:
    _require("typescript")
    code = """
import { Service } from "./service";

interface Shape { area(): number; }
enum Color { Red, Blue }

class Circle implements Shape {
  area(): number { return 3.14; }
}

function make(r: number): Circle { return new Circle(); }
const sq = (n: number): number => n * n;
"""
    added, store = await _ingest(tmp_path, "shapes.ts", code)
    assert added >= 5
    contents = _contents(store)
    assert any("Class Shape in shapes.ts" in c for c in contents)
    assert any("Class Color in shapes.ts" in c for c in contents)
    assert any("Class Circle in shapes.ts" in c for c in contents)
    assert any("Method area in shapes.ts" in c for c in contents)
    assert any("Function make in shapes.ts" in c for c in contents)
    assert any("Function sq in shapes.ts" in c for c in contents)
    assert "./service" in _dep_targets(store)


@pytest.mark.asyncio
async def test_ingest_go(tmp_path: Path) -> None:
    _require("go")
    code = """
package main

import (
    "fmt"
    "os"
)

type Server struct {
    port int
}

type Runner interface {
    Run() error
}

func NewServer() *Server { return &Server{} }

func (s *Server) Start() error {
    fmt.Println("hi")
    return nil
}
"""
    added, store = await _ingest(tmp_path, "server.go", code)
    assert added >= 4
    contents = _contents(store)
    assert any("Class Server in server.go" in c for c in contents)
    assert any("Class Runner in server.go" in c for c in contents)
    assert any("Function NewServer in server.go" in c for c in contents)
    assert any("Method Start in server.go" in c for c in contents)
    assert {"fmt", "os"} <= _dep_targets(store)


@pytest.mark.asyncio
async def test_ingest_rust(tmp_path: Path) -> None:
    _require("rust")
    code = """
use std::collections::HashMap;
use crate::foo::bar;

pub struct Config {
    pub name: String,
}

pub enum Mode { Fast, Slow }

pub trait Run {
    fn run(&self);
}

impl Config {
    pub fn new(name: &str) -> Self { Config { name: name.into() } }
}

fn main() { let _ = Config::new("x"); }
"""
    added, store = await _ingest(tmp_path, "main.rs", code)
    assert added >= 6
    contents = _contents(store)
    assert any("Class Config in main.rs" in c for c in contents)
    assert any("Class Mode in main.rs" in c for c in contents)
    assert any("Class Run in main.rs" in c for c in contents)
    assert any("Method run in main.rs" in c for c in contents)
    assert any("Method new in main.rs" in c for c in contents)
    assert any("Function main in main.rs" in c for c in contents)
    assert {"std::collections::HashMap", "crate::foo::bar"} <= _dep_targets(store)


@pytest.mark.asyncio
async def test_ingest_java(tmp_path: Path) -> None:
    _require("java")
    code = """
package com.example;

import java.util.List;
import static java.lang.Math.PI;

public class App extends Base {
    private int x;
    public App(int x) { this.x = x; }
    public int compute(List<String> items) { return items.size(); }
}

interface Worker { void work(); }
"""
    added, store = await _ingest(tmp_path, "App.java", code)
    assert added >= 4
    contents = _contents(store)
    assert any("Class App in App.java" in c for c in contents)
    assert any("Class Worker in App.java" in c for c in contents)
    assert any("Method compute in App.java" in c for c in contents)
    assert any("Method App in App.java" in c for c in contents)  # constructor
    assert {"java.util.List", "java.lang.Math.PI"} <= _dep_targets(store)


@pytest.mark.asyncio
async def test_ingest_c(tmp_path: Path) -> None:
    _require("c")
    code = """
#include <stdio.h>
#include "local.h"

static int add(int a, int b) { return a + b; }

int main(void) {
    printf("%d", add(1, 2));
    return 0;
}
"""
    added, store = await _ingest(tmp_path, "main.c", code)
    assert added >= 2
    contents = _contents(store)
    assert any("Function add in main.c" in c for c in contents)
    assert any("Function main in main.c" in c for c in contents)
    assert {"stdio.h", "local.h"} <= _dep_targets(store)


@pytest.mark.asyncio
async def test_ingest_cpp(tmp_path: Path) -> None:
    _require("cpp")
    code = """
#include <vector>
#include "util.hpp"

class Engine {
public:
    Engine();
    void start() { }
    int power() const;
};

int Engine::power() const { return 42; }

struct Point { int x; int y; };

template <typename T>
T maximum(T a, T b) { return a > b ? a : b; }

int main() { Engine e; e.start(); return 0; }
"""
    added, store = await _ingest(tmp_path, "engine.cpp", code)
    assert added >= 5
    contents = _contents(store)
    assert any("Class Engine in engine.cpp" in c for c in contents)
    assert any("Class Point in engine.cpp" in c for c in contents)
    assert any("Method start in engine.cpp" in c for c in contents)
    assert any("Function power in engine.cpp" in c for c in contents)
    assert any("Function maximum in engine.cpp" in c for c in contents)
    assert any("Function main in engine.cpp" in c for c in contents)
    assert {"vector", "util.hpp"} <= _dep_targets(store)


@pytest.mark.asyncio
async def test_ingest_swift(tmp_path: Path) -> None:
    _require("swift")
    code = """
import Foundation
import UIKit

class ViewController: UIViewController {
    override func viewDidLoad() {
        super.viewDidLoad()
    }
}

struct Model {
    var name: String
    func describe() -> String { return name }
}

enum Direction { case north, south }

protocol Drawable {
    func draw()
}

func helper(_ x: Int) -> Int { return x * 2 }
"""
    added, store = await _ingest(tmp_path, "App.swift", code)
    assert added >= 7
    contents = _contents(store)
    assert any("Class ViewController in App.swift" in c for c in contents)
    assert any("Class Model in App.swift" in c for c in contents)
    assert any("Class Direction in App.swift" in c for c in contents)
    assert any("Class Drawable in App.swift" in c for c in contents)
    assert any("Method viewDidLoad in App.swift" in c for c in contents)
    assert any("Method describe in App.swift" in c for c in contents)
    assert any("Method draw in App.swift" in c for c in contents)
    assert any("Function helper in App.swift" in c for c in contents)
    assert {"Foundation", "UIKit"} <= _dep_targets(store)


@pytest.mark.asyncio
async def test_ingest_fallback_for_unsupported_suffix(tmp_path: Path) -> None:
    """Files without a tree-sitter grammar still get the text summary."""
    code = 'fun main() { println("hi") }\n'
    added, store = await _ingest(tmp_path, "Main.kt", code)
    assert added == 1
    contents = _contents(store)
    assert any(c.startswith("File Main.kt:") for c in contents)


@pytest.mark.asyncio
async def test_ingest_fallback_when_nothing_extracted(tmp_path: Path) -> None:
    """A parseable file with no declarations or imports falls back to text."""
    _require("javascript")
    added, store = await _ingest(tmp_path, "script.js", 'console.log("hi");\n')
    assert added == 1
    contents = _contents(store)
    assert any(c.startswith("File script.js:") for c in contents)


@pytest.mark.asyncio
async def test_ingest_directory_with_treesitter_languages(tmp_path: Path) -> None:
    """ingest_directory routes .swift/.js/.go files through tree-sitter."""
    for lang in ("swift", "javascript", "go"):
        _require(lang)
    (tmp_path / "main.py").write_text("def py_func():\n    pass\n")
    (tmp_path / "app.js").write_text("function jsFunc() { return 1; }\n")
    (tmp_path / "main.swift").write_text("func swiftFunc() -> Int { return 1 }\n")
    (tmp_path / "notes.txt").write_text("not a code file\n")
    store = SemanticStore(tmp_path / "semantic.db", embedder=None)
    added = await ingest_directory(tmp_path, "test", store)
    assert added >= 3
    contents = _contents(store)
    assert any("Function py_func in main.py" in c for c in contents)
    assert any("Function jsFunc in app.js" in c for c in contents)
    assert any("Function swiftFunc in main.swift" in c for c in contents)
    assert not any("notes.txt" in c for c in contents)
