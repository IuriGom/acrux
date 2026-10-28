# Foundation: Trusted Learning and Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Acrux learning evidence-rich, reversible, recoverable, and idle-safe without changing its selected Ollama models.

**Architecture:** Add focused capture/provenance, journal, backup, and verification services around the existing Click CLI, SQLite stores, and daemon. Preserve existing store APIs where callers depend on their return types, use durable before-images for crash recovery, and treat FTS/vector indexes as derivable from relational SQLite state.

**Tech Stack:** Python 3.10+, Click, SQLite/FTS5, httpx, pytest/pytest-asyncio, real Git CLI repositories, POSIX shell.

**Spec:** `docs/superpowers/specs/2026-10-28-foundation-trusted-learning-design.md`

## Global Constraints

- Do not change qwen3:8b or bge-m3 configuration and do not add dependencies.
- stdout/stderr caps are 16 KiB each; diff caps are 32 KiB/file and 256 KiB/session.
- Manual verification uses `think: false`, `num_ctx: 4096`, `num_predict: 8`, 30-second HTTP timeout, and `keep_alive: "30s"`.
- Automatic reflection performs no fact or skill re-verification; new-skill validation during extraction remains allowed.
- Secret-like files are excluded before content reads; captured text is redacted before Acrux persists it.
- Pre-existing dirty-tree content is never attributed to a wrapped command.
- Journal before-images commit before data mutations; do not rely on cross-database WAL atomicity.
- Metrics, observational recall counters, health history, configuration, and API tokens are not rolled back or included in backups.
- Preserve existing mutation return types (`add_pending_fact() -> int`, promotion methods `-> bool`); batch IDs are exposed by `MutationBatch.id` and reflection results.
- Every task is committed only after its focused tests and existing related tests pass. Never stage `.acrux`, runtime databases, logs, tokens, or private memories.

## Review Focus

- Dirty worktree with pre-existing edits and untracked files: only the command's delta is stored; pinned by Task 4 `test_dirty_baseline_excludes_preexisting_changes`.
- Crash after a data commit but before its after-image: startup blocks new batches and the named undo restores the before-image; pinned by Task 8 `test_incomplete_batch_recovers_with_exact_command`.
- Commit adding a feature module with internal error handling: diff-only evidence must not call it `fix`; pinned by Task 6 `test_error_handling_in_new_feature_module_is_feature`.
- Backup manifest containing traversal or symlinked payload paths: restore rejects it before creating a safety backup; pinned by Task 9 `test_restore_rejects_traversal_and_symlinks_before_mutation`.
- Malformed/timeout Ollama verdicts and cancellation: no fact mutation occurs and every client closes; pinned by Task 2 `test_verification_bounds_verdicts_and_cleanup`.

---

### Task 1: Eligible-Only, Nonoverlapping Reflection

**Files:**
- Modify: `acrux/daemon.py:26-213`
- Modify: `acrux/reflection/base.py`
- Modify: `acrux/reflection/ollama.py:13-97`
- Modify: `acrux/reflection/engine.py:21-63,235-244`
- Modify: `acrux/memory/semantic.py:41-64`
- Modify: `acrux/app/main.py:909-924`
- Test: `acrux/tests/test_daemon_resources.py`

**Interfaces:**
- Produces: `ReflectionEngine.close() -> None`; `SemanticStore.close() -> None`; no-op `ReflectionProvider.close() -> None` with Ollama override.
- Produces: `AcruxDaemon._eligible_projects() -> list[str]` and a full-run/per-project overlap guard.
- Consumes: existing `EpisodicStore.count_unreflected(project) -> int` before creating semantic/procedural stores or embedders.

- [ ] **Step 1: Write failing scheduler and cleanup tests**

```python
async def test_idle_projects_make_no_ollama_or_expensive_store_calls(...):
    # Two real episodic DBs, one with compacted-only episodes and one pending.
    # Patch config.create_embedder, SemanticStore, ProceduralDBStore, ReflectionEngine.
    # Only the pending project reaches those constructors.

async def test_scheduler_never_reverifies(...):
    # Patch SkillVerifier and daemon._run_reverify to raise if called.
    await daemon._run_reflection()  # must complete without either call.

async def test_overlapping_full_run_is_skipped_and_clients_close(...):
    # Hold the first run with an event; a second run returns without another engine.
    # Release/cancel the first; provider and embedder close exactly once.
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest acrux/tests/test_daemon_resources.py -v`
Expected: FAIL because every project is constructed, verification runs, and engines have no `close()`.

