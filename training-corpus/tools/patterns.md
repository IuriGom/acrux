# Tools: Idiomatic Patterns and Recipes

A collection of practical, reusable patterns for Git, shell scripting, Docker, package managers, build systems, and CLI workflows. These are the patterns an AI coding assistant should reach for when asked to solve common developer-tool problems.

---

## Git Patterns

### Feature Branch Workflow

Use a short-lived branch per feature or fix; rebase onto the main branch before merging to keep history linear.

```bash
git switch -c feature/add-search
git commit -am "Implement search endpoint"
git switch main
git pull origin main
git switch feature/add-search
git rebase main
# resolve conflicts if any
git push -u origin feature/add-search
# open pull request, review, merge
```

### Commit Message Convention

A consistent commit message style improves readability and enables automated changelogs.

```
type(scope): subject

body (optional)

footer (optional)
```

Common types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`, `build`.

Example:

```
feat(auth): add OAuth2 login with GitHub

Implements the initial OAuth2 flow using passport-github.
Adds a new `/auth/github/callback` route and stores tokens
in an httpOnly cookie.

Closes #42
```

### Atomic Commits

Each commit should represent a single logical change. Mixing unrelated changes in one commit makes review and `git bisect` harder. Stage with `git add -p` to split changes into logical commits.

### Squashing Before Merge

Clean up a noisy feature branch with interactive rebase:

```bash
git switch feature/add-search
git rebase -i main
# mark earlier commits as `fixup` or `squash`
```

Alternatively, use the merge button's "Squash and merge" option in GitHub/GitLab.

### Bisect for Regression Hunting

```bash
git bisect start
git bisect bad HEAD          # current state is broken
git bisect good v1.0.0       # known good version
# git checks out a commit; test and mark good/bad
git bisect bad
git bisect good
# repeat until git identifies the first bad commit
git bisect reset
```

### Reflog Recovery

```bash
git reflog
# find the commit hash before the destructive operation
git reset --hard HEAD@{3}
```

### Partial Commits with Patches

```bash
git add -p file.py
# choose: y n s e ?
# s = split the hunk further
# e = edit the hunk manually
```

### Stash Only Staged Changes

```bash
git stash --staged
```

Useful when you want to stash what is staged but keep unstaged edits.

### Worktrees for Parallel Contexts

```bash
git worktree add ../my-project-hotfix hotfix/urgent
cd ../my-project-hotfix
# work on the hotfix branch without touching the main checkout
git worktree remove ../my-project-hotfix
```

### Signed Commits and Tags

```bash
git commit -S -m "Signed commit"
git tag -s v1.0.0 -m "Signed release"
git verify-commit HEAD
git verify-tag v1.0.0
```

Enable automatic signing:

```bash
git config --global commit.gpgsign true
git config --global tag.gpgsign true
git config --global user.signingkey KEYID
```

### Rebase with Autosquash

When making fixup commits, name them with `git commit --fixup=HEAD` or `--fixup=<commit>`. Later:

```bash
git rebase -i --autosquash main
```

Git will automatically place fixup commits after the target commit.

### Pre-Push Checklist Script

```bash
#!/usr/bin/env bash
set -euo pipefail

main() {
    echo "Running pre-push checks..."
    make lint
    make test
    echo "OK"
}

main "$@"
```

### Branch Naming Conventions

```
feature/123-add-login
bugfix/456-fix-memory-leak
hotfix/urgent-patch
chore/update-dependencies
docs/api-reference
```

---

## Shell Scripting Patterns

### Strict Bash Template

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

if [[ "${TRACE-0}" == "1" ]]; then
    set -o xtrace
fi

cd "$(dirname "$0")"

main() {
    local name="${1:-World}"
    echo "Hello, $name"
}

main "$@"
```

### Argument Parsing

For simple scripts, manual parsing is sufficient and avoids external dependencies:

```bash
#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $0 [-n name] [-v] file" >&2
    exit 1
}

name="World"
verbose=0

while getopts ":n:vh" opt; do
    case "$opt" in
        n) name="$OPTARG" ;;
        v) verbose=1 ;;
        h | ?) usage ;;
    esac
done
shift $((OPTIND - 1))

if [[ $# -eq 0 ]]; then
    usage
fi

file="$1"

[[ "$verbose" -eq 1 ]] && echo "Processing $file"
echo "Hello, $name"
```

For complex needs, consider `argparse` in Python or tools like `docopt`.

### Reading Files Safely

```bash
while IFS= read -r line; do
    printf '%s\n' "$line"
done < "input.txt"
```

Use `-r` to prevent backslash interpretation.

### Iterating Over Files

```bash
for file in src/**/*.py; do
    [[ -f "$file" ]] || continue
    echo "$file"
done
```

Always quote `$file` and check that it exists; globbing can match directories.

### Safe Temporary Files

```bash
cleanup() {
    rm -rf "$tmpdir"
}
trap cleanup EXIT

tmpdir=$(mktemp -d)
tmpfile=$(mktemp "${tmpdir}/data.XXXXXX")
```

### Running Commands in Script Directory

```bash
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"
```

Use `${BASH_SOURCE[0]}` instead of `$0` for sourced scripts.

### Parallel Processing with `xargs`

```bash
find . -name "*.png" -print0 | xargs -0 -P 4 -I {} optipng {}
```

### Logging Helpers

```bash
log_info() { printf '[INFO] %s\n' "$*"; }
log_warn() { printf '[WARN] %s\n' "$*" >&2; }
log_error() { printf '[ERROR] %s\n' "$*" >&2; }
```

### Retry Logic

```bash
retry() {
    local attempts=5
    local delay=2
    local count=0
    until "$@"; do
        count=$((count + 1))
        if [[ $count -ge $attempts ]]; then
            log_error "Command failed after $attempts attempts"
            return 1
        fi
        log_warn "Attempt $count failed; retrying in ${delay}s..."
        sleep "$delay"
    done
}

retry curl -fsSL https://api.example.com/health
```

### Waiting for a Service

```bash
wait_for_port() {
    local host="${1:-localhost}"
    local port="${2:-8080}"
    local timeout="${3:-30}"
    local elapsed=0
    while ! nc -z "$host" "$port"; do
        if [[ "$elapsed" -ge "$timeout" ]]; then
            echo "Timed out waiting for $host:$port" >&2
            return 1
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
}

wait_for_port localhost 5432
```

### Dotenv Loader

```bash
load_env() {
    local file="${1:-.env}"
    if [[ -f "$file" ]]; then
        set -a
        # shellcheck source=/dev/null
        source "$file"
        set +a
    fi
}
```

### Backup Before In-Place Edit

```bash
backup_and_edit() {
    local file="$1"
    cp "$file" "$file.bak"
    sed -i '' 's/old/new/g' "$file"   # GNU: sed -i.bak
}
```

### Choosing Between `sh` and Bash

- Use `#!/bin/sh` when the script is simple and portable, with no arrays or `[[ ]]`.
- Use `#!/usr/bin/env bash` when you need arrays, string manipulation, or modern features.
- Switch to Python when the script exceeds ~200 lines or needs complex data structures.

---

## Docker Patterns

### Multi-Stage Python Build

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc

COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

RUN groupadd -r app && useradd -r -g app app
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

USER app

COPY . .

CMD ["python", "-m", "myapp"]
```

### Non-Root User Pattern

```dockerfile
FROM node:20-alpine
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001
WORKDIR /app
COPY --chown=nodejs:nodejs . .
USER nodejs
CMD ["node", "server.js"]
```

### Caching Dependencies Separately

Copy only dependency manifest files first so that dependency installation is cached unless the manifest changes.

```dockerfile
COPY package*.json ./
RUN npm ci
COPY . .
```

### Health Check Pattern

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsSL http://localhost:3000/health || exit 1
```

