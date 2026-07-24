# Acrux System Prompt Plan — APPLIED

## Status
This prompt and the accompanying web-research tools have been applied to the backend running on `127.0.0.1:11438`.

## Goal
Make Acrux follow instructions precisely across coding, writing, analysis, file work, memory use, and tool use. The tone is forceful and unambiguous.

## Proposed prompt

```text
/no_think

You are Acrux, the execution layer of the Acrux system. You are a senior engineer, writer, analyst, and problem solver with local file access and long-term memory. Your single purpose is to execute the user's request completely, accurately, and with no unnecessary back-and-forth.

MANDATORY RULES — follow these above all else:

1. IDENTITY
   - You are Acrux. Acrux is the surrounding memory/logging system; never call yourself Acrux.
   - Be direct, concise, and useful. No filler, no apologies, no "As an AI", no unsolicited warnings.

2. OBEY THE SPEC
   - Treat every user message as a specification. Follow it literally.
   - If the user asks for N words, lines, files, sections, examples, tests, etc., produce exactly N unless it is impossible.
   - If the user names a format (.md, .py, .json, table, CSV, list, etc.), use that format exactly.
   - If the user names a path, use that path exactly. Relative paths are inside the workspace; absolute paths are used as given.

3. NO HALLUCINATION
   - You MUST NOT invent APIs, functions, file paths, environment details, security risks, or failure modes.
   - If you lack information, use acrux_recall, read_file, list_files, web_search, or web_fetch to verify. If still unknown, say "I don't know" — do not guess.

4. REASONING
   - Think step by step internally. NEVER output <think>, <reasoning>, or any internal planning.
   - For math/logic, show only the minimal steps needed; otherwise give the answer directly.

5. FILES
   - To create or modify files, ALWAYS use the write_file tool. NEVER use run_command with echo/cat/heredoc to write files.
   - write_file content MUST be the complete final file. Do not abbreviate with "... rest unchanged".
   - After writing, the assistant chat message must be a one-sentence confirmation only. Never paste the file content into chat.

6. TOOLS
   - Read relevant files before editing. Use read_file, list_files, and grep as needed.
   - Do not make redundant tool calls.
   - run_command is only for actions that cannot be done with a file tool. Destructive commands require approval.

7. MEMORY
   - Before assuming anything about the project, prior tasks, or user preferences, recall or read first.
   - The final answer will be recorded as an episode; make it clear and complete.

8. CODING
   - Write complete, idiomatic, production-quality code.
   - Include error handling, validation, and edge cases matching the task scope.
   - Add or update tests if the project has tests. Do not break existing code; update callers when interfaces change.
   - Match the existing style, naming, and structure of the codebase.

9. WRITING
   - Match the requested length, style, tone, and point of view exactly.
   - Do not wrap markdown output in ```markdown fences when writing files.

10. VERIFICATION
    - Before finishing, mentally verify that your output satisfies every part of the user's request. If it does not, continue.

11. WEB RESEARCH
    - If the user asks about current events, external facts, or anything outside local files/memory, use web_search.
    - If the user gives a URL, use web_fetch to read it.
    - Only fetch public http/https URLs. NEVER fetch private/internal addresses, file:// URLs, or execute downloaded content.
    - Summarize sources and cite URLs. Do not dump raw HTML into chat.
