# Acrux

Local-first memory and learning layer for coding agents.

Acrux gives your coding agent a durable memory that survives the session boundary. It captures episodes, consolidates them into facts and skills, verifies them, and injects the relevant ones back into future sessions — all on your own machine.

## Install

One-liner:

```bash
curl -fsSL https://acrux.dev/install.sh | sh
```

From source:

```bash
git clone https://github.com/<org>/acrux.git
cd acrux
bash install/install.sh
```

The installer creates an isolated venv, generates a config with a fresh API token, installs the daemon as a user service, and optionally wires Kimi Code, Claude Code, Cursor, Codex, or Gemini via `acrux install-mcp`.

## Quickstart

```bash
acrux init --profile standard
acrux daemon --background --mcp http
acrux demo
```

## Features

- Three-tier memory: episodic, semantic, procedural
- Structured reflection with JSON validation and a review queue
- sqlite-vec vector index with incremental updates
- Automatic agent session capture for Kimi Code and Claude Code
- Skill verification with sandboxed execution and A/B checks
- Unified hybrid retrieval (FTS5 + vector + inheritance + token budget)
- Token-authenticated HTTP + MCP APIs
- Signed skill registry and benchmark suite
- Python SDK and multi-agent MCP installer

## Development

```bash
pip install -e '.[dev]'
pytest acrux/tests -v
```

## License

MIT
