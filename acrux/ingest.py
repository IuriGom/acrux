"""Code-aware ingestion: turn code structure into semantic facts."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
from typing import Any

from acrux.memory.semantic import SemanticStore
from acrux.models import Fact

# ---------------------------------------------------------------------------
# Optional tree-sitter support (JS/TS, Go, Rust, Java, C/C++, Swift)
# ---------------------------------------------------------------------------

try:  # Preferred backend: the tree-sitter-languages grammar bundle.
    from tree_sitter_languages import get_language as _tsl_get_language
except Exception:  # pragma: no cover - optional dependency
    _tsl_get_language = None

try:
    from tree_sitter import Language as _TsLanguage
    from tree_sitter import Parser as _TsParser
except Exception:  # pragma: no cover - optional dependency
    _TsLanguage = None
    _TsParser = None

# Individual grammar wheels, used as a fallback when tree-sitter-languages is
# unavailable (it does not ship wheels for newer CPython versions).
_TS_STANDALONE_GRAMMARS = {
    "javascript": ("tree_sitter_javascript", "language"),
    "typescript": ("tree_sitter_typescript", "language_typescript"),
    "tsx": ("tree_sitter_typescript", "language_tsx"),
    "go": ("tree_sitter_go", "language"),
    "rust": ("tree_sitter_rust", "language"),
    "java": ("tree_sitter_java", "language"),
    "c": ("tree_sitter_c", "language"),
    "cpp": ("tree_sitter_cpp", "language"),
    "swift": ("tree_sitter_swift", "language"),
}

# File suffix -> tree-sitter language name.
_TS_LANG_BY_SUFFIX = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".swift": "swift",
}

# Node types that directly hold a declared symbol's name.
_IDENTIFIER_TYPES = frozenset(
    {
        "identifier",
        "type_identifier",
        "field_identifier",
        "property_identifier",
        "simple_identifier",
        "namespace_identifier",
    }
)

# Per-language node types that produce facts, mapped to the fact kind.
_TS_ENTITY_NODES: dict[str, dict[str, str]] = {
    "javascript": {
        "function_declaration": "Function",
        "generator_function_declaration": "Function",
        "class_declaration": "Class",
        "method_definition": "Method",
    },
    "typescript": {
        "function_declaration": "Function",
        "generator_function_declaration": "Function",
        "class_declaration": "Class",
        "abstract_class_declaration": "Class",
        "interface_declaration": "Class",
        "enum_declaration": "Class",
        "method_definition": "Method",
        "method_signature": "Method",
    },
    "go": {
        "function_declaration": "Function",
        "method_declaration": "Method",
    },
    "rust": {
        "function_item": "Function",
        "function_signature_item": "Method",
        "struct_item": "Class",
        "enum_item": "Class",
        "trait_item": "Class",
    },
    "java": {
        "class_declaration": "Class",
        "interface_declaration": "Class",
        "enum_declaration": "Class",
        "record_declaration": "Class",
        "method_declaration": "Method",
        "constructor_declaration": "Method",
    },
    "c": {
        "function_definition": "Function",
    },
    "cpp": {
        "function_definition": "Function",
        "class_specifier": "Class",
        "struct_specifier": "Class",
    },
    "swift": {
        "class_declaration": "Class",  # also covers struct and enum declarations
        "protocol_declaration": "Class",
        "function_declaration": "Function",
        "protocol_function_declaration": "Method",
    },
}
_TS_ENTITY_NODES["tsx"] = _TS_ENTITY_NODES["typescript"]

# Node type that holds import/include statements per language.
_TS_IMPORT_NODES = {
    "javascript": "import_statement",
    "typescript": "import_statement",
    "tsx": "import_statement",
    "go": "import_declaration",
    "rust": "use_declaration",
    "java": "import_declaration",
    "c": "preproc_include",
    "cpp": "preproc_include",
    "swift": "import_declaration",
}

# Node types shared between free functions and methods; they only count as
# methods when nested inside one of the container node types below.
_TS_FUNCTION_AS_METHOD = {
    "rust": "function_item",
    "cpp": "function_definition",
    "swift": "function_declaration",
}

# Call-expression node type for languages that support same-file call edges.
_TS_CALL_NODE_TYPES = {
    "javascript": "call_expression",
    "typescript": "call_expression",
    "tsx": "call_expression",
    "go": "call_expression",
    "rust": "call_expression",
}

# Containers that turn a nested function definition into a method.
_TS_METHOD_CONTAINERS = {
    "rust": frozenset({"impl_item", "trait_item"}),
    "cpp": frozenset({"class_specifier", "struct_specifier"}),
    "swift": frozenset({"class_declaration", "protocol_declaration", "extension_declaration"}),
}

_TS_PARSERS: dict[str, Any] = {}


def _decode(node: Any) -> str:
    return node.text.decode("utf-8", errors="replace")


def _load_ts_parser(lang: str) -> Any | None:
    """Return a cached tree-sitter parser for `lang`, or None if unavailable."""
    if lang in _TS_PARSERS:
        return _TS_PARSERS[lang]
    language = None
    if _tsl_get_language is not None:
        try:
            language = _tsl_get_language(lang)
        except Exception:
            language = None
    if language is None and _TsLanguage is not None and lang in _TS_STANDALONE_GRAMMARS:
        try:
            module_name, attr = _TS_STANDALONE_GRAMMARS[lang]
            module = importlib.import_module(module_name)
            language = _TsLanguage(getattr(module, attr)())
        except Exception:
            language = None
    parser = None
    if language is not None and _TsParser is not None:
        try:
            parser = _TsParser(language)
        except TypeError:  # tree-sitter < 0.22 API
            parser = _TsParser()
            try:
                parser.set_language(language)
            except AttributeError:
                parser.language = language
    _TS_PARSERS[lang] = parser
    return parser


def _ts_entity_kind(lang: str, node: Any, ancestors: tuple[str, ...]) -> str | None:
    """Classify a tree-sitter node as Function/Class/Method, or None."""
    spec = _TS_ENTITY_NODES.get(lang)
    if spec is None:
        return None
    kind = spec.get(node.type)
    if kind is None:
        # Go: type_spec wrapping a struct_type/interface_type is a type declaration.
        if lang == "go" and node.type == "type_spec":
            type_node = node.child_by_field_name("type")
            if type_node is not None and type_node.type in {"struct_type", "interface_type"}:
                return "Class"
        # JS/TS: arrow functions / function expressions assigned to variables.
        if lang in {"javascript", "typescript", "tsx"} and node.type == "variable_declarator":
            value = node.child_by_field_name("value")
            if value is not None and value.type in {
                "arrow_function",
                "function_expression",
                "function",
            }:
                return "Function"
        return None
    if kind == "Function" and _TS_FUNCTION_AS_METHOD.get(lang) == node.type:
        containers = _TS_METHOD_CONTAINERS.get(lang, frozenset())
        if any(ancestor in containers for ancestor in ancestors):
            return "Method"
    return kind


def _ts_node_name(node: Any) -> str | None:
    """Best-effort extraction of a declaration's name."""
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return _decode(name_node)
    # C/C++: the name is nested in the declarator chain.
    declarator = node.child_by_field_name("declarator")
    while declarator is not None:
        if declarator.type in _IDENTIFIER_TYPES:
            return _decode(declarator)
        nested = declarator.child_by_field_name("name")  # e.g. qualified_identifier
        if nested is not None:
            return _decode(nested)
        declarator = declarator.child_by_field_name("declarator")
    # Fallback: first identifier-like child.
    for child in node.named_children:
        if child.type in _IDENTIFIER_TYPES:
            return _decode(child)
    return None


