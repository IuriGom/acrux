# Tools: Common Pitfalls, Edge Cases, and How to Avoid Them

A collection of frequent mistakes, sharp edges, security risks, and performance traps when working with Git, the shell, Docker, package managers, build systems, and related developer tools.

---

## Git Pitfalls

### Rebase Commits That Are Already Shared

Rebasing rewrites commit hashes. If you rebase commits already pushed to a shared branch and then force-push, collaborators' local branches diverge and they may reintroduce old commits when merging.

**Rule**: only rebase local, unpushed commits or branches you are certain no one else is using.

### Force-Pushing Without `--force-with-lease`

`git push --force` overwrites remote history unconditionally. If someone else pushed in the meantime, you may silently discard their work.

```bash
# Safer
git push --force-with-lease
```

`--force-with-lease` refuses the push if the remote ref does not match what you fetched.

### Committing Secrets

Passwords, API keys, and tokens committed to Git are very hard to remove completely from history. Even after deletion, they remain in reflog, packfiles, and forks/clones.

**Prevention**:

- Use `.gitignore` and global gitignore for secrets files.
- Use tools like `git-secrets`, `trufflehog`, or `gitleaks` in pre-commit hooks.
- If leaked, rotate the credential immediately; do not rely on rewriting history alone.

### Using `git add .` Without Review

`git add .` stages every change, including debugging code, temporary files, and unrelated modifications.

**Better**: use `git add -p` or stage files explicitly, then review with `git diff --staged`.

### Writing Vague Commit Messages

Messages like "fix bug" or "update" make `git log`, `git bisect`, and code archaeology harder.

**Fix**: write commit messages that explain why the change was made and what behavior changed.

### Ignoring Merge Conflicts

Resolving a conflict by choosing "mine" or "theirs" without understanding the context can reintroduce bugs or remove features.

**Fix**: inspect the conflict markers, run tests, and ask the author of the conflicting change if unclear.

### Forgetting to Set `user.name` and `user.email`

Commits made without these configs show unknown authorship.

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

### Using `git reset --hard` Casually

`git reset --hard` discards uncommitted changes and is not undoable from within Git. It is a common source of lost work.

**Safer alternatives**:

- `git restore <file>` to discard changes in one file.
- `git stash` to save changes temporarily.
- Use `git reflog` to recover if you already reset.

### Confusing `git revert` and `git reset`

- `git reset` moves the current branch pointer (rewrites history on the current branch).
- `git revert` creates a new commit that undoes a previous commit's changes (safe for shared history).

Use `git revert` for changes already pushed to shared branches.

### Not Pulling Before Pushing

If you push without pulling latest changes, Git rejects the push. Rushing to force-push can overwrite others' work.

**Fix**: `git pull --rebase origin main` before pushing, or use `git pull` with a sensible default.

### Merge Commits in a Linear-History Project

Some projects require linear history. Merging without rebasing creates merge commits that fail CI checks.

**Fix**: use `git pull --rebase` or configure `git config pull.rebase true`.

### `git commit --amend` on Pushed Commits

Amending a pushed commit changes its hash. The next push will be rejected unless you force-push, which is risky on shared branches.

**Fix**: amend only local commits; for shared branches, make a follow-up commit instead.

### Submodules Need Explicit Updates

After cloning or pulling, submodules may remain at the wrong commit.

**Fix**: run `git submodule update --init --recursive` after clone/pull.

### Stale Remote Branches

Deleted remote branches can linger as remote-tracking refs locally.

**Fix**: `git fetch --prune` or set `fetch.prune true` globally.

### Large Files in Git

Committing large binaries bloats the repository forever, even if later deleted.

**Fix**: use Git LFS for large files. Track files with `git lfs track "*.psd"`.

### `.gitignore` Not Ignoring Already-Tracked Files

Adding a file to `.gitignore` does not untrack it if it is already committed.

**Fix**:

