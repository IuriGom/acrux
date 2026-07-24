# Acrux Next Batch — Design Document

**Date:** 2026-07-13  
**Path:** `acrux/docs/superpowers/plans/2026-07-13-acrux-next-batch.md`  
**Status:** Design / spec only. Do not implement from this document without a separate execution plan.

---

## Goal

Extend the Acrux from a session-oriented memory store into a self-managing, project-aware knowledge system. The selected features add structure (hierarchy, versioning, clustering, inheritance), automation (watchers, health checks, summarization, agent loops), and a richer Swift UI (tabs, search, diff, command palette, floating widget, status bar). All changes must remain optional and degrade gracefully on low-RAM / low-storage machines.

---

## Architecture overview

```text
┌─────────────────────────────────────────────────────────────┐
│                        SwiftUI Acrux App                     │
│  Chat · Memory Inspector · Knowledge Graph · Floating Widget │
│  Command Palette · Status Bar · Tabs · Diff Viewer           │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────▼──────────────────────────────────────┐
│              FastAPI backend (acrux.app.main)                │
│  Chat engine · Tool executor · Memory CRUD · Import/export   │
│  Watcher · Health checks · Scheduler · Reflection hooks      │
└──────────────────────┬──────────────────────────────────────┘
                       │ SQLite / YAML / Vector index
┌──────────────────────▼──────────────────────────────────────┐
│              ~/.acrux/data                                   │
│  global/  +  projects/<name>/                                │
│  facts.db · episodes.db · skills.yaml · embeddings.hnsw      │
└─────────────────────────────────────────────────────────────┘
```

Design principles for this batch:

1. **Optional richness, mandatory frugality.** Every expensive feature (embeddings, clustering, LLM summarization, graph layout) must be toggleable and fall back to cheap behavior on `minimal`/`light` profiles.
2. **Project-first, global-aware.** Most new data is scoped to a project. Global memories are a base layer that projects can optionally inherit.
3. **Append-only by default.** Versioning, health checks, and watchers append records rather than mutating history.
4. **Swift and backend in sync.** New backend endpoints get matching Swift models and `AcruxService` methods.

---

## Shared data model

These tables/columns are reused by multiple features. They are additive; existing columns remain.