- [ ] **Step 3: Implement eligibility, guards, and deterministic ownership**

Add `_eligible_projects()` that creates only episodic stores and skips missing, `_`-prefixed, and zero-pending projects. Make `_run_reflection()` return immediately when a full run is active, skip an already-active project, and remove automatic `verify_project()` / `_run_reverify()` calls. Keep `_run_reverify()` only as an explicit-call compatibility wrapper; the scheduler must not call it.

Add no-op provider `close()`, Ollama `close()` using `client.aclose()`, `SemanticStore.close()` closing its owned embedder, and `ReflectionEngine.close()` closing provider then semantic resources. Use `try/finally` in the daemon and `/api/acrux/reflect`. Add `keep_alive: "30s"` to normal Ollama generation without changing existing `num_ctx`, `num_predict`, model, or thinking behavior.

- [ ] **Step 4: Run focused and related tests**

Run: `.venv/bin/python -m pytest acrux/tests/test_daemon_resources.py acrux/tests/test_reflection_validation.py acrux/tests/test_skill_feedback.py acrux/tests/test_stores.py -v`
Expected: PASS; no scheduler path invokes verification or constructs resources for idle projects.

- [ ] **Step 5: Commit the Ollama scheduler slice**

```bash
git add acrux/daemon.py acrux/reflection acrux/memory/semantic.py acrux/app/main.py acrux/tests/test_daemon_resources.py
git commit -m "fix: make scheduled reflection idle-safe"
```

### Task 2: Bounded Explicit Verification

**Files:**
- Modify: `acrux/verify.py`
- Modify: `acrux/daemon.py:162-213`
- Modify: `acrux/cli.py:553-589`
- Modify: `acrux/app/main.py:4283-4334`
- Test: `acrux/tests/test_verification_http.py`

**Interfaces:**
- Produces: `async OllamaFactVerifier.verify_fact(content: str) -> str | None`, returning only `Yes`, `No`, or `Uncertain`.
- Produces: `async OllamaFactVerifier.reverify_project(semantic: SemanticStore, project: str, limit: int) -> list[dict[str, Any]]`.
- Produces: `async OllamaFactVerifier.close() -> None`; verifier owns one `httpx.AsyncClient(timeout=30.0)`.

- [ ] **Step 1: Write failing request/verdict/cleanup tests**

```python
async def test_verification_bounds_verdicts_and_cleanup(...):
    # Capture request JSON and client timeout.
    assert payload["think"] is False
    assert payload["keep_alive"] == "30s"
    assert payload["options"] == {"num_ctx": 4096, "num_predict": 8}
    assert client.timeout == 30 seconds
    # Responses "Yes", "No", "Uncertain" are accepted case-insensitively.
    # Empty, multiword, unknown, HTTP error, and timeout results return None
    # and leave verification counters unchanged; close/cancellation closes once.
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest acrux/tests/test_verification_http.py -v`
Expected: FAIL because current requests have a 60-second timeout and no bounds or strict verdict handling.

- [ ] **Step 3: Implement the shared verifier and route all explicit callers through it**

Put `OllamaFactVerifier` in `acrux/verify.py`, with prompt construction, strict first-token normalization, and `finally`-safe close semantics. Replace duplicate CLI, API, and daemon request bodies with this service. CLI and API call it only after an explicit command/request; malformed verdicts append an error result without `record_verification()`.

- [ ] **Step 4: Run focused and existing verification tests**

Run: `.venv/bin/python -m pytest acrux/tests/test_verification_http.py acrux/tests/test_reverify.py acrux/tests/test_daemon_resources.py -v`
Expected: PASS; explicit verification works and automatic verification remains absent.

- [ ] **Step 5: Commit the verification slice**

```bash
git add acrux/verify.py acrux/daemon.py acrux/cli.py acrux/app/main.py acrux/tests/test_verification_http.py
git commit -m "fix: bound explicit Ollama verification"
```