```bash
git rm --cached file.txt
# commit the removal; .gitignore will now take effect
```

---

## Shell Scripting Pitfalls

### Word Splitting on Unquoted Variables

```bash
filename="my file.txt"
cat $filename      # tries to cat "my" and "file.txt"
cat "$filename"    # correct
```

**Rule**: always quote variable expansions unless you explicitly want word splitting.

### Unquoted Command Substitution

```bash
output=$(ls)
rm $output         # breaks on filenames with spaces
rm "$output"       # still wrong if multiple files; use find + xargs
```

### Relying on `set -e` for All Error Handling

`set -e` does not trigger inside `if`, `while`, `||`, `&&`, or command substitutions in some contexts.

**Fix**: explicitly check important commands.

```bash
if ! command; then
    echo "failed"
    exit 1
fi
```

### Globbing an Empty Directory

```bash
for f in *.log; do
    rm "$f"        # fails with "*.log" if no matches (unless nullglob is set)
done
```

**Fix**:

```bash
shopt -s nullglob
for f in *.log; do
    [[ -f "$f" ]] || continue
    rm "$f"
done
```

### Using Backticks for Command Substitution

Backticks do not nest well and are hard to read.

**Fix**: use `$(command)`.

### Modifying the Same File You Are Reading

```bash
for f in $(cat files.txt); do ... done
```

This reads the whole file into memory, splits on whitespace, and can fail on special filenames.

**Fix**:

```bash
while IFS= read -r f; do
    [[ -f "$f" ]] || continue
    ...
done < files.txt
```

### Assuming `/bin/bash` Exists

On some systems (e.g., macOS, NixOS, BSD), Bash may not be at `/bin/bash`.

**Fix**: use `#!/usr/bin/env bash`.

### `rm -rf` Without Validation

```bash
rm -rf "$dir"/*
```

If `$dir` is empty, this deletes everything in the current directory.

**Fix**: validate and use safer patterns.

```bash
[[ -n "$dir" ]] || exit 1
find "$dir" -mindepth 1 -delete
```

### Reading Passwords with `read` Without `-s`

```bash
read password    # visible in terminal
```

**Fix**:

```bash
read -s -p "Password: " password
echo
```

### Hardcoding Secrets in Scripts

Secrets in scripts can be leaked through version control, process listings, or shell history.

**Fix**: read from environment variables, secret files, or secret managers.

### `set -e` + `source` + Errors in Sourced Files

A sourced file that fails can cause the parent script to exit unexpectedly. Be careful with `source` and strict mode.

### Using `eval` with Untrusted Input

`eval` executes its arguments as shell code. Combining `eval` with user input is a command injection risk.

**Fix**: avoid `eval`; use arrays or parameter expansion.

### Floating-Point Math in Bash

Bash only supports integer arithmetic. `$((1.5 + 2))` fails.

**Fix**: use `bc`, `awk`, or switch to Python.

### Relying on Default `IFS`

The default `IFS` splits on spaces, tabs, and newlines, causing surprises when iterating over arrays or command output.

**Fix**: set `IFS=$'\n\t'` or localize `IFS` for specific loops.

### Not Checking If a Command Exists

```bash
aws s3 ls ...
```

If `aws` is not installed, the script fails with a confusing message.

**Fix**:

```bash
command -v aws >/dev/null 2>&1 || { echo "aws CLI not found" >&2; exit 1; }
```

### Changing Directory and Not Returning

```bash
cd /tmp
# rest of script runs in /tmp
```

**Fix**: use subshells or `pushd`/`popd`.

```bash
(
    cd /tmp
    do_something
)
# back to original directory
```

### Ignoring Exit Codes in Pipelines

By default, only the last command's exit code matters in a pipeline.

```bash
cat missing.txt | grep foo   # succeeds even if cat fails
```

**Fix**: use `set -o pipefail`.

### Using `cat` Unnecessarily

