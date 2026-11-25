# acrux

Local-first memory and learning layer for coding agents.

Acrux gives your coding agent a durable memory that survives the session boundary. It captures what your agent does, consolidates it into facts and skills, verifies them, and injects the relevant ones back into future sessions — all on your own machine.

[![CI](https://github.com/IuriGom/acrux/actions/workflows/ci.yml/badge.svg)](https://github.com/IuriGom/acrux/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Install

One-liner:

```sh
curl -fsSL https://acrux.dev/install.sh | sh
```

From source:

```sh
git clone https://github.com/IuriGom/acrux.git
cd acrux
bash install/install.sh
```

The installer creates an isolated venv, generates a config with a fresh API token, installs the daemon as a user service, and optionally wires Kimi Code, Claude Code, Cursor, Codex, or Gemini via `acrux install-mcp`.

## Quickstart

```sh
acrux init --profile standard
acrux daemon --background --mcp http
acrux demo
```

## How it works

Sessions flow through five stages:

1. **Capture** — watchers tail Kimi Code and Claude Code sessions and turn transcripts into episodes.
2. **Consolidate** — the reflection engine (Kimi or Ollama backend) distills episodes into facts and procedural skills, with JSON-validated output and a review queue.
3. **Verify** — candidate skills run in a sandbox with A/B checks; the registry signs accepted entries with ed25519.
4. **Retrieve** — hybrid search combines FTS5 full-text, sqlite-vec embeddings, project inheritance, and a token budget, so only what fits goes into context.
5. **Inject** — a local daemon serves memory over token-authenticated HTTP and MCP. Agents query it at session start and mid-session.

Everything is stored in local SQLite, with a mutation journal and undo across all tiers.

## Features

- Three-tier memory: episodic, semantic, procedural
- Structured reflection with JSON validation and a review queue
- sqlite-vec vector index with incremental updates
- Automatic agent session capture for Kimi Code and Claude Code
- Skill verification with sandboxed execution and A/B checks
- Signed (ed25519) skill registry and benchmark suite
- Unified hybrid retrieval (FTS5 + vector + inheritance + token budget)
- Token-authenticated HTTP + MCP APIs
- Python SDK and multi-agent MCP installer
- Optional macOS app (SwiftUI) in `swift_app/`

## Project layout

```
acrux/            core package
  memory/         episodic / semantic / procedural stores, graph, journal
  reflection/     consolidation engine (kimi / ollama backends)
  daemon.py       background service (HTTP + MCP)
  http_server.py  token-authenticated HTTP API
  mcp_server.py   MCP interface for agents
  retrieval.py    hybrid search (FTS5 + vector + inheritance)
  verify.py       skill verification + sandbox
  taskbench.py    benchmark harness
docs/             architecture, operating guide, spec
install/          installer / uninstaller / upgrade scripts
training-corpus/  facts / patterns / pitfalls corpus + ingest pipeline
swift_app/        macOS app (SwiftUI)
```

## Development

```sh
pip install -e '.[dev]'
pytest acrux/tests -v
```

## Docs

- [Architecture](docs/architecture.md)
- [Operating guide](docs/OPERATING.md)
- [Quickstart](docs/quickstart.md)
- [Changelog](CHANGES.md)

Full docs site: [acrux.dev](https://acrux.dev)

## License

[MIT](LICENSE)