### Task 3: Failure Evidence Capture

**Files:**
- Create: `acrux/capture.py`
- Modify: `acrux/models.py:13-38`
- Modify: `acrux/cli.py:1394-1435`
- Test: `acrux/tests/test_failure_capture.py`

**Interfaces:**
- Produces: `cap_text(text: str, limit: int = 16384) -> tuple[str, bool]`.
- Produces: `redact_text(text: str) -> str` and `normalize_error(exit_code: int, stdout: str, stderr: str) -> str`.
- Produces: optional `Action.exit_code`, `stdout`, `stderr`, `error_signature`, `output_truncated` with backward-compatible `to_dict()` / `from_dict()`.

- [ ] **Step 1: Write failing capture and CLI tests**

```python
def test_stream_caps_preserve_utf8_and_exit_status(...):
    # Cap multibyte text at 16384 bytes without UnicodeDecodeError.
    # Nonzero wrapped command preserves its exact exit code and streams output.

def test_redaction_and_error_signature(...):
    # Bearer tokens, token/password assignments, URL credentials, and private-key
    # blocks become [REDACTED]; paths/line numbers/addresses are normalized.
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest acrux/tests/test_failure_capture.py -v`
Expected: FAIL because the new fields/utilities do not exist.

- [ ] **Step 3: Implement bounded redacted capture**

Implement UTF-8-safe truncation, focused credential patterns, and stable error signatures. `wrap` persists redacted bounded streams and exit metadata, while preserving child output and exit status for the caller. Successful empty stderr produces an empty error signature.

- [ ] **Step 4: Run focused and model/store tests**

Run: `.venv/bin/python -m pytest acrux/tests/test_failure_capture.py acrux/tests/test_stores.py acrux/tests/test_claude_watcher.py -v`
Expected: PASS; old serialized actions still load.

- [ ] **Step 5: Commit failure capture**

```bash
git add acrux/capture.py acrux/models.py acrux/cli.py acrux/tests/test_failure_capture.py
git commit -m "feat: capture bounded command failure evidence"
```

### Task 4: Dirty-Baseline Worktree Deltas

**Files:**
- Create: `acrux/provenance.py`
- Modify: `acrux/models.py`
- Modify: `acrux/capture.py`
- Test: `acrux/tests/test_worktree_provenance.py`

**Interfaces:**
- Produces: `CodeChange` dataclass with project, session ID, nullable commit SHA, relative path, change type, diff, truncation, source, timestamp, and content hash.
- Produces: `WorktreeSnapshot.capture(path: Path, project: str, session_id: str) -> WorktreeSnapshot`.
- Produces: `WorktreeSnapshot.changes_since() -> list[CodeChange]`, comparing pre-command state to current state and cleaning temporary snapshots.
- Produces: `is_secret_path(path: Path) -> bool`.

- [ ] **Step 1: Write failing real-Git baseline/limit/security tests**

```python
def test_dirty_baseline_excludes_preexisting_changes(tmp_path):
    # Real repo: dirty an existing file and create an old untracked file.
    # Snapshot; change only part of the dirty file and add a new file.
    # Assert stored diff lacks pre-existing hunks and old untracked content.

def test_binary_secret_symlink_and_caps(tmp_path):
    # .env/private keys are never opened; binary gets metadata only;
    # escaping symlinks are skipped; per-file/session truncation is explicit.
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest acrux/tests/test_worktree_provenance.py -v`
Expected: FAIL because baseline capture is absent.

- [ ] **Step 3: Implement safe before/after snapshots**

Before process execution, record eligible tracked-modified and untracked paths, status, hashes, and private temporary pre-images. Generate diffs pre-image → post-image, not `HEAD` → post-image. Handle add/modify/delete/rename/binary and clean temporary files in `finally`. Enforce UTF-8-safe 32 KiB/file and 256 KiB/session limits.

- [ ] **Step 4: Run focused tests**

Run: `.venv/bin/python -m pytest acrux/tests/test_worktree_provenance.py acrux/tests/test_failure_capture.py -v`
Expected: PASS on real temporary Git repositories.

- [ ] **Step 5: Commit baseline capture**