```bash
cat file | grep foo
```

**Fix**: use redirection or pass the file directly.

```bash
grep foo file
```

### Writing Logs to stdout Instead of stderr

Error and diagnostic messages should go to stderr so they do not pollute piped output.

```bash
echo "error" >&2
```

### Race Conditions in `/tmp`

Predictable temporary filenames are vulnerable to symlink attacks.

**Fix**: use `mktemp` or `mktemp -d`.

---

## Docker Pitfalls

### Running Containers as Root

Root inside the container is root on the host in many default configurations. A container breakout can compromise the host.

**Fix**: create and use a non-root user in the Dockerfile.

### Baking Secrets into Images

```dockerfile
ENV API_KEY=supersecret
```

Secrets in image layers can be extracted by anyone with access to the image.

**Fix**: pass secrets at runtime with `--env-file`, Docker secrets, or orchestrator secrets. Use BuildKit secret mounts for build-time secrets.

```dockerfile
# syntax=docker/dockerfile:1
RUN --mount=type=secret,id=api_key cat /run/secrets/api_key > /tmp/key
```

### Using `latest` Tag in Production

`latest` is mutable and ambiguous. Builds may pull different images over time.

**Fix**: pin specific tags or digests.

### Forgetting `.dockerignore`

Without `.dockerignore`, build context includes `.git`, `node_modules`, build artifacts, and secrets, increasing build time and image size.

### `apt-get update` in a Separate RUN Layer

```dockerfile
RUN apt-get update
RUN apt-get install -y curl
```

If you later add a package, Docker may reuse the cached `apt-get update` layer with stale package lists.

**Fix**: combine in one layer and clean up.

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*
```

### Layer Cache Bloat

Each instruction creates a layer. Cleaning up files in a later layer does not remove them from earlier layers.

**Fix**: do cleanup in the same `RUN` instruction where files are created.

### Using `ADD` When `COPY` Is Enough

`ADD` automatically extracts archives and downloads URLs, which can cause unexpected behavior and larger layers.

**Fix**: use `COPY` for local files; use `ADD` only when you need URL fetch or auto-extraction.

### Not Handling Signals Properly

A container's main process may not forward signals (e.g., SIGTERM) to child processes, causing slow shutdowns.

**Fix**: use `exec` in entrypoint scripts so the application becomes PID 1, or use an init system like `tini`.

```bash
exec "$@"
```

### Writing to the Container Filesystem

Containers are ephemeral. Writing logs or data inside the container loses them on restart.

**Fix**: log to stdout/stderr and mount volumes for persistent data.

### Exposing Too Many Ports

`EXPOSE` documents intent but does not actually publish ports. Still, declaring unnecessary ports can confuse users.

### Ignoring Image Size

Large images increase pull time, storage cost, and attack surface.

**Fix**: multi-stage builds, minimal base images, remove build dependencies, use `.dockerignore`.

### Not Testing Builds in CI

A Dockerfile that builds locally may fail in CI due to a dirty build context or uncached layers.

**Fix**: build from a clean checkout in CI and run image tests.

### Using `curl | bash` in Dockerfiles

Downloading and executing remote scripts blindly is risky and non-reproducible.

**Fix**: pin URLs and checksums, or vendor scripts into the repository.

### Stale Base Images

Using old base images exposes containers to known CVEs.

**Fix**: rebuild images regularly, use `--pull`, scan with tools like Trivy or Docker Scout.

### Docker-in-Docker Privileges

Running Docker inside a container with the host Docker socket (`/var/run/docker.sock`) grants full host root access.

**Fix**: use Kaniko, BuildKit rootless, or carefully scoped permissions.

---

## Package Manager Pitfalls

### Not Committing Lockfiles

Without a lockfile, installs may pull different dependency versions on different machines or CI runs.

**Fix**: commit `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `Cargo.lock` (for binaries), `uv.lock`, `poetry.lock`, `go.sum`, etc.

