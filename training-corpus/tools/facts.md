# Tools: Developer Tools, CLI, Git, Docker, and Build Systems

This reference covers the essential facts, commands, concepts, and standard workflows for the everyday tools an AI coding assistant needs to recall when helping with software engineering tasks: Git, the Unix shell, Docker, package managers, build systems, and related CLI workflows.

---

## Git Fundamentals

### What Git Is

Git is a distributed version control system (DVCS). Every working copy is a full repository with complete history, enabling offline work, cheap branching, and flexible collaboration models. Git stores data as snapshots of a mini filesystem rather than deltas.

Core concepts:

- **Repository**: A directory containing the `.git` metadata store and a working tree.
- **Working tree**: The checked-out files you edit.
- **Index / staging area**: A place where changes are gathered before being committed.
- **Commit**: A snapshot of the project at a point in time, identified by a SHA-1 hash.
- **Branch**: A movable pointer to a commit.
- **HEAD**: A pointer to the current branch (or commit).
- **Remote**: A reference to another repository (commonly `origin`).
- **Ref**: A name that points to a commit (branches, tags, `HEAD`, remotes).

### First-Time Setup

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
git config --global core.editor "vim"   # or "code --wait", "nano", etc.
```

Configuration files:

- `--system`: `/etc/gitconfig`
- `--global`: `~/.gitconfig` or `~/.config/git/config`
- `--local`: `.git/config`

Useful settings:

```bash
git config --global color.ui auto
git config --global push.default simple
git config --global pull.rebase false   # or true / "merges" for --rebase=merges
git config --global fetch.prune true
git config --global rebase.autoStash true
git config --global alias.lg "log --oneline --graph --decorate --all"
```

### Creating and Cloning Repositories

```bash
git init my-project
cd my-project
git init   # inside existing directory

git clone https://github.com/user/repo.git
git clone git@github.com:user/repo.git
git clone --depth 1 https://github.com/user/repo.git   # shallow clone
git clone --branch feature --single-branch https://github.com/user/repo.git
```

### Recording Changes

States of a file:

1. **Untracked**: not in the index.
2. **Modified**: changed but not staged.
3. **Staged**: added to the index, ready to be committed.
4. **Committed**: stored in the local repository.

```bash
git status                    # see current state
git status -sb                # short branch-focused status

git add filename              # stage specific file
git add -p                    # stage interactively (hunks)
git add -A                    # stage all changes (new, modified, deleted)
git add -u                    # stage modified and deleted tracked files

git commit -m "message"       # commit staged changes
git commit -am "message"      # stage tracked files and commit (skips new files)
git commit --amend            # modify the last commit (use with caution if pushed)

git rm file                   # delete and stage
git mv old new                # rename and stage
git restore file              # discard unstaged changes in a file
git restore --staged file     # unstage a file
```

### Viewing History and Diffs

```bash
git log
git log --oneline -20
git log --graph --oneline --all --decorate
git log --stat                # show changed files and stats
git log -p                    # show patches
git log --author="Alice" --since="2 weeks ago"

git diff                      # unstaged changes vs index
git diff --staged             # staged changes vs HEAD
git diff HEAD~3 HEAD          # changes between commits
git diff branch-a branch-b -- path/to/file
git show HEAD                 # show commit details and patch
```

### Branching and Merging

```bash
git branch                    # list local branches
git branch -a                 # list all branches (including remotes)
git branch -vv                # show tracking branches

git switch feature            # switch to existing branch
git switch -c feature         # create and switch to new branch
git checkout -b feature       # older equivalent

git merge feature             # merge feature into current branch
git merge --no-ff feature     # always create a merge commit
git merge --ff-only feature   # only merge if fast-forward is possible

git branch -d feature         # delete merged branch
git branch -D feature         # force delete
```

### Rebasing

Rebase replays commits from one base onto another, producing a linear history.

```bash
git switch feature
git rebase main               # replay feature commits on top of main