### Entrypoint Wrapper Script

```dockerfile
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["node", "server.js"]
```

```bash
#!/bin/sh
set -e

# Run migrations if available
if command -v migrate >/dev/null 2>&1; then
    migrate up
fi

exec "$@"
```

### Docker Compose Development Override

Keep production and development concerns separate:

```yaml
# compose.yaml
services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      NODE_ENV: production
```

```yaml
# compose.override.yaml (loaded automatically)
services:
  app:
    volumes:
      - .:/app
      - /app/node_modules
    environment:
      NODE_ENV: development
    command: npm run dev
```

### `.dockerignore` Template

```gitignore
# Git
.git
.gitignore

# Node
node_modules
npm-debug.log
yarn-error.log
.pnpm-debug.log

# Python
__pycache__
*.pyc
*.pyo
*.egg-info
.venv
venv

# Build artifacts
dist
build
*.md
!README.md

# IDE
.vscode
.idea
*.swp

# CI
.github
.gitlab-ci.yml
```

### Pinning Base Images

```dockerfile
# Pin tag
FROM python:3.12.4-slim-bookworm

# Pin digest for maximum reproducibility
FROM python:3.12.4-slim-bookworm@sha256:abc123...
```

### Combining apt-get Update and Install

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*
```

### Build Args for Flexibility

```dockerfile
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim
ARG APP_VERSION=dev
LABEL version="${APP_VERSION}"
```

```bash
docker build --build-arg APP_VERSION=1.0.0 -t myapp:1.0.0 .
```

---

## Package Manager Patterns

### Lockfile Hygiene

- Always commit lockfiles.
- Regenerate lockfiles when adding or upgrading dependencies.
- Review lockfile diffs in pull requests.
- Use `npm ci`, `pnpm install --frozen-lockfile`, `poetry install --no-root`, or `uv sync --locked` in CI.

### Deterministic Installs

```bash
# Node
npm ci
pnpm install --frozen-lockfile
yarn install --frozen-lockfile

# Python
uv sync --locked
poetry install --no-root

# Rust
cargo build --locked

# Go
go mod download
```

### Dependency Groups

Use dependency groups / optional dependencies for dev/test/docs tools so production images do not install them.

Python `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = ["pytest", "ruff", "mypy"]
```

or the standard `[dependency-groups]` (PEP 735):

```toml
[dependency-groups]
dev = ["pytest", "ruff", "mypy"]
```

Node:

```json
{
  "devDependencies": {
    "vitest": "^1.0.0"
  }
}
```

### Automated Dependency Updates

Use Renovate, Dependabot, or similar tools to open PRs for outdated dependencies. Configure them to group minor/patch updates and separate major updates.

### Audit Pattern

```bash
npm audit
npm audit fix
pnpm audit
poetry check
pip-audit
uv pip audit
cargo audit
```

### Publishing Packages

```bash
# npm
npm version patch
npm publish --access public

# Python with uv
uv build
uv publish