### Mixing `npm install` and `npm ci`

`npm install` can modify `package-lock.json`. `npm ci` installs exactly from the lockfile. In CI and production, use `npm ci`.

### Pinning Too Loosely

`"*"` or unbounded ranges allow major version updates that may break your code.

**Fix**: use `^` for libraries you trust to follow semver, pin exact versions for reproducible deployments.

### Pinning Too Tightly in Libraries

Libraries with exact pins make it hard for consumers to resolve dependencies.

**Fix**: libraries should specify minimum compatible versions (`>=`) or semver ranges.

### Ignoring Security Audits

Vulnerable dependencies are a common attack vector.

**Fix**: run `npm audit`, `pnpm audit`, `pip-audit`, `cargo audit`, `bandit` regularly and in CI.

### Installing Global Tools When Local Is Better

Global installs create version conflicts between projects.

**Fix**: use project-local tools or version managers (nvm, pyenv, uv, rustup).

### Forgetting Dev Dependencies in Production

Including test frameworks, linters, and build tools in production images increases size and attack surface.

**Fix**: use production installs (`npm ci --omit=dev`), multi-stage builds, or dependency groups.

### Left-Pad Style Dependency Risk

Deep transitive dependency trees can break when a single small package is unpublished or compromised.

**Fix**: pin versions, vendor critical dependencies, use private registries or lockfiles.

### Python `requirements.txt` Without Versions

A plain list of package names without versions is not reproducible.

**Fix**: generate with `pip freeze` or use a lockfile-driven tool like uv or Poetry.

### Mixing System and Virtualenv Packages

Installing packages into the system Python can break OS tools.

**Fix**: always use virtual environments or project-local tools.

```bash
python -m venv .venv
source .venv/bin/activate
```

### Not Cleaning pip Cache

```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
```

### Using `setup.py` Directly in New Projects

Modern Python prefers `pyproject.toml` (PEP 517/518).

**Fix**: use `pyproject.toml` with a build backend like Hatchling, setuptools, or uv's backend.

---

## Build System Pitfalls

### Global Include Directories in CMake

```cmake
include_directories(include)
```

This pollutes all targets.

**Fix**: use `target_include_directories` with `PRIVATE`/`PUBLIC`/`INTERFACE`.

### Building in Source Tree

In-source builds clutter the repository with generated files.

**Fix**: use out-of-source builds.

```bash
cmake -S . -B build
cmake --build build
```

### Hardcoding Absolute Paths

Build scripts with absolute paths are not portable.

**Fix**: use CMake variables, relative paths, or environment variables.

### Not Specifying Minimum CMake Version

Older CMake versions may not support commands you use.

**Fix**: set `cmake_minimum_required(VERSION 3.20)` or similar.

### Forgetting `.PHONY` for Non-File Targets

```makefile
clean:
    rm -rf build
```

If a file named `clean` exists, Make will skip the target.

**Fix**:

```makefile
.PHONY: clean
clean:
    rm -rf build
```

### Using Tabs vs Spaces in Makefiles

Make requires real tab characters for recipe lines. Spaces cause "missing separator" errors.

### Recursive Make Considered Harmful

Recursive Make can break parallel builds and dependency tracking.

**Fix**: use a single Makefile or a proper build system generator like CMake.

### Not Caching Build Outputs

Clean builds are slow. Reuse object files and dependency caches when possible.

**Fix**: use ccache, sccache, Docker layer caching, and CI caches.

### Hardcoding Compiler Flags Globally

```cmake
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall")
```

This affects all targets, including third-party code.

**Fix**: set flags per target with `target_compile_options`.

### Ignoring Warnings

Warnings often indicate real bugs. Treat them as errors in CI.

```cmake
if(MSVC)
    target_compile_options(myapp PRIVATE /W4 /WX)
else()
    target_compile_options(myapp PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
```

---

## CI/CD Pitfalls