def _strip_path(text: str) -> str:
    return text.strip().strip("\"'<>").strip()


def _is_test_file(path: Path) -> bool:
    """Detect test files: test_*.py, *.test.{js,ts,...}, *_test.go."""
    name = path.name
    suffix = path.suffix.lower()
    if suffix == ".py":
        return name.startswith("test_")
    if suffix == ".go":
        return name.endswith("_test.go")
    if suffix in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}:
        return ".test." in name
    return False


def _descendants(node: Any, types: set[str]) -> Any:
    stack = list(node.named_children)
    while stack:
        child = stack.pop()
        if child.type in types:
            yield child
        stack.extend(child.named_children)


def _ts_import_targets(lang: str, node: Any) -> list[str]:
    """Extract imported module/include paths from an import node."""
    if lang == "go":  # import_declaration may hold several import_specs
        return [
            _strip_path(_decode(path))
            for spec in _descendants(node, {"import_spec"})
            if (path := spec.child_by_field_name("path")) is not None
        ]
    for field in ("source", "argument", "path"):
        child = node.child_by_field_name(field)
        if child is not None:
            return [_strip_path(_decode(child))]
    # Java (scoped_identifier) and Swift (identifier) have no named field.
    for child in node.named_children:
        if child.type in {"scoped_identifier", "identifier"}:
            return [_strip_path(_decode(child))]
    return []