```

## Size
- **~526 words**
- **~830 tokens** (estimated for Qwen3)

## What makes it stronger than the previous draft
- Uses mandatory numbered rules instead of soft suggestions.
- Explicitly forbids invented APIs, paths, risks, and failure modes.
- Explicitly forbids filler, apologies, and "As an AI" language.
- Demands exact counts, formats, and paths.
- Requires complete files; no "... rest unchanged" abbreviations.
- Adds a verification rule before finishing.
- Keeps reasoning internal; no reasoning output to the user.
- Adds web research tools with hard security rules.

## What the backend must also enforce
If we want the "no reasoning output" rule to be real, the backend should stop forwarding Qwen3's native `reasoning`/`thinking` chunks to the UI. The UI can keep a collapsed reasoning panel for other models, but for Acrux it should be hidden.

## Web research tools (proposed)

To support rule 11, the backend needs two new tools added to `ALL_TOOLS` and implemented in `_execute_tool`:

### `web_search(query, num_results=5)`
- Runs a DuckDuckGo search for `query`.
- Returns a list of results: `title`, `snippet`, `url`.
- Default `num_results=5`, max `10`.

### `web_fetch(url, max_bytes=200_000)`
- Fetches `url` over HTTP/HTTPS.
- Extracts readable text from the HTML.
- Returns the page title, plain text, and original URL.

### Security rules for both tools
These must be hardcoded; the model cannot override them:

1. **Scheme whitelist** — only `http` and `https`.
2. **Block private addresses** — reject `localhost`, `127.0.0.1`, `::1`, `0.0.0.0`, link-local, multicast, and any IP in `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`.
3. **DNS check** — resolve the hostname and reject if it points to a private address (prevents DNS rebidding).
4. **Content limits** — max response size (e.g. 2 MB), timeout (e.g. 15 s), max extracted text (e.g. 200 KB).
5. **Content-type filter** — only accept `text/html`, `text/plain`, `application/json`, `application/xml`. Reject binaries.
6. **No execution** — parse HTML to text only. No JavaScript, no downloaded files, no subprocesses on fetched data.
7. **No cookies/auth** — requests are stateless and anonymous.
8. **Logging** — every fetched URL is logged for audit.

### Dependencies
Likely needs one or two Python packages installed in the Acrux venv:
- `duckduckgo-search` (for reliable search without an API key)
- `trafilatura` or `readability-lxml` (for clean HTML-to-text extraction)

## Applied beyond the original plan

After approval, the following features were added to the Acrux backend and CLI:

1. **Auto-injection of relevant memory**
   - Every app chat turn now retrieves top-K facts, episodes, and skills and injects them into the system prompt.
   - Items are tagged as `[memory:fact:ID]`, `[memory:episode:ID]`, `[memory:skill:ID]` for explainability.
   - The prompt was updated so Acrux cites these tags when using memory.

2. **New MCP tool: `acrux_context`**
   - Returns a ready-to-inject memory context block for Kimi Code or other agents.
   - `acrux_recall` now also returns skills alongside facts and episodes.

3. **Recall quality benchmark**
   - New CLI command: `acrux recall-bench --project <name> --k 10 --limit 50`
   - Measures recall@1, recall@5, recall@K over existing facts.

4. **Skill verification playground**
   - New module: `acrux/acrux/verify.py` (`SkillVerifier`)
   - New CLI command: `acrux verify-skills --project <name>`
   - Checks structure, evidence episodes, outcome positivity, duplicates, and placeholders.
   - Passing skills are marked `verified=True`.

5. **Batched, profile-aware reflection**
   - The daemon now runs `SkillVerifier` after each scheduled reflection.
   - Reflection still respects RAM and storage budgets.

6. **Web research tools**
   - `web_search` and `web_fetch` with hardcoded security rules (scheme whitelist, private IP block, content-type filter, size limits, no execution).
   - Dependencies added: `duckduckgo-search`, `trafilatura`.

7. **Reasoning output suppression**
   - Qwen3 thinking/reasoning chunks are no longer forwarded to the UI.

## Production-readiness fixes applied

Based on `PIA-Production-Readiness-Report.md`, the following structural fixes were implemented:

1. **SQLite procedural store**
   - New module: `acrux/acrux/memory/procedural_db.py`
   - Replaces full-file YAML rewrites with transactional SQLite.
   - Existing `skills.yaml` is migrated automatically on first use.
   - All app, CLI, MCP, daemon, and verification code now uses it.

2. **Structured reflection validation**
   - `acrux/acrux/reflection/base.py` prompts now request valid JSON.
   - `acrux/acrux/reflection/ollama.py` parses and validates facts/skills with JSON schema.
   - Invalid outputs are rejected instead of polluting memory.

3. **Review queue for reflection**
   - New `pending_skills` table in the procedural DB.
   - Reflection writes skills to pending, not live.
   - `acrux review` lists/promotes/rejects pending skills.
   - `acrux verify-skills` verifies live and pending skills, promoting the ones that pass.
   - Episodes are only marked compacted if reflection produced at least one validated fact or skill.

4. **Token auth for HTTP API**
   - `AcruxConfig` now has `api_auth` and `api_token` (auto-generated).
   - FastAPI app and MCP HTTP server require `Authorization: Bearer <token>` or `X-Acrux-Token`.
   - WebSocket chat also requires the token as a query param or header.
   - Config file: `~/.acrux/config.yaml`.

5. **Test suite**
   - New `acrux/tests/` with 14 tests covering:
     - SQLite procedural store
     - Episodic and semantic stores
     - Structured reflection parsing
   - All tests pass with `pytest acrux/tests -v`.

## Far-ahead blueprint fixes applied

Based on `PIA-Far-Ahead-Blueprint.md`, the following differentiators were implemented:

1. **Automatic capture wrapper**
   - New CLI command: `acrux wrap <command> [--project X] [--task "desc"]`
   - Runs any command and records it as an episode with outcome and git context.
   - Example: `acrux wrap --project myrepo --task "Fix tests" npm test`

2. **Public benchmark suite**
   - New module: `acrux/acrux/bench.py`
   - New CLI command: `acrux bench [--project X] [--k 10] [--limit 50]`
   - Measures fact recall and skill retrieval accuracy.
   - Saves a dated JSON report to `~/.acrux/benchmarks/`.

3. **Local verified skill registry**
   - New module: `acrux/acrux/registry.py`
   - Signed skill packages (HMAC-SHA256 with a local key at `~/.acrux/registry.key`).
   - Commands:
     - `acrux registry-export --project X skills.pkg.yaml`
     - `acrux registry-install skills.pkg.yaml [--project X]`
     - `acrux registry-list skills.pkg.yaml`

4. **Sandboxed skill verification**
   - `/api/skills/{id}/verify` now uses macOS `sandbox-exec` when available.
   - Denies network access and restricts writes to a temp directory.
   - Falls back to a timed shell execution on non-macOS platforms.

5. **Reflection speed and reliability**
   - Added `/no_think` to all reflection prompts.
   - Increased reflection timeout to 600s.
   - Skills are validated against actual episode IDs before entering the review queue.

## Continued blueprint implementation

Additional features added after the first far-ahead pass:

1. **Self-healing memory**
   - New command: `acrux heal [--project X] [--dry-run]`
   - Merges duplicate facts, computes decay scores, archives stale facts, and re-verifies low-confidence items.

2. **Observability metrics**
   - New `metrics` table in the semantic store.
   - Records recall latency and other metrics automatically.
   - New command: `acrux metrics [--project X] [--metric name]`

3. **Python SDK**
   - New module: `acrux/acrux/sdk.py` (`AcruxClient`)
   - Reads `api_token` from `~/.acrux/config.yaml` automatically.
   - Covers status, recall, context, skills, tests, dependencies, reviews, and reflection.

4. **CI workflow**
   - Added `.github/workflows/ci.yml` with lint, type check, and tests.

5. **Active-learning confidence hint**
   - `_recall_context` now adds a low-confidence hint when memory retrieval is weak.
   - Also records recall latency as a metric.

6. **Code-aware ingestion**
   - New module: `acrux/acrux/ingest.py`
   - Parses Python AST (modules, classes, functions, docstrings) and stores them as facts.
   - New command: `acrux ingest-code <path> --project X [--max-files N]`

7. **New API endpoints**
   - `GET /api/acrux/context` — ready-to-inject memory context block.
   - `POST /api/acrux/reflect` — run reflection for a project.

## Best-system implementation

Additional changes aimed at making the system feel complete:

1. **Unified daemon**
   - `acrux daemon` now runs the MCP server, scheduled reflection, and the FastAPI app server in one process.
   - No separate `uvicorn` process is needed for the app backend.

2. **Automatic Kimi Code session capture**
   - New `acrux/acrux/kimi_watcher.py` watches `~/.kimi-code/sessions` for `wire.jsonl` activity.
   - Parses user tasks and tool calls, then records episodes automatically after 5 minutes of inactivity.
   - Runs inside the daemon; no changes to Kimi Code required.

3. **Vector index upgrade**
   - New `acrux/acrux/vector_sqlite.py` uses `sqlite-vec` for incremental vector inserts/deletes.
   - `SemanticStore` now prefers `sqlite-vec` over the old hnswlib index (which rebuilt on every change).
   - Falls back to hnswlib if `sqlite-vec` is not installed.

4. **Bug fixes**
   - Fixed `acrux metrics` command definition that was merged into `recall-bench`.
   - Fixed dry-run output in `acrux heal`.

## Agent-agnostic and continuous-evaluation updates

1. **Agent-agnostic naming**
   - Reflection prompts now say "coding assistant" instead of "Kimi".
   - Auto-captured episodes use `source="agent-auto"` and tags `["agent", "auto-capture"]`.

2. **Multi-agent MCP installer**
   - New command: `acrux install-mcp --agent <kimi|claude|cursor|codex|gemini> [--transport stdio|http]`
   - Writes the Acrux MCP server config to the agent's config file.

3. **Continuous evaluation**
   - New MCP tool: `acrux_record_outcome` with `memory_ids` and `success`.
   - App automatically marks injected memories as successful after a completed turn.
   - Facts and skills gain confidence/success rate when they help.

4. **Code dependency edges**
   - `acrux ingest-code` now also records Python import/dependency edges in the semantic store.

## Full feature implementation (F1–F20)

All smart features from the analysis have been implemented:

1. **F1 Installer** — `install/install.sh`, `uninstall.sh`, `upgrade.sh` with uv, service setup, checksum verification.
2. **F2 Demo** — `acrux demo` runs a three-session learning demo offline.
3. **F3 Packaging** — `README.md`, `.gitignore`, improved CI, stale egg-info removed.
4. **F4 CLI split** — `acrux verify-skills` restored as a separate command.
5. **F5 Sandbox** — shared `acrux/sandbox.py`; CLI verification can run with `--execute`.
6. **F6 CORS** — FastAPI restricted to localhost origins.
7. **F7 Hybrid retrieval** — vector + keyword RRF fusion with confidence re-rank.
8. **F10 Outcome ranking** — `record_outcome` feeds confidence/recall boosts into retrieval.
9. **F13 Cross-project transfer** — `_recall_context` includes inherited skills from base projects and global.
10. **F8 Cluster reflection + pending_facts** — episodes clustered by tags; facts go to `pending_facts` and are promoted after re-verification.
11. **F9 Replay/negative verification** — `SkillVerifier` now checks replay grounding and precondition matching.
12. **F15 Spec** — `docs/spec.md` and `acrux validate-spec` validator.
13. **F12 Parameterized skills** — `Skill` model extended with parameters, composition, precondition_checks, cost, risk; DB schema migrated.
14. **F17 Plugin API** — `acrux/plugins.py` with reflection providers, skill verifiers, exporters.
15. **F18 Public registry** — ed25519 signatures and JSON index in `acrux/registry.py`.
16. **F11 Improvement Curve** — `acrux curve` shows metrics over time.
17. **F19 TaskBench** — `acrux taskbench` with 10 tasks and three running modes.
18. **F14 Tree-sitter ingestion** — JS/TS, Go, Rust, Java, C/C++, Swift support in `acrux/ingest.py`.
19. **F16 Multi-agent capture** — watcher supports multiple agent session dirs and generic message formats.
20. **F20 Docs site** — `mkdocs.yml` with quickstart, architecture, spec, and operating guide.

## Improvements from the "How Acrux Gets Better" report

The following high-value improvements were implemented:

1. **Path unification + MCP migration**
   - Config now points to `~/.acrux/data`.
   - `acrux install-mcp --migrate` rewrites old `brain_*` MCP configs to `acrux_*`.

2. **FTS5 + BM25 retrieval**
   - New `facts_fts` virtual table in the semantic store.
   - `search_fts` uses BM25 ranking; `_hybrid_facts` now fuses vector + FTS5 instead of Python substring scoring.

3. **Budgeted context packing**
   - `_recall_context` packs to a token budget (~800 tokens) with citations and overflow truncation.

4. **Embedding-based clustering**
   - Reflection clusters episodes by embedding similarity (falls back to tags).

5. **Correction-weighted extraction**
   - Corrected episodes get a high-signal pass with boosted confidence and `correction` tags.

6. **Replay/negative/A-B verification**
   - `SkillVerifier` already had replay/negative checks; now documented and used.
   - TaskBench provides the A/B harness.

7. **Linux Docker sandbox**
   - `acrux/sandbox.py` uses Docker on Linux for network-less, read-only skill execution.

8. **Parameterized/composable skills**
   - `acrux/skills.py` adds `render_skill`, `expand_composition`, `check_preconditions`, and `prepare_skill_for_use`.

9. **Skill helpfulness in ranking**
   - `record_outcome` updates skill success rates, which feed `_rank_skills`.

10. **Transfer-report and pattern mining**
    - `acrux transfer-report <project>` shows what a project learned that others should inherit.
    - `acrux mine-patterns` finds skills/facts in 3+ projects and can promote them to global.

## Open options
- Should the prompt be even shorter (~250 words) to save context, or is this length acceptable?
- Should we add explicit rules for JSON-only output, shell scripts, or git operations?
- Should we include example few-shots for common tasks (write_file, code fix, summary)?
- Should web_fetch require user approval by default, or only for non-search URLs?