### Running CI on Every File Change

Running the full heavy test suite for every README change wastes resources.

**Fix**: use path filters in workflow triggers.

```yaml
on:
  push:
    paths:
      - 'src/**'
      - 'tests/**'
```

### Hardcoding Secrets in Workflow Files

```yaml
env:
  API_KEY: "super-secret"
```

This is visible in logs and repository history.

**Fix**: use GitHub Secrets, GitLab CI variables, or vault integrations.

### Not Caching Dependencies

CI runs become slow because every job downloads dependencies from scratch.

**Fix**: cache package manager caches and lockfiles.

### Running Tests After Merge Without PR Checks

A green `main` branch depends on checks running before merge.

**Fix**: require status checks before merging in branch protection rules.

### Publishing from Untrusted Branches

A workflow that publishes packages on every push can release broken or malicious code.

**Fix**: trigger releases only on tagged commits or protected branches.

### Not Using `fail-fast: false`

By default, a matrix job failure cancels all other jobs, hiding platform-specific failures.

**Fix**: set `fail-fast: false` for matrix jobs.

### Overly Broad `on: pull_request` Triggers

Running expensive jobs for draft PRs or documentation changes is wasteful.

**Fix**: use `paths`, `types`, or conditional job execution.

### Storing CI Credentials Long-Term

Long-lived tokens leaked from CI can be exploited.

**Fix**: use short-lived tokens, OIDC, and least-privilege roles.

---

## Security Pitfalls

### Command Injection in Scripts

```bash
read -p "Enter filename: " file
cat "$file"   # safer
cat $file     # unsafe if file contains spaces or ; rm -rf /
```

**Fix**: always quote variables; validate inputs; avoid `eval`.

### Path Traversal

Accepting user-supplied filenames without sanitization can read arbitrary files.

**Fix**: validate paths, use allowlists, canonicalize with `realpath`/`readlink -f`.

### Running `curl | bash`

Executing remote shell scripts without verification is dangerous.

**Fix**: download, inspect, checksum, then execute.

### Storing Credentials in Environment Variables on Shared Hosts

Environment variables are visible to all processes running as the same user.

**Fix**: use secret files, secret managers, or scoped environment injection.

### World-Writable Files

```bash
chmod 777 /app
```

**Fix**: use the minimum permissions needed, typically `644` for files and `755` for directories.

### Exposing Debug Endpoints in Production

Flask debug mode, Django DEBUG=True, and similar settings can leak secrets and enable remote code execution.

**Fix**: disable debug mode in production and validate configuration at startup.

### Using Self-Signed or Expired TLS Certificates

Expired or invalid certificates break clients and reduce trust.