```bash
git add acrux/provenance.py acrux/models.py acrux/capture.py acrux/tests/test_worktree_provenance.py
git commit -m "feat: capture command-only worktree deltas"
```

### Task 5: Persist and Link `code_changes`

**Files:**
- Create: `acrux/memory/provenance.py`
- Modify: `acrux/memory/semantic.py:24-46,73-329`
- Modify: `acrux/cli.py:1399-1435`
- Test: `acrux/tests/test_code_changes.py`

**Interfaces:**
- Consumes: Task 4 `CodeChange` and `WorktreeSnapshot.changes_since()`.
- Produces: `SemanticStore.add_code_change(change: CodeChange) -> int`.
- Produces: `SemanticStore.list_code_changes(project: str, session_id: str | None = None, commit_sha: str | None = None, file_path: str | None = None, limit: int = 100) -> list[CodeChange]`.

- [ ] **Step 1: Write failing schema/link/idempotency tests**

```python
def test_wrap_links_only_command_delta_to_episode(...):
    # Invoke real wrap in a dirty real repo with configured temporary data dir.
    # Load episode and code_changes by session ID; assert exact path/delta.

def test_code_changes_upsert_is_idempotent(tmp_path):
    # Adding the same project/commit/path/content hash twice returns an existing
    # identity and leaves one row; indexes support session/commit/path queries.
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest acrux/tests/test_code_changes.py -v`
Expected: FAIL because the table/methods do not exist.

- [ ] **Step 3: Implement the migration and wrap integration**

Create `code_changes` with the spec's fields, indexes, and uniqueness constraint. Compose `ProvenanceStoreMixin` into `SemanticStore`. In `wrap`, take the snapshot before `subprocess.run`, collect changes afterward, and persist rows linked to the same `wrap-*` session before the episode. Non-Git directories produce no changes and no failure.

- [ ] **Step 4: Run focused and schema tests**

Run: `.venv/bin/python -m pytest acrux/tests/test_code_changes.py acrux/tests/test_worktree_provenance.py acrux/tests/test_stores.py -v`
Expected: PASS.

- [ ] **Step 5: Commit provenance storage**

```bash
git add acrux/memory/provenance.py acrux/memory/semantic.py acrux/cli.py acrux/tests/test_code_changes.py
git commit -m "feat: link code changes to learning episodes"
```

### Task 6: Deterministic Git Ingestion

**Files:**
- Create: `acrux/git_ingest.py`
- Modify: `acrux/cli.py`
- Test: `acrux/tests/test_git_ingest.py`

**Interfaces:**
- Consumes: Task 5 `add_code_change()` and existing `EpisodicStore.add()`.
- Produces: `classify_commit(subject: str, files: list[CommitFile]) -> tuple[str, float]`.
- Produces: `ingest_git(path: Path, project: str, semantic: SemanticStore, episodic: EpisodicStore, max_commits: int | None = None) -> dict[str, int]`.
- CLI: `acrux ingest-git PATH --project PROJECT [--max-commits N]`.

- [ ] **Step 1: Write failing classification and real-repository tests**

```python
def test_error_handling_in_new_feature_module_is_feature():
    # No fix wording in subject; new module/export plus error handling.
    assert classify_commit(subject, files)[0] == "feature"

def test_ingest_is_idempotent_and_never_calls_llm(tmp_path):
    # Real docs/test/fix/refactor/feature/chore/merge/empty commits.
    # Import twice; counts/episodes/code_changes remain stable and embedder/LLM
    # boundaries are never invoked. Remote credentials are absent from metadata.
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest acrux/tests/test_git_ingest.py -v`
Expected: FAIL because the importer/CLI does not exist.

- [ ] **Step 3: Implement newest-first idempotent ingestion**

Parse commit metadata and first-parent diffs with Git CLI. Apply docs/tests precedence, then subject-corroborated fixes, constrained diff-only fixes, refactor, feature, and chore. Diff-only error handling cannot override net-new modules/exports. Store one commit episode and per-file changes; validate the selection before writing and surface malformed repository errors without partial import.

- [ ] **Step 4: Run focused and provenance tests**

Run: `.venv/bin/python -m pytest acrux/tests/test_git_ingest.py acrux/tests/test_code_changes.py -v`
Expected: PASS.