# Rust
cargo publish --dry-run
cargo publish
```

### Workspace / Monorepo Pattern

```json
{
  "name": "my-monorepo",
  "private": true,
  "workspaces": ["packages/*"]
}
```

```bash
npm install
npm run build --workspaces
npm run test --workspace=packages/core
```

Python with uv workspaces:

```toml
[tool.uv.workspace]
members = ["packages/*"]
```

---

## Build System Patterns

### CMake Target-Based Build

```cmake
cmake_minimum_required(VERSION 3.20)
project(Calculator VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(calculator STATIC
    src/calculator.cpp
)

target_include_directories(calculator
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_compile_features(calculator PUBLIC cxx_std_17)

add_executable(calc_app src/main.cpp)
target_link_libraries(calc_app PRIVATE calculator)

enable_testing()
add_subdirectory(tests)
```

### Makefile Pattern with Auto-Help

```makefile
.PHONY: help install test lint format clean

help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -r requirements.txt

test: ## Run tests
	pytest

lint: ## Run linters
	ruff check .
	mypy src/

format: ## Format code
	ruff format .

clean: ## Remove build artifacts
	rm -rf build dist *.egg-info
```

Run `make help` to see documented targets.

### Justfile Pattern

```just
set dotenv-load

build:
    cargo build --release

test:
    cargo test

lint:
    cargo clippy --all-targets --all-features

fmt:
    cargo fmt --check

dev:
    cargo watch -x run
```

### Taskfile Pattern

```yaml
version: '3'

tasks:
  build:
    cmds:
      - go build -o bin/app ./cmd/app

  test:
    cmds:
      - go test ./...

  lint:
    cmds:
      - golangci-lint run
```

### Reproducible Python Builds with uv

```bash
uv init --python 3.12 my-project
uv add requests
uv add --dev pytest ruff mypy
uv sync --locked
uv run pytest
```

### Cross-Platform Build Scripts

When a project is used on Windows, macOS, and Linux, prefer task runners or scripts written in Python/Node over Makefiles, or provide a `Taskfile.yml` / `justfile` that works everywhere.

---

## CI/CD Patterns

### Matrix Testing

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ["3.10", "3.11", "3.12"]
fail-fast: false
```

### Caching Dependencies in CI

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.cache/pip
      ~/.local/share/virtualenvs
    key: ${{ runner.os }}-python-${{ hashFiles('**/pyproject.toml', '**/uv.lock') }}
```

### Lint and Test Gate

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff mypy
      - run: ruff check .
      - run: mypy src/

  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - run: python -m pip install --upgrade pip
      - run: pip install -e '.[dev]'
      - run: pytest
```

### Docker Image Build and Push

```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3

- name: Log in to GHCR
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}

- name: Build and push
  uses: docker/build-push-action@v6
  with:
    context: .
    push: true
    tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### Security Scanning

```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ghcr.io/${{ github.repository }}:${{ github.sha }}
    format: sarif
    output: trivy-results.sarif
```

### Release Automation

```yaml
on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install build
      - run: python -m build
      - uses: softprops/action-gh-release@v2
        with:
          files: dist/*
```

---

## CLI Workflow Patterns

### Search and Replace Across a Repository

```bash
# Preview
grep -R "old_function" src/

# Replace
find src -type f -name "*.py" -exec sed -i '' 's/old_function/new_function/g' {} +
```

### Mass Rename Files

```bash
for f in *.txt; do
    mv "$f" "${f%.txt}.md"
done
```

### Bulk Format Code

```bash
# Python
find src -name "*.py" -exec ruff format {} +

# JavaScript
prettier --write "src/**/*.{js,ts,json}"

# Go
go fmt ./...
```

### Convert Between JSON and YAML

```bash
yq -P -oy data.json > data.yaml
yq -P -oj data.yaml > data.json
```

### Working with CSV

```bash
# Convert CSV to JSON
mlr --csv cat data.csv | mlr --json cat > data.json

# Filter rows
csvsql --query "SELECT * FROM data WHERE age > 18" data.csv
```

### Monitoring Logs

```bash
# Follow multiple logs
tail -f /var/log/app.log /var/log/nginx.log

# Colorize and filter
journalctl -u myapp -f | ccze -A

# Search recent errors
grep -i error /var/log/app.log | tail -n 50
```

### One-Off HTTP Servers

```bash
# Python
python -m http.server 8000

# Node
npx serve .

# PHP
php -S localhost:8000
```

### Transfer Files

```bash
# rsync (preferred)
rsync -avz --exclude='.git' ./ deploy@server:/var/www/app/

# scp
scp -r ./build deploy@server:/var/www/app/
```

### SSH Port Forwarding

```bash
# Local forward: access remote service as if local
ssh -L 8080:localhost:80 user@server

# Remote forward: expose local service on remote
ssh -R 8080:localhost:3000 user@server
```

---

## Environment and Secret Patterns

### Required Environment Variables

```bash
: "${DATABASE_URL:?DATABASE_URL is required}"
: "${API_KEY:?API_KEY is required}"
```

### Inject Secrets Without Shell History

```bash
read -s API_KEY
export API_KEY
```

### Docker Secrets in Swarm

```yaml
secrets:
  db_password:
    external: true

services:
  app:
    image: myapp:latest
    secrets:
      - db_password
```

Inside the container, read `/run/secrets/db_password`.

### Kubernetes Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: api-key
type: Opaque
stringData:
  API_KEY: "super-secret"
```

Mount as an environment variable:

```yaml
env:
  - name: API_KEY
    valueFrom:
      secretKeyRef:
        name: api-key
        key: API_KEY
```

### Loading `.env` in Python

```python
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(".env")
if env_path.exists():
    load_dotenv(env_path)
```

### Loading `.env` in Node

```javascript
if (process.env.NODE_ENV !== "production") {
    require("dotenv").config();
}
```

---

## Debugging and Troubleshooting Patterns

### Verbose Mode

Add a `--verbose` / `-v` flag that sets `set -o xtrace` or prints extra context.

### Sanitize and Validate Inputs

```bash
validate_int() {
    local value="$1"
    if ! [[ "$value" =~ ^[0-9]+$ ]]; then
        log_error "'$value' is not a positive integer"
        return 1
    fi
}
```

### Capture Command Output and Exit Code

```bash
output=$(some_command 2>&1) || {
    log_error "some_command failed with output: $output"
    exit 1
}
```

### Inspect a Running Container

```bash
docker exec -it container_name bash
docker logs --tail 100 -f container_name
docker inspect container_name
```

### Network Debugging in Containers

```bash
docker run --rm --network container:web nicolaka/netshoot
dig +short app
curl -v http://app:8080/health
```

### Check Exit Codes

```bash
some_command
if [[ $? -ne 0 ]]; then
    echo "Failed"
fi

# Better
if ! some_command; then
    echo "Failed"
fi
```

---

## Documentation Patterns

### README Checklist

A good README includes:

1. Project name and one-line description.
2. Installation instructions.
3. Quick start / usage example.
4. Configuration (environment variables).
5. Development setup (`make install`, `just dev`).
6. Testing instructions.
7. Contributing guidelines.
8. License.

### Changelog Convention

Use Keep a Changelog format:

```markdown
## [Unreleased]

### Added
- New feature X.

### Fixed
- Bug in Y.

## [1.0.0] - 2025-01-15
```

Generate release notes from conventional commits with tools like `git-cliff` or `semantic-release`.

### Makefile Self-Documentation

```makefile
help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
```

### Script Help Text

```bash
show_help() {
    cat <<EOF
Usage: $0 [OPTIONS] FILE

Options:
  -o OUTPUT   Write output to OUTPUT
  -v          Verbose mode
  -h          Show this help
EOF
}
```

---

## Refactoring Tool Patterns

### Rename Symbol with Confidence

1. Search for the old symbol across the codebase.
2. Check imports, re-exports, and string-based references (configs, tests).
3. Use an IDE or `sed`/`rg` carefully.
4. Run the test suite.

### Extract Common Script Helpers

Create a `scripts/lib.sh` file sourced by multiple scripts:

```bash
# scripts/lib.sh
set -euo pipefail

log_info() { printf '[INFO] %s\n' "$*"; }
log_error() { printf '[ERROR] %s\n' "$*" >&2; }
```

```bash
source "$(dirname "$0")/lib.sh"
log_info "Starting..."
```

### Convert Ad-Hoc Commands to Scripts

If you find yourself running a sequence of commands repeatedly, wrap it in a script or a `just` task and commit it.
