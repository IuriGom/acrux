# Acrux

**Acrux** is a local-first memory and learning daemon for coding agents. It captures what
happened in every session, reflects on it to extract durable facts and skills, and injects
the relevant ones back into future sessions — all on your own machine.

It is **not** a RAG wrapper: it learns from every session and keeps the knowledge on disk,
so memory survives even when the agent compacts or resets its own context.

## Documentation

- [Quickstart](quickstart.md) — install, initialize, and run Acrux in minutes.
- [Architecture](architecture.md) — how the system is put together: memory tiers,
  reflection, daemon, and integrations.
- [Operating Guide](OPERATING.md) — day-to-day operation: profiles, commands, models,
  storage, retention, and troubleshooting.
- [Installation Plan](installation-plan.md) — the one-line installer design for new machines.
- [System Prompt Plan](system_prompt_plan.md) — the agent system prompt and the
  web-research tool policy, plus the feature log applied on top of it.

## Key properties

- **Local-first** — everything lives under `~/.acrux/`; nothing leaves the machine unless
  you configure an online reflection provider.
- **Three-tier memory** — episodic (what happened), semantic (what is true), and
  procedural (how to do it), with a vector index for semantic recall.
- **Self-training** — a reflection engine consolidates raw episodes into validated facts
  and skills, gated by a review queue.
- **Agent-agnostic** — works with Kimi Code, Claude, Cursor, Codex, and Gemini through MCP,
  plus a Python SDK and an HTTP API.

## Building this site

The documentation is built with [MkDocs](https://www.mkdocs.org/):

```bash
pip install mkdocs
mkdocs serve   # live preview at http://127.0.0.1:8000
mkdocs build   # static site in site/
```