**Fix**: automate certificate renewal (Let's Encrypt, cert-manager) and monitor expiry.

### Running Services as Root

Services should run with the least privilege necessary.

**Fix**: use dedicated service accounts, containers with non-root users, and capabilities dropping.

---

## General Tooling Pitfalls

### Not Reading Tool Output

Ignoring warnings, deprecation notices, and linter output allows problems to accumulate.

**Fix**: address warnings as they appear; treat CI lint failures seriously.

### Tool Version Mismatch Between Local and CI

A project may build locally with Node 20 but fail in CI with Node 18.

**Fix**: pin tool versions with `.nvmrc`, `pyproject.toml`, `rust-toolchain.toml`, `tool-versions`, or CI setup actions.

### Using Aliases in Scripts

Shell aliases are not expanded in non-interactive shells by default.

**Fix**: use functions or full commands in scripts.

### Editing Files with `sed -i` Portably

GNU `sed -i` edits in place; BSD/macOS `sed -i ''` requires an empty extension.

**Fix**: use `sed -i.bak` and remove the backup, or use a portable tool like Perl/Python.

### Assuming GNU Coreutils

macOS ships BSD utilities with different flags. Scripts using GNU-specific options may fail on macOS.

**Fix**: write POSIX-compatible commands, install `coreutils`, or detect the platform.

### Not Handling CRLF Line Endings

Windows line endings (`\r\n`) can break shebang lines and shell scripts.

**Fix**: configure Git's `core.autocrlf` appropriately or use `.gitattributes`.

```gitattributes
* text=auto eol=lf
*.sh text eol=lf
```

### Not Testing Scripts in a Clean Environment

A script may work locally because of installed tools, environment variables, or files present.

**Fix**: test in a fresh container or CI environment.

### Hardcoding Home Directory Paths

```bash
/home/alice/.config
```

**Fix**: use `$HOME` or platform-specific directories (`~/.config`, `%USERPROFILE%`).

### Ignoring Disk Space

Logs, caches, and temporary files can fill disks.

**Fix**: rotate logs, prune Docker, clean caches, and set retention policies.

### Not Documenting Manual Steps

If a workflow requires manual CLI commands, document them or automate them.

**Fix**: add tasks to Makefile/justfile/Taskfile and README.

---

## Performance Pitfalls

### Inefficient Docker Layers

Putting `COPY . .` before `RUN npm install` invalidates the dependency layer on every source change.

**Fix**: copy manifests first, install, then copy source.

### Running `find` in Loops

```bash
for f in $(find . -name "*.log"); do ... done
```

This breaks on special filenames and spawns many subshells.

**Fix**: use `find ... -exec` or `xargs -0`.

### Not Using Parallel Jobs

Builds and tests run sequentially when they could run in parallel.

**Fix**: use `make -j`, `pytest -n auto`, `cargo test --jobs`, and CI matrix parallelism.

### Over-Logging

Excessive logging slows down applications and fills storage.

**Fix**: use structured logging and configurable log levels.

### Pulling Full Images for Small Tasks

Using a `ubuntu:24.04` image just to run a tiny script is wasteful.

**Fix**: use `alpine`, `distroless`, or `busybox` images when possible.

### Not Using Incremental Builds

Cleaning the build directory every time wastes time.

**Fix**: use incremental build systems and cache build artifacts.

---

## Recovery Patterns

### Recover a Deleted File from Git

```bash
git log --diff-filter=D --summary | grep delete
# find commit before deletion
git checkout <commit-before-deletion> -- path/to/file
```

### Recover a Deleted Branch

```bash
git reflog
# find the branch tip commit
git checkout -b recovered-branch <commit-hash>
```

### Revert a Bad Merge

```bash
git revert -m 1 <merge-commit-hash>
```

`-m 1` specifies the first parent (usually the target branch).

### Undo a Bad Rebase

```bash
git reflog
# find HEAD before rebase
git reset --hard HEAD@{n}
```

### Restore a Container's Filesystem

```bash
# Create a tar of container filesystem
docker export container_name > backup.tar

# Copy specific files out
docker cp container_name:/app/data ./data
```

### Clean Up Docker Disk Usage

```bash
docker system df
docker system prune -a --volumes -f
```

### Reset a Broken Python Environment

```bash
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Reset Node Modules

```bash
rm -rf node_modules package-lock.json
npm install
```

### Reset Cargo Build Cache

```bash
cargo clean
cargo build
```

---

## Summary of Defensive Habits

1. **Quote variables** in shell scripts.
2. **Use strict mode** (`set -euo pipefail`) for Bash scripts.
3. **Never commit secrets**; use `.gitignore`, pre-commit hooks, and secret managers.
4. **Pin dependencies and base images** for reproducibility.
5. **Commit lockfiles** and use deterministic install commands in CI.
6. **Run as non-root** in containers.
7. **Use multi-stage builds** to keep images small.
8. **Review diffs** before committing, especially generated files.
9. **Test in clean environments** and CI.
10. **Validate inputs** and avoid `eval`.
11. **Use `trap` for cleanup** in scripts.
12. **Prefer explicit over implicit** in build configurations.