- [ ] **Step 5: Commit Git ingestion**

```bash
git add acrux/git_ingest.py acrux/cli.py acrux/tests/test_git_ingest.py
git commit -m "feat: ingest semantic git history"
```

### Task 7: Project Lock and Durable Mutation Journal

**Files:**
- Create: `acrux/memory/locks.py`
- Create: `acrux/memory/journal.py`
- Modify: `acrux/daemon.py`
- Test: `acrux/tests/test_mutation_journal.py`

**Interfaces:**
- Produces: `project_write_lock(project_dir: Path)` context manager using a project-local `.write.lock` file.
- Produces: `MutationJournal(project_dir)` with `begin(operation) -> str`, `record_before(...) -> int`, `record_after(...) -> None`, `complete(batch_id) -> None`, `incomplete() -> list[BatchInfo]`, and `latest() -> BatchInfo | None`.
- Produces: `MutationBatch(project_dir, operation)` context manager exposing `.id`; it refuses new batches while an incomplete batch exists.
- Produces: `IncompleteBatchError` whose message includes `acrux undo BATCH_ID --project PROJECT`.

- [ ] **Step 1: Write failing durability/lock/crash tests**

```python
def test_before_image_is_durable_before_data_mutation(tmp_path):
    # Journal failure injection proves ordering: before -> data -> after -> complete.

def test_incomplete_batch_warning_and_lock_exclusion(tmp_path):
    # Simulate a crash; a second MutationBatch is refused with exact recovery
    # command, reads remain possible, and lock is released after exceptions.
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest acrux/tests/test_mutation_journal.py -v`
Expected: FAIL because lock/journal modules do not exist.

- [ ] **Step 3: Implement WAL-safe journal protocol**

Create `journal.db` with batch/entry tables and exact JSON row images. Commit before-images before store mutations and after-images afterward; never assume attached-WAL atomicity. `complete()` marks completion only after all entries have after-images. On daemon startup, log every incomplete batch and its recovery command without rolling back automatically.

- [ ] **Step 4: Run focused tests**

Run: `.venv/bin/python -m pytest acrux/tests/test_mutation_journal.py acrux/tests/test_daemon_resources.py -v`
Expected: PASS.

- [ ] **Step 5: Commit journal foundation**

```bash
git add acrux/memory/locks.py acrux/memory/journal.py acrux/daemon.py acrux/tests/test_mutation_journal.py
git commit -m "feat: journal durable memory mutation batches"
```

### Task 8: Store Integration and Exact Batch Undo

**Files:**
- Create: `acrux/undo.py`
- Modify: `acrux/memory/episodic.py`
- Modify: `acrux/memory/procedural_db.py`
- Modify: `acrux/memory/facts.py`
- Modify: `acrux/memory/semantic.py`
- Modify: `acrux/reflection/engine.py`
- Modify: `acrux/cli.py`
- Test: `acrux/tests/test_undo.py`

**Interfaces:**
- Consumes: Task 7 `MutationBatch`, journal entries, and lock.
- Produces: `UndoCoordinator(project_dir).undo(batch_id: str | None = None, last: bool = False) -> UndoResult`.
- CLI: `acrux undo [BATCH_ID] --project PROJECT [--last] [--yes]`.
- Covered mutations: episode add/delete/mark_compacted; skill add/update/delete/pending/promote/reject; fact add/update/delete/pending/promote/reject/record_verification. Existing return types remain unchanged.

- [ ] **Step 1: Write failing exact-restore/conflict/search/crash tests**

```python
def test_incomplete_batch_recovers_with_exact_command(tmp_path):
    # Commit a data row with a before-image but no after-image. Warning names
    # the batch; confirmed undo removes it and permits the next batch.

def test_multi_store_undo_restores_rows_fts_vectors_and_pending(tmp_path):
    # Apply one reflection batch across real DBs; undo recreates deleted rows,
    # removes new rows, restores pending state, and agrees with FTS/vector search.

def test_undo_conflict_and_confirmation_are_atomic(tmp_path):
    # Later changed row differs from after-image; no entry is restored.
    # Unknown/already-undone batches and missing --yes leave data unchanged.
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest acrux/tests/test_undo.py -v`
Expected: FAIL because mutations are not journaled and undo is absent.

