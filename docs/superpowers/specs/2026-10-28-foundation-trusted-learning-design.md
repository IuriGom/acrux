# Foundation: Trusted Learning and Recovery — Design Spec

Date: 2026-10-28
Status: Implemented and verified

## Purpose

Make Acrux's learning pipeline trustworthy and affordable to run. A wrapped command should preserve enough evidence to explain a failure and its fix; learned memories should link back to code changes; durable mutations should be reversible; installations should be recoverable; and an idle Acrux daemon should not keep an Ollama model busy or resident.

This package implements approved ideas #8, #9, #11, #29, #30, and #50, plus the approved Ollama resource fix. It deliberately excludes every deferred or rejected idea and does not change the qwen3:8b model selection.

## Success criteria

- `acrux wrap` preserves the command, exit status, bounded stdout/stderr, a normalized error signature, and bounded per-file diffs while redacting obvious credentials.
- `code_changes` links a project and episode/session to a commit, file path, change classification, and captured diff where those values are available.
- `acrux ingest-git` imports real Git history idempotently and classifies commits as feature, fix, refactor, docs, test, or chore without an LLM.
- Every durable memory mutation covered by the new mutation layer receives a batch ID and before/after journal entries. `acrux undo --last` and `acrux undo <batch-id>` restore exact recorded state rather than deleting by timestamp.
- Backups are consistent SQLite snapshots with manifests and SHA-256 checksums. Restore validates the complete backup, creates a safety backup, and never includes configuration or API tokens.
- Scheduled reflection considers only projects with unreflected episodes. It performs no automatic fact or skill re-verification and makes zero Ollama calls for idle projects.
- Manual verification uses `think: false`, a 4K context, 8 output tokens, a 30-second request timeout, and a 30-second keep-alive. Reflection has bounded keep-alive, background jobs cannot overlap, and provider/embedder clients close deterministically.
- The complete fail → fix → pass → commit → reflect → undo → backup/restore scenario passes against temporary real Git repositories and SQLite databases, followed by the full existing Python test suite.

## Current problems and evidence

- `acrux/cli.py` currently records only a human-readable outcome in `Action.result`; stdout, stderr, and diffs are discarded.
- Git context currently contains branch, commit, dirty state, and diff statistics, not file-level provenance.
- The workspace watcher records modification times rather than actual changes.
- Scheduled reflection iterates every project, creates semantic/procedural stores and providers before establishing that work exists, then runs skill verification and Ollama fact re-verification after every reflection.
- Fact verification currently has no thinking, context, output, or keep-alive bounds and uses a 60-second client timeout.
- The investigated workstation had 72 projects but only 34 with unreflected work. A run could continue for hours through hundreds of verification prompts, keeping qwen3:8b resident and repeatedly timing out.

## Scope and non-goals

In scope:

1. Failure evidence capture in `acrux wrap`.
2. File-level diff provenance and deterministic Git-history ingestion.
3. Journaling and confirmed batch undo for durable memory mutations.
4. Backup creation, listing, validation, and restore, including upgrade integration.
5. Scheduler eligibility, explicit-only verification, Ollama request bounds, job exclusion, and client cleanup.
6. Tests, documentation for the new commands, and a separate commit for each completed tested slice.

Out of scope:

- Automatic semantic re-verification or background skill execution.
- Changing the configured reflection or embedding models.
- Timestamp-based undo, metrics/health-history rollback, or configuration rollback.
- Capturing secrets, `.env` files, private keys, logs, local runtime state, or unrelated private data in Git.
- New embedding providers, an LLM-based commit classifier, or an LLM-based undo/recovery system.
- The deferred and rejected ideas from the original idea review.

## Architecture

The work is divided into small units with explicit boundaries:

- **Capture utilities** normalize errors, redact sensitive text, enforce UTF-8-safe byte limits, classify secret-like paths, and produce bounded unified diffs.
- **Provenance storage** owns `code_changes` and idempotent Git ingestion. It links evidence to episodes without asking an LLM to interpret history.
- **Mutation journal** owns batch metadata and before/after row snapshots. Store mutation methods delegate journal writes to this unit while retaining their existing public behavior.
- **Undo coordinator** acquires the project write lock, validates the requested batch and current state, restores recorded rows, and rebuilds affected FTS/vector state.
- **Backup service** owns SQLite backup API calls, manifests, checksums, validation, safety backups, and staged restore.
- **Learning scheduler** selects eligible projects before constructing expensive resources, prevents overlap, and delegates explicit verification to a shared bounded service.

CLI commands are thin adapters over these services. Existing storage formats remain readable; schema additions are migrations, not replacements.

## Failure capture (#8)

### Episode and action data

Extend command-action serialization compatibly with optional fields for:

- `exit_code`: integer process status, including nonzero values.
- `stdout` and `stderr`: captured text, each limited to 16 KiB.
- `error_signature`: normalized, stable summary derived from the exit status and the most relevant nonempty error line or exception signature.
- `output_truncated`: indicates whether either stream was truncated.

The existing `result` remains the human-readable outcome. `command`, task, duration, and Git context remain available. Old episodes missing the new fields deserialize with neutral defaults.

Capture limits apply independently to stdout and stderr. Truncation must not split a UTF-8 code point. The command continues to stream its captured output back to the caller and exits with the child process's original status.

### Redaction

Redact obvious credentials before storing or displaying captured evidence through Acrux. Patterns cover common bearer tokens, API-key/token/password assignments, private-key blocks, and URL-embedded credentials. Redaction replaces the secret value, not the surrounding diagnostic context.

No redaction rule is treated as a guarantee that arbitrary secrets are safe. Secret-like file paths are excluded from diff capture entirely.

### Error normalization

A normalized signature removes volatile paths, line numbers, timestamps, memory addresses, and repeated whitespace while retaining the exception/error type and useful message. Empty successful commands have no error signature. Failed commands with no stderr use the nonzero exit status and available stdout/result as fallback evidence.

## Diff provenance (#9)

### Capture

For a wrapped command inside a Git worktree, snapshot the pre-command worktree state before starting the child process. For every eligible tracked-modified and untracked file, record its path, status, content hash, and the pre-execution content needed for comparison. After the command exits, compare that baseline with the resulting worktree and generate unified diffs from the pre-command file state to the post-command file state—not from `HEAD` to the post-command state. Therefore, pre-existing dirty-tree edits and pre-existing untracked files are not attributed to the wrapped command; only the delta introduced while the command ran is written to `code_changes`.

Include additions, modifications, deletions, renames where Git reports them, and untracked files created by the command. Binary files receive metadata and a binary-change marker rather than binary content.

Limits:

- At most 32 KiB of unified diff text per file.
- At most 256 KiB of captured diff text per wrapped session.
- Truncation is explicit in both the file record and session metadata.

Exclude `.env` variants, private keys, credential stores, equivalent secret-like paths, VCS internals, and files outside the worktree. The capture must not follow a path that escapes the repository through a symlink.

### `code_changes`

Add a `code_changes` table in the project's semantic database with:

- Stable integer ID and project name.
- Episode/session ID when the change came from a wrapped or watched session.
- Commit SHA when known; nullable for uncommitted working-tree changes.
- Repository-relative file path.
- Change classification: `add`, `modify`, `delete`, `rename`, or `binary`.
- Bounded diff text and truncation flag.
- Source (`wrap` or `git-ingest`) and capture timestamp.
- A deterministic content hash for idempotent ingestion and lookups.

Indexes cover project/session, project/commit, and project/path. Git ingestion uses a uniqueness constraint based on project, commit, path, and content hash so repeated imports do not duplicate rows.

Episodes retain their existing Git context; `code_changes` supplies file-level evidence rather than embedding an unbounded diff in every episode.

## Semantic Git commits (#11)

Add:

```text
acrux ingest-git PATH --project PROJECT [--max-commits N]
```

`PATH` must identify a Git worktree. The importer walks commits newest-first, optionally bounded by `--max-commits`, and stores per-file provenance plus a commit episode. Re-running with the same repository and project is idempotent.

Each commit receives exactly one primary classification, using deterministic metadata and diff heuristics in this precedence order:

1. `docs` when all changed paths are documentation-only.
2. `test` when all changed paths are tests or test fixtures.
3. `fix` when the subject/commit message explicitly indicates bug fixing, regression, or a hotfix. Diff-level error-handling patterns can independently select `fix` only when they modify existing functions and add no net-new feature modules or exports. If such modules or exports are present, diff-level error-handling evidence cannot override `feature` without subject/commit-message corroboration.
4. `refactor` when the subject indicates restructuring without behavior change or the diff is dominated by renames/moves.
5. `feature` when the subject indicates a feature/addition or new implementation files and behavior are added.
6. `chore` for dependency, build, CI, formatting, release, and other maintenance changes.

Conventional Commit prefixes inform the decision but do not override an unambiguous all-docs or all-tests commit. A `fix:` subject is sufficient corroboration for a mixed fix/feature diff; an error-handling-only diff is not. Merge commits use their subject and first-parent diff. Empty commits are retained as commit episodes with no `code_changes` rows. Classification and confidence are stored as metadata; no Ollama or other LLM call is permitted.

Commit episodes include author, committer date, parent SHAs, subject, classification, and source repository identity, but not credentials from remotes.

## Journaled mutations and batch undo (#50)

