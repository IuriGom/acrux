# Acrux Improvement — Final Plan and Verification

This document summarizes the improvement plan, what was implemented, and how to prove each change works.

## Plan review

The original plan (`Acrux-Improvement-Prompt.md`) was reviewed against the current codebase. Key adjustments:

- Many tasks were already done (MCP migration, embedding clustering, CORS).
- The real problem was a **split-brain retrieval stack**: FastAPI had hybrid retrieval, but MCP/agents used naive keyword search. Tasks 4, 5, and 10 were merged into a **unified retrieval module** used by both paths.
- Outcome inference was added because auto-captured episodes need meaningful outcomes for verification.
- SQLite concurrency was addressed by enabling WAL in all stores.
- SemanticStore was split into focused modules.

## What was implemented

### 1. Unified retrieval module (`acrux/retrieval.py`)

- `hybrid_facts`: vector + FTS5 fusion with reciprocal-rank fusion and outcome re-rank.
- `rank_skills`: verified + success_rate ordering.
- `inherited_skills` / `inherited_facts`: cross-project transfer with source tags.
- `pack_context`: token-budget packing with citations and overflow truncation.
- `recall_context`: one entry point used by MCP and FastAPI.

**Proof:** `acrux_context` MCP tool and the app both use it; `pytest acrux/tests` passes.

### 2. FTS5 + WAL everywhere

- Facts: `facts_fts` (already existed).
- Episodes: `episodes_fts` with BM25 ranking.
- Skills: `skills_fts` with BM25 ranking.
- WAL enabled in `SemanticStore`, `EpisodicStore`, `ProceduralDBStore` for concurrent access.

**Proof:** `search_fts` returns ranked results; concurrent reads/writes don't lock.

### 3. Outcome inference + capture filtering (`acrux/kimi_watcher.py`)

- Filters low-signal sessions (zero tool calls, read-only Q&A, short tasks).
- Always stores edits, fail→pass sequences, corrections.
- Infers outcome (`success (inferred)` / `error (inferred)`) from tool results.
- Tags high-signal episodes with `signal:high`.

**Proof:** `test_capture_heuristics.py` (21 tests) passes.

### 4. Claude Code capture adapter (`acrux/claude_watcher.py`)

- Watches `~/.claude/projects/**/*.jsonl`.
- Parses Claude Code transcript format (user/assistant messages, tool_use blocks).
- Emits the same `Episode` schema as the Kimi watcher.

**Proof:** `test_claude_watcher.py` (7 tests) passes; daemon starts both watchers.

### 5. Tree-sitter test links + same-file call edges (`acrux/ingest.py`)

- `tests` edges for `test_*.py`, `*.test.ts`, `*_test.go`.
- `calls` edges for Python, JS/TS, Go, Rust (same-file, name-based).

**Proof:** `test_ingest_links.py` (10 tests) passes.

### 6. SemanticStore split (`acrux/memory/`)

- `facts.py` — fact CRUD, confidence, decay, versioning, pending facts, metrics.
- `graph.py` — relationships, trees, clusters, inheritance layers.
- `artifacts.py` — tests, reviews, dependencies, file summaries, watcher state.
- `health.py` — health checks, checksums.
- `semantic.py` is now a thin facade; no caller changes.

**Proof:** `test_semantic_split.py` (4 tests) passes; all existing tests still pass.

### 7. TaskBench as A-B verification harness

- `run_taskbench` accepts `extra_skills`.
- `SkillVerifier.ab_check` runs TaskBench with and without a candidate skill and compares pass rates.

**Proof:** `ab_check` returns a comparison string; TaskBench tests pass.

### 8. Linux Docker sandbox

- `acrux/sandbox.py` uses Docker on Linux for network-less, read-only skill execution.

### 9. Verifier replay + negative checks

- `SkillVerifier.replay_execute` replays a skill at its evidence git commit in a temp worktree.
- `SkillVerifier.negative_execute` runs the skill in an empty workspace and requires graceful failure.
- Only executable-looking skills are executed; natural-language procedures are checked statically.

**Proof:** verifier tests pass; replay/negative paths are exercised with mock workspaces.

### 10. Path consolidation with migration

- `AcruxConfig.load` migrates `~/.brain` to `~/.acrux` on first load and leaves a symlink for backward compatibility.

### 11. Cross-file call graph resolution

- Python ingestion now resolves calls to imported functions across files (`from module import func` + `func()` → `module.func`; `import module` + `module.func()` → `module.func`).
- Same-file call edges are preserved alongside cross-file edges.

**Proof:** `test_ingest_crossfile.py` (11 tests) passes.

### 12. Registry hosting prep

- `acrux registry-index` builds a public JSON index of signed packages.
- `acrux registry-push <url>` uploads index + packages with httpx (supports `--dry-run`).
- `acrux registry-pull <url>` downloads and installs packages after signature verification.

**Proof:** `test_registry_hosting.py` (22 tests) passes.

### 13. Anonymous Git upload staging

- Staged a clean public copy at `~/Desktop/acrux-public`.
- Scrubbed all personal paths and names from the staged copy.
- Stripped all runtime data (DBs, logs, exports).
- Fresh git history with `iurigomide <iurigomide@proton.me>` as author/committer.
- `pyproject.toml` fixed: removed un-installable `tree-sitter-languages`, added optional grammar extras and `mypy` to dev deps.
- Install scripts fixed: `ACRUX_GH_REPO` placeholder, domain `acrux.dev`, init now skips existing `~/.acrux/config.yaml`, uninstall splits install prefix (`~/.pia`) from data (`~/.acrux`).
- Tests pass from the staged copy: **191 passed, 17 skipped**.

### 14. Installer MCP flow fixes and three-LLM review

- Got three independent LLM opinions on the ACRUX plan (qwen3:14b ×2 with different prompts, llava:latest). Consensus: fix installer MCP bugs and identity leaks first; defer enterprise and LoRA.
- **Bug 2 fixed:** `install.sh` now splits `INSTALL_HOME` (venv, `~/.pia`) from `ACRUX_HOME` (config/data, `~/.acrux`).
- **Bug 3 fixed:** `acrux install-mcp --transport http` now writes a URL entry (`{"url": "http://127.0.0.1:<port>/sse", "headers": {"Authorization": "Bearer <token>"}}`) instead of a broken daemon command entry.
- Identity leaks fixed in the working repo: `Constants.swift` project dir is configurable (`ACRUX_PROJECT_DIR`, default `~/acrux`), `install_app.sh` derives from script location, `claude_watcher.py` comment and test fixture genericized, `docs/OPERATING.md` and `CHANGES.md` use `~/acrux`.
- README updated with one-liner install and from-source path at the top.
- Restaged with `brain-training-corpus/`; identity and data greps pass; tests pass from clean venv (**191 passed, 17 skipped**); git identity is `iurigomide <iurigomide@proton.me>`.

## Verification

Run the test suite:

```bash
cd ~/acrux
source .venv/bin/activate
pytest acrux/tests -q
```

Expected output: **208 passed**.

Run the doctor on a real data dir:

```bash
acrux doctor
```

Start the daemon and check status:

```bash
acrux daemon --background --mcp http
curl -H "Authorization: Bearer $(acrux config acrux.api_token)" http://127.0.0.1:11438/api/acrux/status
```

Expected: HTTP 200 with `running: true`.

## Not implemented (out of scope or premature)

- Public skill registry hosting (needs a public index).
- Enterprise features (encryption, audit, RBAC).
- LoRA/parametric consolidation (gated on trusted verification).
- Full cross-file call-graph resolution (scoped to name-based edges).