def _ts_call_name(node: Any, depth: int = 0) -> str | None:
    """Best-effort extraction of the callee name from a call target."""
    if node is None or depth > 6:
        return None
    if node.type in _IDENTIFIER_TYPES:
        return _decode(node)
    # Member/selector access: obj.method() -> method; pkg.Func() -> Func;
    # Config::new() -> new.
    for field in ("property", "field", "name"):
        child = node.child_by_field_name(field)
        if child is not None and child.type in _IDENTIFIER_TYPES:
            return _decode(child)
    # Generic functions wrap the callee, e.g. foo<T>().
    nested = node.child_by_field_name("function")
    if nested is not None and nested is not node:
        return _ts_call_name(nested, depth + 1)
    return None


def _ts_collect_calls(lang: str, func_node: Any) -> set[str]:
    """Collect callee names inside a function/method node (same file only).

    Nested named function/class scopes are pruned; their calls are collected
    separately when the main traversal visits them.
    """
    call_type = _TS_CALL_NODE_TYPES.get(lang)
    if call_type is None:
        return set()
    names: set[str] = set()
    stack: list[tuple[Any, tuple[str, ...]]] = [
        (child, (func_node.type,)) for child in func_node.named_children
    ]
    while stack:
        node, ancestors = stack.pop()
        if node.type == call_type:
            name = _ts_call_name(node.child_by_field_name("function"))
            if name:
                names.add(name)
        elif _ts_entity_kind(lang, node, ancestors) is not None:
            continue  # nested named scope; handled separately
        stack.extend((child, ancestors + (node.type,)) for child in node.named_children)
    return names


_PY_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _py_import_map(tree: ast.AST) -> dict[str, str]:
    """Map locally-bound names to their fully-qualified import targets.

    - ``from module import func``       -> {func: "module.func"}
    - ``from module import func as f``  -> {f: "module.func"}
    - ``import module as m``            -> {m: "module"}
    - ``import module`` / ``import a.b``-> {module_or_root: same} (identity;
      the raw dotted chain at the call site is already fully qualified)
    """
    mapping: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    mapping[alias.asname] = alias.name
                else:
                    root = alias.name.split(".")[0]
                    mapping.setdefault(root, root)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                local = alias.asname or alias.name
                mapping[local] = f"{module}.{alias.name}" if module else local
    return mapping


def _py_dotted_chain(node: ast.AST) -> tuple[str, list[str]] | None:
    """Return (root_name, attrs) for a Name/Attribute chain like ``a.b.c``."""
    attrs: list[str] = []
    while isinstance(node, ast.Attribute):
        attrs.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        attrs.reverse()
        return node.id, attrs
    return None