### Journal model

Add a project-local journal database containing:

- `mutation_batches`: batch UUID, project, operation/source, creation time, completion state, undone state, and undone timestamp.
- `mutation_entries`: batch ID, sequence number, store/entity type, entity key, serialized before image, serialized after image, and enough schema metadata to restore the correct table.

A batch is created before the first mutation. Before and after images are exact row snapshots for affected facts, skills, episodes, pending facts/skills, and their FTS/vector records. Batches spanning multiple store mutations use the same ID. Store mutation APIs accept an optional batch ID to join an existing unit of work and return the batch ID used; when the caller supplies none, they create a new batch. The CLI and reflection pipeline propagate the returned ID.

Metrics, recall counters that are purely observational, and health history are not journaled and are never rolled back.

### Locking and crash behavior

All journaled mutations and undo operations acquire the same project write lock. Because SQLite WAL mode does not guarantee atomic commits across attached databases, the journal first durably commits each before-image, then the store commits its mutation, then the journal durably records the after-image. Therefore a committed row mutation always has a recovery image without relying on cross-database WAL atomicity. A multi-store batch remains incomplete until every per-store mutation and after-image is recorded. A crash between these steps leaves an incomplete batch discoverable; it can be inspected and undone, and is never silently marked complete.

On daemon startup and whenever a project write lock is acquired for a new mutation batch, Acrux checks for incomplete batches. If one exists, it emits a prominent warning containing the project, batch ID, creation time, last completed sequence, and the exact recovery command: `acrux undo BATCH_ID --project PROJECT`. New mutation batches for that project pause until the incomplete batch is explicitly recovered; reads and the undo operation remain available. Acrux does not automatically roll back crashed work, because the user must see and confirm restoration of the partial state.

Undo does not use timestamps to select rows and does not infer inverse operations from natural-language content.

### Undo commands

```text
acrux undo --last --project PROJECT
acrux undo BATCH_ID --project PROJECT
acrux undo --last --project PROJECT --yes
```

Both forms require confirmation; `--yes` is the explicit noninteractive confirmation. `--last` selects the newest completed, not-yet-undone batch. An incomplete batch must be named explicitly, with its state shown before confirmation.

The undo coordinator:

1. Acquires the project write lock and loads the ordered journal entries.
2. Refuses an already-undone or unknown batch.
3. Compares each current row with the recorded after image. If a later mutation changed the same entity, it aborts without partial restoration and reports the conflicting entities.
4. Restores exact before images in reverse sequence, including deletions of newly created rows and recreation of deleted rows.
5. Restores or deterministically rebuilds affected FTS and vector records so search agrees with restored relational state.
6. Marks the batch undone only after every store succeeds. Failure leaves the batch available for diagnosis/retry and does not produce a partial undo.

Undo is itself recorded as an audit event, not as a new ordinary memory batch. This prevents repeated `--last` calls from toggling history.

## Backup and restore (#29, #30)

### Commands

```text
acrux backup create [--output DIR]
acrux backup list [--output DIR]
acrux backup restore BACKUP_ID_OR_PATH [--yes]
```

The default backup root is outside the live data directory. A backup is a timestamped/unique directory containing `manifest.json` and SQLite snapshot files at repository-independent relative paths.

### Creation and manifest

For each live project and global SQLite database, use SQLite's backup API rather than copying database files directly. Coordinate with project write locks so journaled state and relational state agree. Include the relevant journal database and required FTS/vector persistence. Exclude configuration files, API tokens, logs, PID files, caches that can be rebuilt, and unrelated runtime data.

The manifest records:

- Manifest format version and Acrux schema versions.
- Creation timestamp and backup ID.
- Every included relative path, byte size, SHA-256 checksum, and database role/project.
- Explicit excluded categories without recording secret values.

Paths are normalized relative POSIX paths. Absolute paths and `..` traversal are invalid.

### Validation and restore

`backup list` reads manifests and reports ID, creation time, project count, size, and validation state. Restore first validates manifest structure, schema compatibility, relative paths, file sizes, and every checksum. Any mismatch aborts before live data changes.

Restore requires confirmation, prevents concurrent daemon writes, and creates a safety backup of current live data. New snapshots are staged beside the live data, checked for SQLite integrity, then moved into place with rollback to the safety backup if replacement fails. Restore does not overwrite the current configuration. Successful restore reports both the restored backup and safety-backup IDs.

### Upgrade integration

`install/upgrade.sh` follows:

```text
stop daemon → create backup → install/migrate → doctor → restart daemon
```

A backup failure aborts the upgrade before package installation or migration. The script prints the backup ID/location. Existing configuration and its token remain untouched.

## Ollama resource correction

### Eligible-only scheduling