- [ ] **Step 3: Integrate journal entries without changing caller return types**

Wrap covered mutation bodies with `MutationBatch` and journal before/after row images, propagating an existing batch ID through reflection and promotion flows. Keep observational counters/health out of the journal. Include relational `fact_embeddings`; rebuild FTS and vector indexes from restored relational state rather than journaling opaque index files.

- [ ] **Step 4: Implement confirmed undo and audit**

Validate current rows against after-images before any write; for a crashed final entry lacking an after-image, use the locked current row as its observed after state. Restore in reverse sequence under the project lock, mark undone only after success, and write an audit event rather than a new ordinary batch. `--last` selects newest completed not-undone; incomplete batches require an explicit ID. CLI prompts unless `--yes`.

- [ ] **Step 5: Run focused and all store/reflection tests**

Run: `.venv/bin/python -m pytest acrux/tests/test_undo.py acrux/tests/test_mutation_journal.py acrux/tests/test_stores.py acrux/tests/test_procedural_db.py acrux/tests/test_reverify.py acrux/tests/test_reflection_validation.py -v`
Expected: PASS.

- [ ] **Step 6: Commit undo**

```bash
git add acrux/undo.py acrux/memory acrux/reflection/engine.py acrux/cli.py acrux/tests/test_undo.py
git commit -m "feat: add exact batch undo for memory mutations"
```

### Task 9: Checked SQLite Backups

**Files:**
- Create: `acrux/backup.py`
- Modify: `acrux/config.py`
- Test: `acrux/tests/test_backup.py`

**Interfaces:**
- Produces: `BackupService(data_dir: Path, backup_root: Path)` with `create() -> BackupManifest`, `list() -> list[BackupInfo]`, and `restore(reference: str) -> RestoreResult`.
- Produces: `AcruxConfig.backup_dir`, defaulting to `~/.acrux/backups` outside `data_dir`.
- Manifest: format/schema versions, ID/timestamp, normalized relative payload paths, sizes, SHA-256 hashes, roles/projects, and excluded category names.

- [ ] **Step 1: Write failing creation/checksum/restore safety tests**

```python
def test_restore_rejects_traversal_and_symlinks_before_mutation(tmp_path):
    # Absolute, .., and symlink payloads fail before safety backup creation or
    # any live-data change.

def test_backup_restore_round_trip_and_safety(tmp_path):
    # Real WAL SQLite DBs; create, mutate, restore; original state returns,
    # config/token content is absent, and a safety backup preserves mutated state.
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest acrux/tests/test_backup.py -v`
Expected: FAIL because the service does not exist.

- [ ] **Step 3: Implement SQLite backup API snapshots and manifest validation**

Snapshot live project/global episodic, semantic, skills, pending-containing, and journal DBs using `sqlite3.Connection.backup()` under project/global write locks. Exclude config, logs, PID/lock files, and rebuildable vector/FTS caches. Validate schema compatibility, normalized paths, sizes, and all hashes before restore. Stage beside live data, run `PRAGMA integrity_check`, create a safety backup, replace data, and roll back on failure. Rebuild derived indexes on next store open.

- [ ] **Step 4: Run focused tests**

Run: `.venv/bin/python -m pytest acrux/tests/test_backup.py acrux/tests/test_mutation_journal.py -v`
Expected: PASS; no runtime configuration or secrets appear in backup payloads.

- [ ] **Step 5: Commit backup service**

```bash
git add acrux/backup.py acrux/config.py acrux/tests/test_backup.py
git commit -m "feat: add checked sqlite backups"
```

### Task 10: Backup CLI and Upgrade Integration

**Files:**
- Modify: `acrux/cli.py`
- Modify: `install/upgrade.sh:1-14,93-110,195-230`
- Modify: `install/README.md`
- Test: `acrux/tests/test_backup_cli.py`
- Modify: `acrux/tests/test_install_scripts.py`

**Interfaces:**
- CLI: `acrux backup create [--output DIR]`, `acrux backup list [--output DIR]`, `acrux backup restore BACKUP_ID_OR_PATH [--yes]`.
- Consumes: Task 9 `BackupService` and existing daemon `PidFile` state.