### `facts` table (semantic memory)

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INTEGER PK | Existing fact id. |
| `parent_id` | INTEGER NULL | Hierarchical memory (#1). Root facts are NULL. |
| `version_group_id` | INTEGER NULL | Memory versioning (#2). All versions of the same fact share one group id. |
| `is_current` | INTEGER DEFAULT 1 | Memory versioning (#2). Exactly one version per group is current. |
| `fact_type` | TEXT DEFAULT 'positive' | Negative knowledge (#8): `positive` or `negative`. |
| `cluster_id` | INTEGER NULL | Auto-clustering (#3). Foreign key to `clusters`. |
| `inheritance_mode` | TEXT DEFAULT 'none' | Cross-project inheritance (#4): `none`, `inherits`, `shared`. |
| `decay_score` | REAL DEFAULT 0 | Memory decay visualization (#10). 0 = fresh, 1 = stale. |
| `last_recalled_at` | TEXT NULL | Decay / temporal reasoning (#9, #10). |
| `checksum` | TEXT NULL | Data integrity checksums (#32). SHA-256 of content + metadata. |

Indexes: `idx_facts_parent`, `idx_facts_version_group`, `idx_facts_cluster`, `idx_facts_type`, `idx_facts_decay`.

### `fact_versions` table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INTEGER PK | |
| `fact_id` | INTEGER FK → facts | The fact this version belongs to. |
| `content` | TEXT | Snapshot of content at this version. |
| `tags` | TEXT JSON | Snapshot of tags. |
| `edited_at` | TEXT | ISO timestamp. |
| `edited_by` | TEXT | `user`, `reflection`, `import`, etc. |

### `clusters` table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INTEGER PK | |
| `project` | TEXT | |
| `label` | TEXT NULL | Human-readable auto-generated label. |
| `centroid_vector` | TEXT JSON | Average embedding of member facts (optional). |
| `created_at` / `updated_at` | TEXT | |

### `project_layers` table (cross-project inheritance)

| Column | Type | Purpose |
|--------|------|---------|
| `project` | TEXT | Child project. |
| `base_project` | TEXT | Parent / shared layer. |
| `layer_order` | INTEGER | Inheritance order. |

### `fact_relationships` table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INTEGER PK | |
| `project` | TEXT | |
| `source_fact_id` | INTEGER FK → facts | |
| `target_fact_id` | INTEGER FK → facts | |
| `relation_type` | TEXT | `related`, `contradicts`, `depends_on`. |
| `strength` | REAL | 0–1. |

### `dependencies` table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INTEGER PK | |
| `project` | TEXT | |
| `source_ref` | TEXT | File path, command, skill id, etc. |
| `source_type` | TEXT | `file`, `command`, `skill`, `fact`, `test`. |
| `target_ref` | TEXT | Depends on. |
| `target_type` | TEXT | |
| `dependency_type` | TEXT | `imports`, `calls`, `reads`, `produces`. |
| `detected_at` | TEXT | |

### `code_reviews` table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INTEGER PK | |
| `project` | TEXT | |
| `file_path` | TEXT | |
| `line_range` | TEXT | e.g. `12-34`. |
| `comment` | TEXT | Review comment. |
| `resolution` | TEXT NULL | `accepted`, `rejected`, `pending`. |
| `reviewer` | TEXT | `user` or model name. |
| `timestamp` | TEXT | |

### `test_results` table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INTEGER PK | |
| `project` | TEXT | |
| `test_name` | TEXT | |
| `file_path` | TEXT NULL | |
| `passed` | INTEGER | |
| `output` | TEXT | Truncated. |
| `duration_ms` | INTEGER | |
| `root_cause` | TEXT NULL | Extracted failure reason. |
| `run_at` | TEXT | |

### `file_summaries` table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INTEGER PK | |
| `project` | TEXT | |
| `path` | TEXT | Relative path in workspace. |
| `summary` | TEXT | LLM or heuristic summary. |
| `content_hash` | TEXT | Hash of the file when summarized. |
| `last_modified` | TEXT | File mtime. |
| `indexed_at` | TEXT | |

### `workspace_watcher_state` table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INTEGER PK | |
| `project` | TEXT | |
| `path` | TEXT | File path. |
| `last_seen_mtime` | TEXT | |
| `last_seen_hash` | TEXT | |
| `last_diff` | TEXT NULL | Stored diff on significant change. |

### `health_checks` table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INTEGER PK | |
| `project` | TEXT NULL | NULL = global. |
| `check_type` | TEXT | `checksum`, `storage`, `orphan`, `conflict`, `stale`. |
| `severity` | TEXT | `info`, `warning`, `error`. |
| `message` | TEXT | |
| `created_at` | TEXT | |
| `resolved_at` | TEXT NULL | |

### `chat_pins` table

| Column | Type | Purpose |
|--------|------|---------|
| `chat_id` | TEXT | |
| `message_id` | TEXT | |
| `created_at` | TEXT | |

### `project_system_prompts` table

| Column | Type | Purpose |
|--------|------|---------|
| `project` | TEXT PK | |
| `prompt_text` | TEXT | Custom system prompt. |
| `updated_at` | TEXT | |

### `storage_checksums` table

| Column | Type | Purpose |
|--------|------|---------|
| `file_path` | TEXT PK | Relative to data_dir. |
| `checksum` | TEXT | |
| `checked_at` | TEXT | |

---

## Phase 1: Core memory structure

### 1. Hierarchical memory — parent/child facts

**What it does:** Facts can have parents and children. A fact like “Acrux uses FastAPI” can have children “Acrux uses hnswlib for vectors” and “Acrux uses SQLite for facts”.

**Why it matters:** Memory becomes navigable and allows summarization at different granularities.

**Data model:** Add `parent_id` to `facts`. Add `fact_relationships` table for non-hierarchical links.

**Backend changes:**
- `PATCH /api/memories/facts/{fact_id}` gains `parent_id` parameter.
- New `POST /api/memories/facts/{fact_id}/children` to create a child fact.
- New `GET /api/memories/facts/{fact_id}/tree` returns the subtree.
- `SemanticStore` adds `get_children`, `get_ancestors`, `link_facts`.

**Swift UI changes:**
- `MemoryInspectorView`: indent children, show disclosure triangles.
- New `MemoryTreeView.swift`.

**Implementation approach:** SQLite self-join; load tree lazily (depth-limited) to keep UI fast. Embeddings stay on each fact; hierarchy is metadata.

---

### 2. Memory versioning — keep history of edits to a fact

**What it does:** Every edit to a fact creates a row in `fact_versions` instead of overwriting.

**Why it matters:** Users can see what changed, revert, and audit reflection-induced edits.

**Data model:** `facts.version_group_id`, `facts.is_current`, plus new `fact_versions` table.

**Backend changes:**
- `PATCH /api/memories/facts/{fact_id}` becomes version-aware: it inserts a new version row and updates `facts` to point to it.
- New `GET /api/memories/facts/{fact_id}/versions`.
- New `POST /api/memories/facts/{fact_id}/versions/{version_id}/restore`.

**Swift UI changes:**
- `MemoryInspectorView`: add a “History” section.
- New `FactVersionHistoryView.swift`.

**Implementation approach:** On update, copy old row to `fact_versions`, then update `facts`. Re-embedding happens only if content changes. Keep a configurable max version count per fact (default 50) to cap storage.

---

### 3. Auto-clustering — group related facts into topics without manual tags

**What it does:** Unsupervised grouping of facts into topics/clusters.

**Why it matters:** Removes the need to manually tag every fact; surfaces emergent themes.

**Data model:** `clusters` table, `facts.cluster_id`.

**Backend changes:**
- New `POST /api/acrux/cluster` triggers clustering for a project.
- New `GET /api/acrux/clusters` lists clusters.
- New `GET /api/memories/facts?cluster_id=...`.

**Implementation approach:**
- If embeddings are enabled, run k-means or HDBSCAN on fact vectors (cap facts to 2000 for weak machines; use mini-batch k-means).
- If embeddings are disabled, fall back to keyword/title overlap + connected components.
- Label clusters with the most common keywords or a short LLM prompt (only on `standard`/`workstation`).
- Schedule as an optional daemon job, not real-time.

---

### 4. Cross-project memory inheritance — let projects share a base layer of facts

**What it does:** A project can inherit facts from a “base” project or `global`.

**Why it matters:** Common conventions (e.g., coding standards, CI patterns) are stored once and reused.

**Data model:** `project_layers` table, `facts.inheritance_mode`.

**Backend changes:**
- New `GET/POST/DELETE /api/projects/{project}/inheritance` to manage layers.
- `SemanticStore.search` and `list_facts` union inherited facts with local facts, marking each result with `inherited_from`.
- New `GET /api/projects/{project}/effective-facts`.

**Swift UI changes:**
- New `ProjectInheritanceSettingsView.swift`.

**Implementation approach:** Read base-layer stores alongside the project store; do not copy facts unless the user “pins” one locally. Cache resolved effective facts for 60 seconds to avoid repeated joins.

---

### 8. Negative knowledge — store things that did not work

**What it does:** Explicitly remember anti-patterns, failed commands, bad assumptions.

**Why it matters:** Prevents the agent from repeating mistakes.

**Data model:** `facts.fact_type` (`positive` / `negative`).

**Backend changes:**
- `POST /api/memories/facts` gains `fact_type`.
- `GET /api/search` gains `fact_type` filter.
- Reflection engine tags extracted failure facts as `negative`.
- Conflicts (#9 existing) treats `negative` facts specially.

**Swift UI changes:**
- `MemoryInspectorView`: badge negative facts in red.
- `MessageRow`: when the model proposes something matching a negative fact, show a warning.

**Implementation approach:** Store as normal facts with type metadata. Search rank negative facts up when the query looks like a “how do I…” or “why does X fail” question.

---

### 9. Temporal reasoning — “what changed in project X last week?”

**What it does:** Answer time-bounded queries about memory changes.

**Why it matters:** Gives users situational awareness without manual archaeology.

**Data model:** Uses existing `facts.timestamp`, `episodes.timestamp`, plus `facts.last_recalled_at` and `fact_versions.edited_at`.

**Backend changes:**
- `GET /api/search` gains `since` and `until` ISO parameters.
- New `GET /api/acrux/timeline?project=...&since=...&until=...` returns merged facts/episodes/skills/versions by day.
- New WebSocket/chat tool `acrux_timeline_query`.

**Swift UI changes:**
- `MemoryInspectorView`: add a timeline strip.
- New `MemoryTimelineView.swift`.

**Implementation approach:** Query each store by timestamp, merge, sort. LLM summarization of the timeline is optional and only on capable profiles.

---

### 10. Memory decay visualization — show which facts are going stale

**What it does:** Compute and display a staleness score per fact.

**Why it matters:** Helps users decide what to verify, prune, or refresh.

**Data model:** `facts.decay_score`, `facts.last_recalled_at`.

**Backend changes:**
- New `POST /api/acrux/decay` recomputes decay scores.
- New `GET /api/acrux/decay?project=...&threshold=0.7` lists stale facts.
- Decay formula: `1 - exp(-age_days / half_life) * (1 - confidence) * recall_boost`.

**Swift UI changes:**
- New `MemoryDecayView.swift`.
- `MemoryBadges`: small color dot (green → red) next to each fact.

**Implementation approach:** Compute decay in a background job or on demand. On `minimal`/`light`, skip vector-based decay and use only age/recall.

---

### 17. Test-result memory — store which tests passed/failed and why

**What it does:** Capture test run outcomes and link failures to root causes.

**Why it matters:** The acrux learns which tests are flaky and which errors are recurring.

**Data model:** `test_results` table.

**Backend changes:**
- New `POST /api/projects/{project}/tests` to record a run.
- New `GET /api/projects/{project}/tests` to list/filter.
- New tool `acrux_record_test` in chat.
- Reflection extracts `root_cause` from failed test output.

**Swift UI changes:**
- New `TestResultsView.swift`.
- `AcruxStatusView`: show latest pass/fail ratio.

**Implementation approach:** Accept JUnit XML or simple JSON. Store truncated output. Link to episodes with matching git commit.

---

### 18. Dependency graph memory — track which files/commands depend on others

**What it does:** Store directed dependencies between files, commands, skills, and facts.

**Why it matters:** Enables impact analysis and safer refactoring suggestions.

**Data model:** `dependencies` table.

**Backend changes:**
- New `POST /api/projects/{project}/dependencies` batch ingestion.
- New `GET /api/projects/{project}/dependencies?source=...` and `?target=...`.
- Tool executor records `run_command` dependencies when commands mention files.
- File watcher (#13) records file→file dependencies on change.

**Swift UI changes:**
- New `DependencyGraphView.swift` (text/list view; visual graph is Phase 5).
- `InlineDiffView` shows impacted dependents before applying a change.

**Implementation approach:** Lightweight static parsing for common imports; heuristic extraction from command output. No full language server required.

---

### 20. Code-review memory — store review comments and resolutions

**What it does:** Persist code review threads and their resolutions.

**Why it matters:** The agent remembers feedback and applies it to future suggestions.

**Data model:** `code_reviews` table.

**Backend changes:**
- New `POST /api/projects/{project}/reviews`.
- New `GET /api/projects/{project}/reviews?file_path=...`.
- Reflection includes open review comments when summarizing a project.

**Swift UI changes:**
- New `CodeReviewView.swift`.
- `InlineDiffView` shows pending review comments on suggested lines.

**Implementation approach:** Store comments keyed by file + line range. When a file is read, include relevant open comments in context.

---

## Phase 2: Memory I/O and automation

### 5. Memory import from Notion/Obsidian — pull notes into semantic memory

**What it does:** Import Markdown/JSON exports from Notion or Obsidian vaults as facts.

**Why it matters:** Bootstraps the acrux from existing knowledge bases.

**Data model:** Reuses `facts`; adds `source` values like `notion-import`, `obsidian-import`.

**Backend changes:**
- New `POST /api/import/notion` and `/api/import/obsidian`.
- Accept multipart file upload or a folder path.
- Parse Markdown frontmatter tags; split long notes into chunks; embed if enabled.

**Swift UI changes:**
- New `ImportExportView.swift` with import panel.

**Implementation approach:** Use Python stdlib / `markdown` parsing only; no new heavy dependencies. Chunk by headings. Store original URL/path in `source`.

---

### 6. Memory export to Markdown — generate a wiki from the acrux

**What it does:** Export facts, skills, and episodes as a linked Markdown wiki.

**Why it matters:** Human-readable backup and external sharing.

**Backend changes:**
- New `GET /api/export/markdown?project=...&format=obsidian|plain`.
- Generates `index.md`, `facts/<slug>.md`, `skills/<slug>.md`, `episodes/YYYY-MM/<slug>.md`.
- Wikilinks between related facts.

**Swift UI changes:**
- Add “Export Markdown wiki” button in `ImportExportView.swift`.

**Implementation approach:** Plain file write to a chosen directory. No templating engine; use f-strings. Optional cluster-based folder structure.

---

### 11. Scheduled health checks — acrux runs acrux doctor and reports issues

**What it does:** The daemon periodically validates data integrity, storage, conflicts, and stale memories.

**Why it matters:** Catches corruption and bloat before it breaks recall.

**Data model:** `health_checks` table; `storage_checksums` table.

**Backend changes:**
- Extend `daemon.py` with `HealthCheckScheduler`.
- New `GET /api/acrux/health` returns latest checks.
- New `POST /api/acrux/health/run` triggers checks now.
- Checks: SQLite PRAGMA integrity, checksums, orphan facts, unresolved conflicts, storage quota.

**Swift UI changes:**
- New `HealthCheckView.swift`.
- Sidebar status dot turns yellow/red on warnings.

**Implementation approach:** Run checks during daemon idle time or on demand. Store results; do not auto-delete user data.

---

### 12. Auto-summarize long files — index file summaries into memory

**What it does:** Watch/workspace scan produces concise summaries of large files and stores them as facts.

**Why it matters:** The LLM can recall file purpose without reading the whole file.

**Data model:** `file_summaries` table plus facts with `source: file-summary`.

**Backend changes:**
- New `POST /api/projects/{project}/summarize-file`.
- New `GET /api/projects/{project}/file-summaries`.
- Only summarize files above a line/byte threshold; skip binary.
- Summaries are produced by the reflection model if available, otherwise by a simple heuristic (docstring + first 10 lines).

**Swift UI changes:**
- `MemoryInspectorView` shows file summaries as a special card type.

**Implementation approach:** Summarize on demand and cache by `content_hash`. Invalidate when file mtime changes. On low-RAM profiles, heuristic-only.

---

### 13. Background workspace watcher — detect file changes and store relevant diffs

**What it does:** A lightweight file watcher records meaningful workspace changes as episodes/diffs.

**Why it matters:** The acrux learns from actual development activity, not just chat sessions.

**Data model:** `workspace_watcher_state` table; reuses `episodes` and `dependencies`.

**Backend changes:**
- Extend `daemon.py` with `WorkspaceWatcher` using `watchdog` or `fsevents` (macOS).
- New `POST /api/projects/{project}/watcher/start|stop`.
- New `GET /api/projects/{project}/watcher/status`.
- Significant changes (non-temp, non-ignored) create an episode with a diff summary.

**Swift UI changes:**
- New `WatcherSettingsView.swift`.
- `AcruxStatusView` shows watched projects.

**Implementation approach:** Use `fsevents` on macOS; polling fallback on other platforms. Debounce 5 seconds. Ignore `.git`, `.venv`, build dirs. On `minimal` profile, watcher is disabled.

---

### 32. Data integrity checksums — detect corrupted DBs

**What it does:** Compute and verify checksums for SQLite/YAML data files.

**Why it matters:** Detects disk corruption and silent data loss.

**Data model:** `storage_checksums` table.

**Backend changes:**
- `acrux doctor` computes checksums and stores them.
- Daemon verifies checksums on schedule.
- New `GET /api/acrux/checksums`.

**Swift UI changes:**
- `HealthCheckView.swift` shows checksum status.

**Implementation approach:** SHA-256 of each file in `~/.acrux/data`. Check on startup and daily. If mismatch, emit a `health_checks` row and warn; do not auto-repair.

---

### 33. Storage quota alerts — warn before hitting the limit

**What it does:** Warn when `~/.acrux/data` approaches `retention.max_storage_gb`.

**Why it matters:** Prevents unexpected disk-full failures.

**Data model:** Reuses `health_checks`.

**Backend changes:**
- Check storage on daemon scheduler and API status.
- `GET /api/acrux/status` adds `storage_used_bytes`, `storage_limit_bytes`, `storage_percent`.
- Emit `health_checks` row when >80% and >95%.

**Swift UI changes:**
- `AcruxStatusView` shows a storage bar.
- Alert banner when >90%.

**Implementation approach:** Reuse `AcruxConfig.check_storage_budget()`. Update on status fetch.

---

## Phase 3: Agentic execution

### 14. Agent loop mode — autonomous tool sequences with periodic user checkpoints

**What it does:** The model can run multiple tool turns automatically, pausing at configurable checkpoints (every N turns, before dangerous tools, or on errors).

**Why it matters:** Increases autonomy while keeping the human in the loop.

**Backend changes:**
- Extend WebSocket chat protocol with `type: checkpoint` event.
- Add `loop_mode`, `checkpoint_interval`, `checkpoint_tools` to chat metadata.
- New tool categories: `safe`, `destructive`, `irreversible`.
- Before a destructive tool or every N turns, send `checkpoint` and wait for `resume`, `step`, or `stop`.

**Swift UI changes:**
- `ChatView`: checkpoint banner with resume/step/stop buttons.
- `NewTaskView`: add “Agent loop” mode toggle.

**Implementation approach:** Minimal change to existing turn loop. Checkpoint state stored in chat metadata. Default to current single-turn approval behavior.

---

### 16. Auto-rollback suggestions — when a command fails, suggest the last known good state

**What it does:** On `run_command` failure, look up git state / last successful episode and suggest a rollback.

**Why it matters:** Reduces time spent recovering from bad commands.

**Data model:** Reuses `episodes.git_info`, new `test_results`, `dependencies`.

**Backend changes:**
- Tool executor records git commit before/after commands.
- New `GET /api/projects/{project}/rollback-suggestion?after_command=...`.
- Suggests `git checkout <commit>` or reverting specific files.

**Swift UI changes:**
- `MessageRow`: failed command output includes a “Suggest rollback” button.
- New `RollbackSuggestionView.swift`.

**Implementation approach:** Use existing `git_context()` helper. Compare current git state to the last episode with `outcome` containing “success”.

---

### 7. Episode replay — how it would work (not selected)

**What it would do:** Re-run a stored skill with the original workspace context.

**Why it matters:** Makes procedural memory executable and verifiable.

**Design:**
1. An episode stores `context`, `actions`, `git_info`, and captured environment variables.
2. A “replay” reconstructs the original workspace state when possible:
   - `git checkout <episode.git_info.commit>` if the repo is clean or the user confirms a stash.
   - Replay each `Action` in order: `read_file`, `run_command`, etc.
3. For `run_command` actions, the system warns before execution and requires approval unless the skill derived from the episode is already verified.
4. Outputs are compared to the stored `outcome`; divergence is recorded as a new episode.
5. If the original files no longer exist, replay falls back to applying stored diffs to the current workspace.

**Backend endpoints (not to implement now):**
- `POST /api/episodes/{session_id}/replay` — start replay.
- `GET /api/episodes/{session_id}/replay/status` — current step and diff.
- `POST /api/episodes/{session_id}/replay/step` — execute next action.
- `POST /api/episodes/{session_id}/replay/abort`.

**Swift UI (not to implement now):**
- `EpisodeReplayView.swift` with step-by-step diff viewer and approve/abort buttons.

---

## Phase 4: UI/UX enhancements (Swift app)

### 21. Floating Acrux widget — small always-on-top panel for quick recall

**What it does:** A compact, draggable, always-on-top window for quick memory search and note capture.

**Swift changes:**
- New `FloatingAcruxWidget.swift`.
- New `AcruxAppDelegate.swift` extension to manage `NSPanel`.
- Toggle via menu bar / command palette.

**Implementation approach:** `NSPanel` with `NSWindow.Level.floating`. Talks to `AcruxService.searchMemory` and `acrux_remember_fact`.

---

### 22. Chat tabs — multiple chats side by side

**What it does:** Open several chats in tabs within the same window.

**Swift changes:**
- New `ChatTabsView.swift`.
- Modify `ChatView` to be embeddable in a tab.
- `ChatStore` already persists chats.

**Implementation approach:** Use `TabView` with `Identifiable` chat tabs. Each tab gets its own WebSocket connection or serializes access.

---

### 23. Message search — search inside chat history

**What it does:** Full-text search across all persisted chat messages.

**Swift changes:**
- New `MessageSearchView.swift`.
- `ChatStore` adds an in-memory search index or loads all chats and filters.

**Implementation approach:** Load persisted chats from `~/.acrux/app/chats`, filter by content. For large history, add a lightweight SQLite FTS index later.

---

### 24. Code blocks with copy/run buttons — render and execute code suggestions

**What it does:** Detect Markdown code blocks in assistant messages and add copy / run buttons.

**Swift changes:**
- Modify `MessageRow` to parse code blocks.
- New `CodeBlockView.swift`.
- “Run” executes in the chat workspace via a new safe tool endpoint.

**Implementation approach:** Regex parse triple-backtick blocks. Copy uses `NSPasteboard`. Run sends the code as a `run_command` with explicit user approval.

---

### 25. Pinned messages — pin important assistant answers

**What it does:** Pin messages so they persist visibly in the chat.

**Swift changes:**
- Add `pinned` flag to `Message`.
- Add `chat_pins` persistence (SQLite or JSON sidecar).
- `MessageRow`: pin button; pinned messages stick to top of scroll view.

**Implementation approach:** Store pins in chat file or separate table. UI keeps pinned messages at the top.

---

### 26. Custom model system prompts per workspace — different behavior per project

**What it does:** Each workspace/project can define a custom system prompt.

**Backend changes:**
- `project_system_prompts` table.
- `GET/POST /api/projects/{project}/system-prompt`.
- Chat endpoint uses project prompt if set, otherwise default.

**Swift changes:**
- New `ProjectSystemPromptView.swift`.
- `NewTaskView`: choose workspace, then optionally edit its prompt.

**Implementation approach:** Store prompt in backend. Fetch when chat starts and prepend to system message.

---

### 27. Drag-and-drop files into chat — easier than the attach button

**What it does:** Accept files dragged onto the chat input or message list.

**Swift changes:**
- `ChatInputBar` and `ChatView` add `.dropDestination` modifiers.
- Reuse existing attach logic.

**Implementation approach:** SwiftUI `dropDestination` with `UTType.fileURL`. Read text files; reject binaries or show a placeholder.

---

### 28. Inline diff viewer — show file changes the model suggests

**What it does:** When the model proposes file edits, render a side-by-side or unified diff.

**Swift changes:**
- New `InlineDiffView.swift`.
- `MessageRow` detects diff content and renders it.
- Add accept/reject buttons per diff.

**Implementation approach:** Accept diff in unified format or Git-style `---/+++`. Use SwiftUI text with color-coded line backgrounds.

---

### 29. Command palette — Cmd+Shift+P for all app actions

**What it does:** A fuzzy-searchable command palette for every app action.

**Swift changes:**
- New `CommandPaletteView.swift`.
- `AcruxApp` registers global `Command+Shift+P` shortcut.
- Actions: new chat, search memory, start/stop acrux, open status, compact memory, run health check, etc.

**Implementation approach:** Maintain a list of `CommandPaletteItem` with title, shortcut, and closure. Filter with `localizedCaseInsensitiveContains`.

---

### 30. Status bar menu extra — Acrux icon in the macOS menu bar

**What it does:** A menu bar icon showing acrux status and quick actions.

**Swift changes:**
- `AcruxAppDelegate.swift`: `NSStatusItem`.
- Menu items: show/hide floating widget, new chat, memory status, quit.

**Implementation approach:** `NSStatusBar` with `NSStatusItem`. Keep lightweight; do not run backend from menu bar alone.

---

## Phase 5: Knowledge graph UI

### Obsidian-style bubble graph in the Swift app

**Goal:** A visual, interactive graph where projects and memories are bubbles. The graph must feel instant on a 16 GB workstation and still be usable on a 4 GB server running a minimal Acrux build.

**Core design:**
- Each **project** is a colored group of bubbles.
- Every project group connects to a central **“Acrux”** node.
- Bubbles represent **memories**: facts, episodes, skills, clusters.
- Bubble size = confidence or importance.
- Bubble color = memory type (fact/episode/skill/negative/cluster).
- Lines represent relationships: parent/child, version history, dependencies, shared keywords, cluster membership.
- **Hover** (or long-press) shows the memory title and a snippet of content.
- Click navigates to `MemoryInspectorView`.

**Smart-loading architecture:**
The Swift client is deliberately thin. It does not decide what to load or how to simplify; the backend returns only what the current viewport and zoom level need.

1. **Server-side graph simplification**
   - `GET /api/projects/{project}/graph` accepts `zoom`, `center_x`, `center_y`, `viewport_w`, `viewport_h`, `max_nodes`.
   - The backend builds a full logical graph in memory, then simplifies it before serialization.
   - Simplification rules:
     - At zoomed-out levels, collapse clusters into single meta-nodes; hide individual facts.
     - At medium zoom, show cluster members but collapse stale/weak facts into their parent cluster.
     - At full zoom, show individual facts, episodes, and skills inside the visible viewport only.
     - Always include the central Acrux node and project group anchors.
   - Profile-aware limits:
     - `workstation` / `standard`: up to 5 000 logical nodes, serialize ~500 nodes.
     - `light`: up to 1 000 logical nodes, serialize ~150 nodes.
     - `minimal`: graph endpoint returns project groups + clusters only; facts are fetched one at a time on click.

2. **Viewport culling**
   - The backend only returns nodes whose projected position falls inside the requested viewport (with a small margin).
   - Edges are filtered to those whose both endpoints are visible, except for a small set of “important” cross-project edges that are always included.

3. **Level-of-detail (LOD) nodes**
   - Each returned node carries a `detail_level`: `meta`, `summary`, or `full`.
   - `meta`: id, type, label, x, y, radius, color.
   - `summary`: adds content snippet, confidence, decay score.
   - `full`: adds tags, source, timestamps, relationships.
   - The client renders `meta` as simple circles, `summary` with hover cards, `full` with rich inspectors.

4. **Incremental expansion**
   - Double-clicking (or pinching open) a meta-node fires `GET /api/projects/{project}/graph?expand=<node_id>`.
   - The backend returns only the children of that node, already simplified for the new zoom level.
   - The client merges the new nodes into the existing SpriteKit scene instead of reloading the whole graph.

5. **Client render budget**
   - The Swift side sets a render budget based on device RAM:
     - ≥ 16 GB: 2 000 sprites.
     - 8 GB: 800 sprites.
     - 4 GB: 300 sprites.
   - If the backend sends more nodes than the budget, the client downgrades distant nodes to cheaper representations or drops labels.
   - No hard cap on total memory count; the cap is on what is rendered at once.

6. **Prefetch and cache**
   - When the user pans, the client requests the next viewport tile before it enters view.
   - Recently fetched graph tiles are cached in memory for 60 seconds and on disk as JSON for offline reuse.

**Data source:**
- `GET /api/projects/{project}/graph?zoom=...&center_x=...&center_y=...&viewport_w=...&viewport_h=...&max_nodes=...&expand=...`
- Returns `nodes` (`id`, `type`, `label`, `x`, `y`, `radius`, `color`, `detail_level`, `content_snippet`, `confidence`, `decay_score`, `parent_id`) and `edges` (`source`, `target`, `type`, `strength`, `visible`).

**Swift view:**
- New `KnowledgeGraphView.swift`.
- Use SpriteKit (already used for the home animation) for the node/edge layer.
- A SwiftUI overlay provides filters, search, zoom controls, and a breadcrumb trail.
- Filters: show/hide episodes, skills, negative facts, stale facts, cross-project links.

**Performance for low-RAM / low-storage machines:**
- On `minimal` builds the graph is read-only and cluster-based; individual facts are never laid out in bulk.
- Graph simplification runs in a background thread on the server and is killed if it exceeds a time budget (2 s for `light`, 5 s for `standard`).
- Serialized graph responses are gzip-compressed.
- The client does not keep the full graph in RAM; only visible tiles and one prefetch ring.

**Do not implement yet.** This section is design-only.

---

## API endpoint summary table

| Method | Path | Feature | Purpose |
|--------|------|---------|---------|
| GET | `/api/acrux/status` | existing + storage quota | Status + storage usage. |
| POST | `/api/acrux/cluster` | #3 | Trigger auto-clustering. |
| GET | `/api/acrux/clusters` | #3 | List clusters. |
| GET/POST/DELETE | `/api/projects/{project}/inheritance` | #4 | Manage base layers. |
| GET | `/api/projects/{project}/effective-facts` | #4 | Inherited + local facts. |
| POST | `/api/import/notion` | #5 | Import Notion export. |
| POST | `/api/import/obsidian` | #5 | Import Obsidian vault. |
| GET | `/api/export/markdown` | #6 | Export wiki. |
| GET | `/api/memories/facts/{fact_id}/versions` | #2 | List versions. |
| POST | `/api/memories/facts/{fact_id}/versions/{version_id}/restore` | #2 | Restore version. |
| GET | `/api/memories/facts/{fact_id}/tree` | #1 | Get fact tree. |
| POST | `/api/memories/facts/{fact_id}/children` | #1 | Create child fact. |
| POST | `/api/memories/facts/{fact_id}/link` | #1 | Link two facts. |
| GET | `/api/acrux/timeline` | #9 | Time-bounded timeline. |
| POST | `/api/acrux/decay` | #10 | Recompute decay scores. |
| GET | `/api/acrux/decay` | #10 | List stale facts. |
| POST | `/api/projects/{project}/tests` | #17 | Record test run. |
| GET | `/api/projects/{project}/tests` | #17 | List test results. |
| POST | `/api/projects/{project}/dependencies` | #18 | Ingest dependencies. |
| GET | `/api/projects/{project}/dependencies` | #18 | Query dependencies. |
| POST | `/api/projects/{project}/reviews` | #20 | Add review comment. |
| GET | `/api/projects/{project}/reviews` | #20 | List review comments. |
| POST | `/api/projects/{project}/summarize-file` | #12 | Summarize a file. |
| GET | `/api/projects/{project}/file-summaries` | #12 | List summaries. |
| POST | `/api/projects/{project}/watcher/start` | #13 | Start file watcher. |
| POST | `/api/projects/{project}/watcher/stop` | #13 | Stop file watcher. |
| GET | `/api/projects/{project}/watcher/status` | #13 | Watcher status. |
| GET | `/api/acrux/health` | #11 | Latest health checks. |
| POST | `/api/acrux/health/run` | #11 | Run health checks now. |
| GET | `/api/acrux/checksums` | #32 | Verify checksums. |
| GET | `/api/projects/{project}/rollback-suggestion` | #16 | Suggest rollback. |
| GET/POST | `/api/projects/{project}/system-prompt` | #26 | Custom prompts. |
| GET | `/api/projects/{project}/graph` | Knowledge graph | Graph nodes/edges. |

---

## Swift view / file changes summary

### New files

| File | Feature |
|------|---------|
| `MemoryTreeView.swift` | #1 hierarchy |
| `FactVersionHistoryView.swift` | #2 versioning |
| `ProjectInheritanceSettingsView.swift` | #4 inheritance |
| `ImportExportView.swift` | #5, #6 import/export |
| `MemoryDecayView.swift` | #10 decay |
| `MemoryTimelineView.swift` | #9 temporal |
| `TestResultsView.swift` | #17 tests |
| `DependencyGraphView.swift` | #18 dependencies (list) |
| `CodeReviewView.swift` | #20 reviews |
| `WatcherSettingsView.swift` | #13 watcher |
| `HealthCheckView.swift` | #11, #32, #33 health |
| `RollbackSuggestionView.swift` | #16 rollback |
| `ProjectSystemPromptView.swift` | #26 custom prompts |
| `FloatingAcruxWidget.swift` | #21 floating widget |
| `ChatTabsView.swift` | #22 tabs |
| `MessageSearchView.swift` | #23 search |
| `CodeBlockView.swift` | #24 code blocks |
| `InlineDiffView.swift` | #28 diff |
| `CommandPaletteView.swift` | #29 command palette |
| `KnowledgeGraphView.swift` | Knowledge graph |
| `AcruxStatusBarController.swift` | #30 menu extra |

### Modified files

| File | Change |
|------|--------|
| `AcruxService.swift` | Add methods for every new endpoint; handle checkpoint events. |
| `ChatView.swift` | Tabs, drag-drop, checkpoint banner, code blocks, pinned messages. |
| `MessageRow.swift` | Code blocks, pins, diff rendering, negative-knowledge warnings. |
| `SidebarView.swift` | Add new navigation items; storage/health indicators. |
| `HomeView.swift` | Integrate tabs and command palette. |
| `NewTaskView.swift` | Agent loop options, custom prompt, watcher toggle. |
| `MemoryInspectorView.swift` | Hierarchy, versions, decay badges, file summaries, reviews. |
| `AcruxApp.swift` / `AcruxAppDelegate.swift` | Status bar, floating widget, global shortcuts. |
| `Chat.swift` / `Message.swift` | Add `pinned`, `loop_mode`, checkpoint fields. |
| `Constants.swift` | Possibly new keyboard shortcuts. |

---

## Low-RAM constraints

- **Profile awareness:** Every expensive operation reads `AcruxConfig.profile`. `minimal` disables embeddings, clustering, watchers, file summarization, and full graph layout. `light` allows keyword-only clustering, heuristic summaries, and cluster-level graph views.
- **Caps:** Clustering caps input facts to 2000. Version history keeps last 50 versions per fact. Health checks run no more than once per hour.
- **Storage quota:** All new append-only tables participate in `retention.max_storage_gb`; warn at 80%, stop non-essential indexing at 95%.
- **Lazy loading:** Trees, timelines, and graphs load incrementally. The Swift UI never holds the entire `~/.acrux/data` in memory.
- **Graph smart loading:** The graph has no fixed node cap. The backend simplifies the logical graph based on zoom, viewport, and profile, and the client enforces only a render budget. See Phase 5 for details.

---

## Recommended order of implementation

1. Storage quota + data integrity (#32, #33, #11 scaffolding) — low risk, high trust.
2. Core fact schema changes (#1, #2, #8) — unlock many downstream features.
3. Temporal queries and decay (#9, #10).
4. Import/export (#5, #6).
5. Cross-project inheritance (#4).
6. Auto-clustering (#3).
7. Workspace watcher + file summaries (#13, #12).
8. Dependencies, tests, reviews (#18, #17, #20).
9. Agent loop + rollback (#14, #16).
10. Swift UI polish: tabs, search, code blocks, diff, drag-drop, pins, prompts (#22-#28).
11. Floating widget + status bar (#21, #30).
12. Command palette (#29).
13. Knowledge graph UI (Phase 5) — design-only for now.

---

## Notes for implementers

- Do **not** write implementation code from this document. Create a task-level execution plan first.
- Preserve existing behavior for current profiles. Add new columns with `DEFAULT` values and migration logic in `_migrate_columns`.
- Keep the Swift app native (no webview). Match the existing dark theme and `Color(red: 0.0, green: 0.83, blue: 1.0)` accent.
- All new LLM usage must be optional and skipped when `reflection.provider == "none"`.
- Maintain backward compatibility in the WebSocket chat protocol; new message types are additive.