Before creating a semantic store, procedural store, embedder, reflection provider, or verification client for a project, query its episodic store for unreflected episodes. Skip the project immediately when the count is zero.

Cron and adaptive triggers share a per-project eligibility scan and a single background-job guard. A second trigger while reflection is already running for the same project is skipped. A global scheduler run also prevents overlapping full runs. Exceptions release guards in `finally` paths.

Automatic reflection may create new pending facts/skills from new episodes. It does not call `SkillVerifier`, `_run_reverify`, or any equivalent automatic re-verification afterward.

### Explicit verification only

Fact promotion/rejection, live-fact re-verification, and executable skill verification happen only through explicit CLI or API requests. CLI and API call the same verification service so bounds and result handling cannot drift.

Manual Ollama verification requests contain:

```json
{
  "think": false,
  "stream": false,
  "keep_alive": "30s",
  "options": {
    "num_ctx": 4096,
    "num_predict": 8
  }
}
```

The HTTP timeout is 30 seconds. The verdict accepts only `Yes`, `No`, or `Uncertain`; malformed/empty responses do not mutate a fact.

### Reflection bounds and cleanup

Normal Ollama reflection retains its existing model, thinking, context, and output behavior and adds `keep_alive: "30s"`. The selected qwen3:8b configuration remains unchanged.

Reflection engines/providers and embedders support deterministic cleanup. Scheduler and explicit-job owners close every created client in `finally`, including error and cancellation paths. Idle scheduling does not instantiate these clients. No code issues a model unload request that would affect unrelated Ollama consumers; bounded keep-alive plus connection cleanup allows Ollama to release the model naturally.

## Error handling and safety

- Child-command failures are recorded without hiding the original exit status.
- Secret-path exclusion happens before reading file content for diffs.
- Git/SQLite malformed inputs produce actionable errors and no partial import.
- Journal conflicts abort the whole undo; they do not force-overwrite newer work.
- Backup validation failures happen before safety-backup creation or live replacement.
- Scheduler failure in one eligible project releases its resources and is logged; it does not trigger verification for unrelated projects.
- All new persistent schemas are migrated with the existing store conventions and remain compatible with old records.

## Testing and verification

### Unit and integration tests

Add tests beside the existing `acrux/tests` suite for:

- 16 KiB stream caps, UTF-8 boundaries, exit statuses, error normalization, and credential redaction.
- Pre-command dirty-tree baselines that exclude pre-existing edits/untracked files and capture only command-introduced deltas.
- Secret-path exclusion, binary/untracked/rename handling, 32 KiB file caps, and 256 KiB session caps.
- `code_changes` round trips and repeated-import idempotency.
- All six commit classifications, narrowed fix/feature precedence, merges, empty commits, and proof that ingestion performs no LLM calls.
- Multi-store batch undo, recreated deleted rows, removed new rows, pending records, FTS/vector consistency, conflicts, incomplete-batch warnings/recovery, confirmation, and lock use.
- Manifest/checksum validation, traversal rejection, safety-backup creation, successful restore, failed-restore rollback, and config/token exclusion.
- Upgrade-script ordering and abort-on-backup-failure.
- Zero Ollama calls for idle projects and automatic re-verification, eligible-only scheduling, overlap prevention, exact manual request bounds, and deterministic provider/embedder cleanup.

Use real temporary Git repositories and real temporary SQLite databases; mocks are limited to external HTTP/model boundaries and overlap probes.

### End-to-end acceptance

Run a temporary project through:

1. A failing wrapped command; inspect its captured error evidence.
2. A file edit and passing wrapped command; inspect file-level provenance.
3. A real Git commit and `acrux ingest-git`; verify idempotent semantic classification.
4. Reflection over only the eligible project; verify no automatic re-verification.
5. Undo of the reflected batch; verify exact relational, FTS, and vector restoration.
6. Backup creation, a live-data change, and restore; verify restored state, checksums, and safety backup.

Then run the complete Python test suite and the project's lint checks. On the actual workstation, confirm an idle daemon makes no Ollama requests and qwen3:8b unloads after keep-alive expires. Inspect the final Git diff and staged files for private memories, runtime databases, logs, tokens, and other secrets before every commit.

## Commit sequence

Keep Git history current with one commit per completed, tested slice:

1. Ollama scheduler/request/lifecycle correction.
2. Failure capture and redaction.
3. Diff provenance and `code_changes`.
4. Deterministic `ingest-git`.
5. Journaling and batch undo.
6. Backup/restore and upgrade integration.
7. End-to-end documentation and any final verification fixes.

A slice is committed only after its tests pass. The final report lists each commit and the exact verification results; unverified workstation behavior is stated plainly rather than claimed as complete.