def _py_collect_crossfile_calls(
    func_node: ast.AST,
    import_map: dict[str, str],
    local_names: set[str],
) -> set[str]:
    """Collect module-qualified callee names for calls to imported names.

    For ``from module import func`` + call ``func()`` yields ``module.func``;
    for ``import module`` (or ``import module as m``) + call ``module.func()``
    (``m.func()``) yields ``module.func``. Names bound to local definitions
    are left to the same-file edges.

    Nested function/class definitions are pruned; their calls are collected
    separately when the main walk visits them.
    """
    names: set[str] = set()
    stack = list(ast.iter_child_nodes(func_node))
    while stack:
        node = stack.pop()
        if isinstance(node, _PY_SCOPE_NODES):
            continue  # nested scope; handled separately
        if isinstance(node, ast.Call):
            chain = _py_dotted_chain(node.func)
            if chain is not None:
                root, attrs = chain
                target = import_map.get(root)
                if target is not None and root not in local_names:
                    if not attrs:
                        resolved = target
                    elif target == root:
                        resolved = ".".join([root, *attrs])
                    else:
                        resolved = ".".join([target, *attrs])
                    names.add(resolved)
        stack.extend(ast.iter_child_nodes(node))
    return names


def _py_call_name(node: ast.AST) -> str | None:
    """Extract the callee name from an ast.Call's func node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _py_collect_calls(func_node: ast.AST) -> set[str]:
    """Collect callee names directly inside a Python function/method.

    Nested function/class definitions are pruned; their calls are collected
    separately when the main walk visits them.
    """
    names: set[str] = set()
    stack = list(ast.iter_child_nodes(func_node))
    while stack:
        node = stack.pop()
        if isinstance(node, _PY_SCOPE_NODES):
            continue  # nested scope; handled separately
        if isinstance(node, ast.Call):
            name = _py_call_name(node.func)
            if name:
                names.add(name)
        stack.extend(ast.iter_child_nodes(node))
    return names


async def ingest_python_file(path: Path, project: str, semantic: SemanticStore) -> int:
    """Parse a Python file and store classes/functions as facts.

    Also records import edges ('tests' edges for test files), same-file
    'calls' edges between functions, and cross-file 'calls' edges from a
    calling function to module-qualified targets for calls to imported names
    (e.g. ``module.func``).
    """
    try:
        source = path.read_text(errors="replace")
        tree = ast.parse(source, filename=str(path))
    except Exception:
        return 0

    added = 0
    module_doc = ast.get_docstring(tree)
    if module_doc:
        await semantic.add(
            Fact(
                project=project,
                content=f"Module {path.name}: {module_doc[:500]}",
                source=f"code:{path.name}",
                tags=["code", "module", path.suffix.lstrip(".")],
            )
        )
        added += 1

    deps: list[dict[str, Any]] = []
    import_map = _py_import_map(tree)
    local_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node) or ""
            content = f"Class {node.name} in {path.name}"
            if doc:
                content += f": {doc[:300]}"
            await semantic.add(
                Fact(
                    project=project,
                    content=content,
                    source=f"code:{path.name}:{node.lineno}",
                    tags=["code", "class", path.suffix.lstrip(".")],
                )
            )
            added += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node) or ""
            content = f"Function {node.name} in {path.name}"
            if doc:
                content += f": {doc[:300]}"
            await semantic.add(
                Fact(
                    project=project,
                    content=content,
                    source=f"code:{path.name}:{node.lineno}",
                    tags=["code", "function", path.suffix.lstrip(".")],
                )
            )
            added += 1
            # Same-file call edges from this function to each callee name,
            # plus cross-file edges to module-qualified imported callees.
            callees = _py_collect_calls(node) | _py_collect_crossfile_calls(
                node, import_map, local_names
            )
            for callee in sorted(callees):
                deps.append(
                    {
                        "source_ref": node.name,
                        "source_type": "function",
                        "target_ref": callee,
                        "target_type": "function",
                        "dependency_type": "calls",
                    }
                )

    # Record import/dependency edges; test files get 'tests' edges instead.
    dep_kind = "tests" if _is_test_file(path) else "imports"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                deps.append(
                    {
                        "source_ref": str(path),
                        "source_type": "file",
                        "target_ref": alias.name,
                        "target_type": "module",
                        "dependency_type": dep_kind,
                    }
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                target = f"{module}.{alias.name}" if module else alias.name
                deps.append(
                    {
                        "source_ref": str(path),
                        "source_type": "file",
                        "target_ref": target,
                        "target_type": "module",
                        "dependency_type": dep_kind,
                    }
                )
    if deps:
        semantic.add_dependencies(project, deps)

    return added


async def ingest_treesitter_file(path: Path, project: str, semantic: SemanticStore) -> int | None:
    """Parse a JS/TS, Go, Rust, Java, C/C++ or Swift file with tree-sitter.

    Stores classes/functions/methods as facts and records import edges
    ('tests' edges for test files) plus same-file 'calls' edges between
    functions. Returns the number of facts stored, or None when the file's
    language is unsupported, no tree-sitter backend is installed, or nothing
    structured was found (the caller should then fall back to plain-text
    ingestion).
    """
    lang = _TS_LANG_BY_SUFFIX.get(path.suffix.lower())
    if lang is None:
        return None
    parser = _load_ts_parser(lang)
    if parser is None:
        return None
    try:
        root = parser.parse(path.read_bytes()).root_node
    except Exception:
        return None

    ext = path.suffix.lstrip(".")
    import_node_type = _TS_IMPORT_NODES.get(lang)
    dep_kind = "tests" if _is_test_file(path) else "imports"
    added = 0
    deps: list[dict[str, Any]] = []

    stack: list[tuple[Any, tuple[str, ...]]] = [(root, ())]
    while stack:
        node, ancestors = stack.pop()
        kind = _ts_entity_kind(lang, node, ancestors)
        if kind is not None:
            name = _ts_node_name(node)
            if name:
                await semantic.add(
                    Fact(
                        project=project,
                        content=f"{kind} {name} in {path.name}",
                        source=f"code:{path.name}:{node.start_point[0] + 1}",
                        tags=["code", kind.lower(), ext],
                    )
                )
                added += 1
                # Same-file call edges from this function/method to callees.
                if kind in {"Function", "Method"}:
                    for callee in sorted(_ts_collect_calls(lang, node)):
                        deps.append(
                            {
                                "source_ref": name,
                                "source_type": "function",
                                "target_ref": callee,
                                "target_type": "function",
                                "dependency_type": "calls",
                            }
                        )
        if node.type == import_node_type:
            for target in _ts_import_targets(lang, node):
                deps.append(
                    {
                        "source_ref": str(path),
                        "source_type": "file",
                        "target_ref": target,
                        "target_type": "module",
                        "dependency_type": dep_kind,
                    }
                )
        for child in reversed(node.named_children):
            stack.append((child, ancestors + (node.type,)))

    if deps:
        semantic.add_dependencies(project, deps)
    if added == 0 and not deps:
        return None  # nothing structured found; let the caller fall back
    return added


async def ingest_file(path: Path, project: str, semantic: SemanticStore) -> int:
    """Ingest a single file."""
    if path.suffix == ".py":
        return await ingest_python_file(path, project, semantic)
    ts_added = await ingest_treesitter_file(path, project, semantic)
    if ts_added is not None:
        return ts_added
    # For other files, store a short summary.
    try:
        text = path.read_text(errors="replace")
    except Exception:
        return 0
    if len(text) > 2000:
        text = text[:2000] + "\n... (truncated)"
    await semantic.add(
        Fact(
            project=project,
            content=f"File {path.name}:\n{text}",
            source=f"code:{path.name}",
            tags=["code", "file", path.suffix.lstrip(".")],
        )
    )
    return 1


async def ingest_directory(
    root: Path,
    project: str,
    semantic: SemanticStore,
    max_files: int = 1000,
) -> int:
    """Walk a directory and ingest code files."""
    ignore_dirs = {".git", ".venv", "node_modules", "__pycache__", ".ruff_cache", ".DS_Store"}
    added = 0
    count = 0
    for path in root.rglob("*"):
        if count >= max_files:
            break
        if not path.is_file():
            continue
        if any(part in ignore_dirs for part in path.parts):
            continue
        if path.suffix not in {
            ".py",
            ".js",
            ".jsx",
            ".mjs",
            ".cjs",
            ".ts",
            ".tsx",
            ".go",
            ".rs",
            ".java",
            ".kt",
            ".c",
            ".cpp",
            ".cc",
            ".h",
            ".hpp",
            ".swift",
            ".sh",
            ".md",
        }:
            continue
        count += 1
        added += await ingest_file(path, project, semantic)
    return added