git rebase -i HEAD~5          # interactive rebase of last 5 commits
# Commands in interactive rebase:
# p, pick = use commit
# r, reword = use commit, edit message
# e, edit = use commit, stop for amending
# s, squash = meld into previous commit
# f, fixup = like squash but discard message
# d, drop = remove commit
```

Golden rule: **do not rebase commits that have been pushed to a shared branch** unless everyone agrees.

### Stashing

```bash
git stash                     # stash unstaged and staged changes
git stash push -m "WIP on feature X"
git stash list
git stash pop                 # apply latest stash and remove it
git stash apply stash@{1}     # apply specific stash without removing
git stash drop stash@{1}      # delete specific stash
git stash clear               # delete all stashes
```

### Remotes and Synchronization

```bash
git remote -v                 # list remotes
git remote add origin <url>
git remote rename old new
git remote remove origin

git fetch origin              # download refs and objects
git pull origin main          # fetch + merge
git pull --rebase origin main # fetch + rebase
git push origin main
git push -u origin feature    # push and set upstream

git push origin --delete feature   # delete remote branch
git fetch origin --prune      # remove remote-tracking branches that no longer exist
```

### Undoing Changes

| Goal | Command |
|------|---------|
| Unstage a file | `git restore --staged <file>` |
| Discard unstaged changes | `git restore <file>` |
| Amend last commit | `git commit --amend` |
| Reset to a commit (keep changes staged) | `git reset --soft HEAD~1` |
| Reset to a commit (keep changes unstaged) | `git reset HEAD~1` |
| Reset to a commit (discard changes) | `git reset --hard HEAD~1` |
| Revert a commit (create inverse commit) | `git revert <commit>` |

`git reset --hard` is destructive. Use `git reflog` to recover lost commits.

### Tagging

```bash
git tag v1.0.0
git tag -a v1.0.0 -m "Release 1.0.0"
git tag -s v1.0.0 -m "Signed release"
git push origin v1.0.0
git push origin --tags
```

### Cherry-Picking

```bash
git cherry-pick <commit>      # apply a single commit onto current branch
git cherry-pick -x <commit>   # include original commit reference in message
git cherry-pick --abort       # abort in-progress cherry-pick
```

### Submodules

```bash
git submodule add https://github.com/user/lib.git libs/lib
git submodule update --init --recursive
git submodule update --remote   # update submodule to latest remote commit
```

### Git Workflows

- **Centralized**: Everyone pushes to a single shared branch (e.g., `main`).
- **Feature Branch**: Each feature/fix gets its own branch; reviewed via PR before merging to `main`.
- **Gitflow**: Uses `main`, `develop`, `feature/*`, `release/*`, `hotfix/*` branches.
- **Forking**: Contributors fork the repo, push to their own fork, and open pull requests.
- **Trunk-based**: Small, short-lived branches merged frequently into `main`.

### Useful Aliases

```bash
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.lg "log --color --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit"
```

---

## Unix Shell Fundamentals

### POSIX vs Bash

- `/bin/sh` is the POSIX shell. Scripts written for `sh` are portable across Unix-like systems.
- `bash` (Bourne-Again shell) adds arrays, associative arrays, `[[ ]]`, process substitution, and more.
- For internal/dev scripts, Bash is usually fine. For system scripts or shebang utilities, consider POSIX `sh` for portability.

### Shebang Lines

```bash
#!/usr/bin/env bash
#!/bin/bash
#!/bin/sh   # POSIX-only
```

`#!/usr/bin/env bash` is more portable across different install locations (macOS uses `/bin/bash` but Homebrew may install a newer version at `/opt/homebrew/bin/bash`).

### Strict Mode

Reliable Bash scripts commonly start with:

```bash
set -euo pipefail
IFS=$'\n\t'
```

- `set -e` / `set -o errexit`: exit immediately on nonzero command status.
- `set -u` / `set -o nounset`: treat unset variables as errors.
- `set -o pipefail`: pipeline fails if any command fails, not just the last.
- `IFS=$'\n\t'`: restrict word splitting to newlines and tabs only.

Optional debug tracing:

```bash
if [[ "${TRACE-0}" == "1" ]]; then
    set -o xtrace
fi
```

### Variables and Quoting

```bash
name="Alice"
echo "Hello, $name"
echo "Hello, ${name}"      # safer with braces

# Always quote variable expansions
cp "$source" "$dest"

# Default values
output_dir="${OUTPUT_DIR:-/tmp}"
required="${API_KEY:?API_KEY must be set}"

# String manipulation (parameter expansion)
file="document.txt"
echo "${file%.txt}"         # document
echo "${file##*.}"          # txt
echo "${file#*.}"           # txt
echo "${file##doc}"         # ument.txt
```

### Arrays

```bash
fruits=("apple" "banana" "cherry")
echo "${fruits[0]}"         # apple
echo "${fruits[@]}"         # all elements (quoted: preserves items with spaces)
echo "${#fruits[@]}"        # length
for fruit in "${fruits[@]}"; do
    echo "$fruit"
done

# Associative arrays (bash 4+)
declare -A user
user[name]="Alice"
user[role]="admin"
echo "${user[name]}"
```

### Conditionals

Use `[[ ]]` in Bash; it is safer than `[ ]` for string comparisons and handles empty values better.

```bash
if [[ -f "file.txt" ]]; then
    echo "file exists"
elif [[ -d "dir" ]]; then
    echo "directory exists"
else
    echo "neither"
fi

# Numeric comparisons
if (( count > 0 )); then
    echo "positive"
fi

# String checks
if [[ -z "$name" ]]; then        # empty
    echo "empty"
fi
if [[ -n "$name" ]]; then        # non-empty
    echo "non-empty"
fi
if [[ "$name" == "Alice" ]]; then
    echo "Alice"
fi
```

Common file test operators:

- `-e`: exists
- `-f`: regular file
- `-d`: directory
- `-r`: readable
- `-w`: writable
- `-x`: executable
- `-s`: nonzero size
- `-h` / `-L`: symbolic link

### Loops

```bash
for i in 1 2 3; do
    echo "$i"
done

for file in *.txt; do
    echo "$file"
done

for i in {1..5}; do
    echo "$i"
done

while [[ "$#" -gt 0 ]]; do
    echo "$1"
    shift
done

# Reading files line by line
while IFS= read -r line; do
    echo "$line"
done < "input.txt"
```

### Functions

```bash
say_hello() {
    local name="${1:-World}"
    echo "Hello, $name"
}

say_hello "Alice"
```

- Always use `local` for variables inside functions.
- Use `$1`, `$2`, etc. for positional parameters.
- `$@` expands to all arguments; `"$@"` preserves quoting.
- `$#` is the argument count.

### Command Substitution

```bash
# Modern form (preferred)
today=$(date +%Y-%m-%d)

# Legacy form (avoid for nesting)
today=`date +%Y-%m-%d`
```

### Process Substitution

```bash
diff <(sort file1.txt) <(sort file2.txt)
```

### Redirection

```bash
cmd > output.txt       # stdout to file (overwrite)
cmd >> output.txt      # stdout to file (append)
cmd 2> errors.txt      # stderr to file
cmd &> output.txt     # stdout and stderr to file (bash)
cmd > /dev/null 2>&1  # redirect stderr to stdout
cmd < input.txt       # read stdin from file
```

### Traps and Cleanup

```bash
cleanup() {
    rm -f "$tmpfile"
}
trap cleanup EXIT

tmpfile=$(mktemp)
```

### Finding Files and Text

```bash
find . -name "*.py" -type f
find . -type f -mtime -7
find . -name "*.log" -delete
find . -type f -exec grep -l "TODO" {} +

grep -R "TODO" .
grep -i "todo" .              # case-insensitive
rg "TODO" .                   # ripgrep, faster by default
```

### Text Processing

```bash
# sed: stream editor
sed 's/foo/bar/g' file.txt
sed -i.bak 's/foo/bar/g' file.txt   # in-place with backup

# awk: pattern scanning and processing
awk '{print $1}' file.txt
awk -F: '{print $1, $3}' /etc/passwd
awk '$3 > 100 {print $0}' file.txt

# jq: JSON processor
cat data.json | jq '.users[0].name'
jq '.items[] | select(.price > 10)' data.json

# yq: YAML processor (multiple implementations exist)
yq '.services.app.image' docker-compose.yml
```

### Process Management

```bash
ps aux
pgrep -f myprocess
kill -15 PID              # SIGTERM (graceful)
kill -9 PID               # SIGKILL (force)
top / htop                # interactive process viewer
lsof -i :8080             # find process using port 8080
```

### Networking Utilities

```bash
curl -fsSL https://example.com/api
wget https://example.com/file.zip
ping -c 4 example.com
ss -tlnp                  # show listening TCP sockets and processes
netstat -tlnp             # older alternative
nc -zv example.com 443    # test port connectivity
dig example.com
```

---

## Docker Fundamentals

### What Docker Is

Docker packages applications into lightweight, portable containers that share the host OS kernel but run in isolated user spaces. A container is a runtime instance of an image; an image is a layered, read-only template.

Key terms:

- **Image**: Read-only template with app code, libraries, dependencies, and config.
- **Container**: A runnable instance of an image.
- **Dockerfile**: A script of instructions to build an image.
- **Layer**: Each Dockerfile instruction creates a layer; layers are cached and shared.
- **Registry**: A service that stores images (Docker Hub, GHCR, ECR, ACR, GCR).
- **Volume**: Persistent storage managed by Docker.
- **Network**: Isolated communication between containers.

### Basic Docker Commands

```bash
# Images
docker build -t myapp:1.0 .
docker build -f Dockerfile.prod -t myapp:prod .
docker images
docker rmi myapp:1.0

docker pull ubuntu:24.04
docker push registry.example.com/myapp:1.0

# Containers
docker run -d -p 8080:80 --name web nginx
docker run -it --rm ubuntu:24.04 bash
docker ps
docker ps -a
docker start web
docker stop web
docker restart web
docker rm web
docker exec -it web bash

docker logs web
docker logs -f web
docker logs --tail 100 web

docker cp web:/etc/nginx/nginx.conf ./nginx.conf
docker cp ./local.file web:/app/local.file

# Cleanup
docker system prune -f
docker volume prune -f
```

### Dockerfile Instructions

```dockerfile
# syntax=docker/dockerfile:1
FROM node:20-alpine
LABEL maintainer="team@example.com"

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 3000

USER node

CMD ["node", "server.js"]
```

Common instructions:

- `FROM`: base image.
- `RUN`: execute command during build.
- `CMD`: default command for the container.
- `ENTRYPOINT`: configure a container that runs as an executable.
- `COPY`: copy files from build context into image.
- `ADD`: like COPY but supports URLs and auto-extraction of tar archives.
- `WORKDIR`: set working directory (creates it if needed).
- `ENV`: set environment variable.
- `ARG`: build-time variable.
- `EXPOSE`: document listening ports.
- `VOLUME`: create a mount point.
- `USER`: run subsequent commands as user.
- `LABEL`: metadata.
- `HEALTHCHECK`: define command to check container health.

### Multi-Stage Builds

Multi-stage builds reduce final image size by separating build-time dependencies from runtime artifacts.

```dockerfile
# syntax=docker/dockerfile:1
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Docker Compose

`docker-compose.yml` (or `compose.yaml`) defines multi-container applications.

```yaml
services:
  web:
    build: .
    ports:
      - "8080:80"
    environment:
      - NODE_ENV=production
    depends_on:
      - db
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: appdb
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

```bash
docker compose up -d
docker compose down
docker compose logs -f
docker compose exec web bash
docker compose build
docker compose pull
```

### Volumes vs Bind Mounts

- **Volume**: Managed by Docker (`docker volume create ...`), stored in Docker's storage area, better for persistent data.
- **Bind mount**: Maps a host path into the container, useful for development when you want live code reloads.
- **tmpfs mount**: Stored in host memory only, useful for sensitive temporary data.

```bash
# Volume
docker run -v mydata:/data myimage

# Bind mount
docker run -v $(pwd):/app myimage

# tmpfs mount
docker run --tmpfs /tmp:noexec,nosuid,size=100m myimage
```

### Docker Networking

```bash
docker network ls
docker network create mynet
docker run -d --network mynet --name app myimage
docker run -d --network mynet --name db postgres
```

Default networks:

- `bridge`: default private network for standalone containers.
- `host`: use host networking (Linux only).
- `none`: no networking.

In Compose, services on the same network can resolve each other by service name.

### Container Best Practices Summary

- Use official, minimal base images (e.g., `alpine`, `slim`, `distroless`).
- Pin base image tags and ideally digests for reproducibility.
- Run as non-root user.
- Keep images small: multi-stage builds, avoid build tools in final image.
- Use `.dockerignore` to exclude unnecessary files.
- Prefer `COPY` over `ADD` unless you need URL/tar extraction.
- Make containers ephemeral and stateless; persist data in volumes.
- One concern per container.
- Never bake secrets into images; use runtime secrets or environment variables from orchestrators.

---

## Package Managers

### npm / yarn / pnpm (Node.js)

`package.json` metadata:

```json
{
  "name": "my-app",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest"
  },
  "dependencies": {
    "express": "^4.19.0"
  },
  "devDependencies": {
    "vitest": "^1.0.0"
  }
}
```

Version ranges:

- `1.2.3`: exact
- `^1.2.3`: compatible with minor/patch (>=1.2.3 <2.0.0)
- `~1.2.3`: approximately equivalent (>=1.2.3 <1.3.0)
- `>=1.2.3`: at least this version
- `*`: any version

Commands:

```bash
npm install                 # install dependencies from package-lock.json
npm install express         # add runtime dependency
npm install --save-dev eslint
npm install -g typescript
npm update
npm run build
npm test
npm audit
npm audit fix

# pnpm
pnpm install
pnpm add express
pnpm add -D eslint
pnpm run build

# yarn
yarn install
yarn add express
yarn add -D eslint
yarn build
```

Lockfiles:

- `package-lock.json` (npm)
- `yarn.lock` (yarn)
- `pnpm-lock.yaml` (pnpm)

Always commit lockfiles to version control for reproducible installs.

### Python Packaging

Modern Python projects use `pyproject.toml` (PEP 517/518).

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "0.1.0"
description = "A sample package"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.31",
]

[project.optional-dependencies]
dev = ["pytest", "ruff"]

[dependency-groups]
dev = ["pytest", "ruff"]
```

Tools:

- **pip**: standard installer; works with `requirements.txt` and `pyproject.toml`.
- **venv / virtualenv**: create isolated Python environments.
- **Poetry**: dependency resolution, lockfile, packaging, publishing.
- **uv**: extremely fast Python package and project manager (Astral), can replace pip, venv, Poetry, pyenv, pipx, pip-tools.
- **PDM**: PEP 582/PEP 621 compliant package manager.
- **Hatch**: extensible build backend and project manager.

Commands:

```bash
# pip + venv
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .

# Poetry
poetry install
poetry add requests
poetry add --group dev pytest
poetry run pytest
poetry build
poetry publish

# uv
uv init my-project
uv add requests
uv add --dev pytest
uv sync
uv run pytest
uv build
uv publish
uv venv
```

### Rust: Cargo

```toml
[package]
name = "my-crate"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0", features = ["derive"] }

[dev-dependencies]
tokio-test = "0.4"
```

```bash
cargo new my-crate
cargo build
cargo run
cargo test
cargo clippy
cargo fmt
cargo add serde
cargo update
```

Cargo.lock is committed for binaries, usually ignored for libraries.

### Go: Modules

```bash
go mod init example.com/mymodule
go get github.com/gin-gonic/gin
go mod tidy
go build ./...
go test ./...
```

- `go.mod`: module definition and direct dependency minimum versions.
- `go.sum`: cryptographic checksums for reproducibility; commit it.

### Java / JVM: Maven and Gradle

Maven `pom.xml` coordinates:

```xml
<dependency>
    <groupId>org.apache.commons</groupId>
    <artifactId>commons-lang3</artifactId>
    <version>3.14.0</version>
</dependency>
```

```bash
mvn clean package
mvn test
mvn dependency:tree
```

Gradle uses a DSL in `build.gradle` or `build.gradle.kts`:

```kotlin
plugins {
    java
}

dependencies {
    implementation("org.apache.commons:commons-lang3:3.14.0")
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.0")
}
```

```bash
./gradlew build
./gradlew test
```

### C/C++: vcpkg / Conan / CMake FetchContent

- **vcpkg**: Microsoft cross-platform C++ package manager.
- **Conan**: C/C++ package manager with binary artifacts.
- **CMake FetchContent**: download dependencies at configure time.

```cmake
include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
)
FetchContent_MakeAvailable(googletest)
```

---

## Build Systems

### Make / GNU Make

Makefile structure:

```makefile
CC := gcc
CFLAGS := -Wall -Wextra -O2
TARGET := app
SRCS := $(wildcard src/*.c)
OBJS := $(SRCS:.c=.o)

.PHONY: all clean test

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f $(TARGET) $(OBJS)

test: $(TARGET)
	./$(TARGET) --test
```

Automatic variables:

- `$@`: target name
- `$<`: first prerequisite
- `$^`: all prerequisites
- `$?`: prerequisites newer than target

### CMake

CMake generates native build files (Makefiles, Ninja, Visual Studio projects, Xcode projects).

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyProject VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(myapp src/main.cpp)

target_link_libraries(myapp PRIVATE mylib)

enable_testing()
add_subdirectory(tests)
```

Modern CMake best practices:

- Treat targets as objects; use `target_include_directories`, `target_compile_options`, `target_link_libraries`.
- Prefer `PRIVATE`/`PUBLIC`/`INTERFACE` visibility keywords.
- Avoid global variables like `include_directories`.
- Use `find_package` for external dependencies.
- Use presets (`CMakePresets.json`) for reproducible configure/build/test workflows.

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
cmake --build build --target test
```

### Ninja

Ninja is a fast, low-level build system often used as CMake's generator.

```bash
cmake -S . -B build -G Ninja
cmake --build build
```

### Bazel

Bazel is a build/test tool optimized for large monorepos and reproducible builds.

```python
# BUILD
cc_binary(
    name = "hello",
    srcs = ["hello.cc"],
)
```

```bash
bazel build //:hello
bazel test //...
bazel run //:hello
```

### Meson

Meson is a fast, user-friendly build system.

```meson
project('myapp', 'cpp')
executable('myapp', 'main.cpp')
```

```bash
meson setup build
meson compile -C build
meson test -C build
```

### Task Runners and Script Runners

- **just**: Handy command runner with a `Justfile`.
- **Taskfile**: YAML-based task runner (`Taskfile.yml`).
- **npm scripts**: built into Node.js projects.
- **Poetry / uv scripts**: run project commands in virtualenvs.
- **tox / nox**: test automation across Python environments.

Example `Justfile`:

```just
set dotenv-load

build:
    cargo build --release

test:
    cargo test

lint:
    cargo clippy
```

---

## CLI Workflows and Development Utilities

### GitHub CLI (`gh`)

```bash
gh auth login
gh repo create my-project --public --source=. --remote=origin --push
gh pr create --title "Add feature" --body "Description"
gh pr checkout 123
gh pr merge 123 --squash
gh issue create --title "Bug" --body "Details"
gh run list
gh run watch 123456789
gh release create v1.0.0 --generate-notes
```

### `jq` and JSON Processing

```bash
curl -s https://api.github.com/users/octocat | jq '.login, .id, .public_repos'
jq '.[] | {name: .name, status: .status}' data.json
jq 'map(select(.age >= 18))' users.json
```

### `curl` and HTTP Requests

```bash
curl -X GET https://api.example.com/items
curl -X POST https://api.example.com/items \
  -H "Content-Type: application/json" \
  -d '{"name":"foo"}'
curl -fsSL https://example.com/install.sh | bash   # -f fail, -s silent, -S show errors, -L follow redirects
curl -o file.zip -L https://example.com/file.zip
```

### `ssh` and Keys

```bash
ssh-keygen -t ed25519 -C "you@example.com"
ssh-keygen -t rsa -b 4096 -C "you@example.com"
ssh-copy-id user@host
ssh -i ~/.ssh/key user@host
```

Config file `~/.ssh/config`:

```
Host myserver
    HostName 203.0.113.10
    User deploy
    IdentityFile ~/.ssh/id_ed25519
    Port 2222
```

### `tmux` / `screen`

```bash
tmux new -s session
tmux attach -t session
tmux ls
tmux kill-session -t session
```

### `fzf`

Fuzzy finder for shells:

```bash
# Find files and open in editor
vim $(fzf)

# Search command history
history | fzf
```

### `ripgrep` (`rg`)

```bash
rg "TODO" src/
rg -t py "class \w+" src/
rg -l "deprecated" src/
```

### `fd`

User-friendly alternative to `find`:

```bash
fd "\.py$" src/
fd -e py -x black {}
```

### `htop` / `btop`

Interactive process viewers for inspecting CPU, memory, and process state.

### `lnav`

Log file navigator for viewing and searching logs.

### `ncdu`

Disk usage analyzer.

---

## Environment and Secret Management

### Environment Variables

```bash
export API_KEY="value"
unset API_KEY
env | grep API
printenv API_KEY
```

In scripts, prefer reading from environment variables rather than hardcoding secrets. Validate that required variables are set:

```bash
: "${API_KEY:?API_KEY must be set}"
```

### `.env` Files

```bash
# .env
DATABASE_URL=postgres://user:pass@localhost/db
DEBUG=true
```

Load in shell:

```bash
set -a; source .env; set +a
```

Many tools (Docker Compose, Python `python-dotenv`, Node `dotenv`) load `.env` automatically.

### Secret Managers

- **Docker secrets**: for Swarm; mounts secrets as files under `/run/secrets/`.
- **Kubernetes Secrets**: base64-encoded secrets stored in etcd.
- **Cloud secret managers**: AWS Secrets Manager, Azure Key Vault, GCP Secret Manager, HashiCorp Vault.

### SSH Agent

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
ssh-add -l
```

---

## Continuous Integration / Deployment Basics

### Common CI Concepts

- **Pipeline**: sequence of stages/jobs.
- **Job**: a unit of work (e.g., run tests).
- **Step**: a command within a job.
- **Artifact**: files produced by a job, passed to downstream jobs.
- **Cache**: reused files between runs to speed up builds.
- **Matrix/Strategy**: run the same job with different configurations.

### GitHub Actions Example

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: pytest
```

### GitLab CI Example

```yaml
stages:
  - test
  - build
  - deploy

test:
  stage: test
  image: python:3.12
  script:
    - pip install -r requirements.txt
    - pytest
```

### Caching Strategies

- Cache dependency directories (`.npm`, `target/`, `.venv`, `~/.cache/pip`).
- Use lockfiles to make caches valid across runs.
- Cache build outputs that are expensive to reproduce.
- Avoid caching secrets or large files that change often.

---

## Container Orchestration (Brief)

### Kubernetes Concepts

- **Pod**: smallest deployable unit; one or more containers.
- **Deployment**: manages ReplicaSets and rolling updates.
- **Service**: exposes pods via ClusterIP, NodePort, LoadBalancer, or ExternalName.
- **ConfigMap / Secret**: inject configuration and secrets.
- **Ingress**: HTTP/HTTPS routing into the cluster.
- **Namespace**: isolates resources.

```bash
kubectl get pods
kubectl get deployments
kubectl apply -f manifest.yaml
kubectl logs deployment/myapp
kubectl exec -it pod/myapp-xxx -- /bin/sh
kubectl port-forward svc/myapp 8080:80
```

### Docker Swarm

Simpler built-in orchestration for Docker:

```bash
docker swarm init
docker stack deploy -c docker-compose.yml myapp
docker service ls
```

---

## Linting, Formatting, and Static Analysis

### Shell

- **ShellCheck**: lints shell scripts for bugs and portability issues.
- **shfmt**: formats shell scripts.

```bash
shellcheck script.sh
shfmt -w script.sh
```

### Python

- **Ruff**: extremely fast linter and formatter.
- **mypy**: static type checker.
- **Bandit**: security linter.
- **pip-audit**: audits dependencies for known vulnerabilities.

```bash
ruff check .
ruff format .
mypy src/
bandit -r src/
pip-audit
```

### JavaScript / TypeScript

- **ESLint**: linter.
- **Prettier**: formatter.
- **TypeScript compiler**: type checking.

```bash
eslint src/
prettier --write src/
tsc --noEmit
```

### Rust

```bash
cargo clippy
cargo fmt
cargo check
```

### Go

```bash
go fmt ./...
go vet ./...
golangci-lint run
```

---

## Documentation and Help

### Reading Manuals

```bash
man git-commit
man bash
man docker-build
```

### Built-In Help

```bash
git commit --help
git help commit
curl --help
curl --manual | less
```

### TLDR Pages

Concise community-maintained examples:

```bash
tldr docker
tldr tar
```

### Cheat Sheets

- `git-scm.com/cheat-sheet`
- Docker docs building best practices
- GNU Make manual
- POSIX shell specification