- [ ] **Step 1: Write failing CLI and upgrade-order tests**

```python
def test_backup_cli_requires_confirmation_and_running_daemon_stopped(...):
    # Restore refuses a running daemon and lacks of --yes; no live mutation.

def test_upgrade_backs_up_after_stop_before_install_and_aborts(...):
    # Stub log order is stop -> backup create -> uv upgrade -> doctor -> daemon.
    # A nonzero backup command prevents uv/doctor/restart and prints the failure.
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest acrux/tests/test_backup_cli.py acrux/tests/test_install_scripts.py -v`
Expected: FAIL because backup commands/upgrade step are absent.

- [ ] **Step 3: Implement thin CLI adapters and script ordering**

Add the Click `backup` group, exact reporting of backup/safety IDs, confirmation, and daemon-write prevention. Update `upgrade.sh` and its header flow to stop → backup → install/migrate → doctor → restart; abort on backup failure without changing config. Document commands in `install/README.md`.

- [ ] **Step 4: Run focused and installer tests**

Run: `.venv/bin/python -m pytest acrux/tests/test_backup_cli.py acrux/tests/test_install_scripts.py acrux/tests/test_backup.py -v`
Run: `sh -n install/upgrade.sh`
Expected: PASS and zero shell syntax errors.

- [ ] **Step 5: Commit CLI/upgrade integration**

```bash
git add acrux/cli.py install/upgrade.sh install/README.md acrux/tests/test_backup_cli.py acrux/tests/test_install_scripts.py
git commit -m "feat: protect upgrades with restorable backups"
```

### Task 11: End-to-End Acceptance and Operator Documentation

**Files:**
- Create: `acrux/tests/test_foundation_e2e.py`
- Modify: `docs/quickstart.md`
- Modify: `docs/OPERATING.md`
- Modify: `docs/superpowers/specs/2026-10-28-foundation-trusted-learning-design.md` (status only after acceptance)

**Interfaces:**
- Consumes: all public CLI/service behavior from Tasks 1-10.

- [ ] **Step 1: Write the complete real-system acceptance scenario**

Use one temporary real Git repository and temporary Acrux data/config directories. Exercise failing wrap → edit/pass wrap → real commit → ingest twice → eligible-only reflection with no automatic verification → journaled undo → backup → live mutation → confirmed restore. Assert evidence, commit classification, exact restored rows/search, checksums, safety backup, and zero idle Ollama calls.

- [ ] **Step 2: Run the scenario to establish the baseline**

Run: `.venv/bin/python -m pytest acrux/tests/test_foundation_e2e.py -v`
Expected: PASS once Tasks 1-10 are complete; if it fails, fix the owning slice before continuing and rerun its focused tests.

- [ ] **Step 3: Document operator workflows**

Document wrap evidence, `ingest-git`, explicit verification, incomplete-batch recovery, undo confirmation/conflicts, backup/restore, and the upgrade backup guarantee. Do not claim automatic secret detection is exhaustive. Change spec status to `Implemented and verified` only after all steps below pass.

- [ ] **Step 4: Run complete project verification**

Run: `.venv/bin/python -m pytest acrux/tests -v`
Expected: PASS with no skipped new foundation tests.

Run: `.venv/bin/ruff check acrux`
Expected: PASS.

Run: `git diff --check && git status --short`
Expected: no whitespace errors; only intended acceptance/doc changes before commit.

- [ ] **Step 5: Verify real daemon idleness and model release**

With no pending episodes, run the actual configured daemon through a scheduler trigger. Confirm no Ollama generate/embed requests originate from Acrux, then create bounded explicit work and confirm qwen3:8b leaves Ollama's loaded-model list after the 30-second keep-alive. Record exact observed commands/results; do not claim this step from unit tests alone.

- [ ] **Step 6: Inspect and commit the final acceptance slice**

Review staged names/content for private memories, runtime DBs, logs, credentials, and temporary snapshots. Commit only source/tests/docs.

```bash
git add acrux/tests/test_foundation_e2e.py docs/quickstart.md docs/OPERATING.md docs/superpowers/specs/2026-10-28-foundation-trusted-learning-design.md
git commit -m "test: verify trusted learning recovery end to end"
```
