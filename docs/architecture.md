# Architecture

Acrux is a local-first memory and learning daemon for coding agents. It records what
happens in every session, consolidates those traces into durable knowledge, and injects
the relevant pieces back into future sessions. Everything is persisted under
`~/.acrux/` on the local machine.

## High-level view

```text
        coding agents (Kimi Code, Claude, Cursor, Codex, Gemini)
                     │  MCP (stdio / HTTP)
                     ▼
┌───────────────────────────────────────────────────────────────┐
│                         acrux daemon                          │
│                                                               │
│  ┌────────────┐   ┌──────────────────┐   ┌────────────────┐   │
│  │ MCP server │   │ Reflection engine │   │ FastAPI server │   │
│  │ (tools)    │   │ (facts + skills)  │   │ (HTTP/WS API)  │   │
│  └─────┬──────┘   └────────┬─────────┘   └───────┬────────┘   │
│        │                   │                     │            │
│        └───────────────────┼─────────────────────┘            │
│                            ▼                                  │
│                 three-tier memory stores                      │
│     episodic (SQLite) · semantic (SQLite + vector index)      │
│     procedural (SQLite)                                       │
└───────────────────────────────────────────────────────────────┘
                     │ spawn / control
                     ▼
            Acrux.app (native Swift UI)
```

The unified daemon (`acrux daemon`) runs the MCP server, scheduled reflection, and the
FastAPI app server in a single process. `acrux start` runs just the stdio MCP server,
which is how most agents connect.

## Three-tier memory

| Tier | Store | Contents | Lifetime |
|------|-------|----------|----------|
| Episodic | `episodes.db` | Raw task traces: "what happened" | Pruned after `retention.episodes_days` |
| Semantic | `facts.db` + vector index | Validated facts: "what is true" | Long-term |
| Procedural | `skills.db` | Verified skills: "how to do it" | Long-term |

Data is partitioned per project, plus a `global` scope:

```text
~/.acrux/data/
├── global/
│   ├── episodes.db
│   ├── facts.db
│   ├── skills.db
│   └── embeddings/
└── <project>/          # same structure, project-scoped
```

- **Episodes** are the largest data and the only tier that is pruned automatically.
- **Facts** and **skills** are small and kept long-term.
- The **semantic store** uses a `sqlite-vec` vector index for incremental
  inserts/deletes, falling back to hnswlib when `sqlite-vec` is unavailable.

## Reflection: the learning loop

Reflection is the self-training step that converts episodes into knowledge:

1. **Read** recent uncompacted episodes (batched, profile-aware).
2. **Extract** candidate facts and skills with an LLM (Ollama locally, Kimi online, or
   `none` to disable). Prompts request structured JSON; invalid outputs are rejected
   instead of polluting memory.
3. **Gate** new skills through a review queue (`pending_skills` table). Skills are
   validated against real episode IDs before entering the queue.
4. **Verify** with `SkillVerifier` — structure, evidence episodes, outcome positivity,
   duplicates, placeholders. Passing skills are marked `verified=True` and promoted.
5. **Compact** — episodes are marked compacted only when reflection produced at least
   one validated fact or skill.

Reflection runs on a schedule inside the daemon, on demand via `acrux reflect`, or from
an agent through the `acrux_reflect` MCP tool.

## Interfaces

- **CLI** (`acrux`, click) — init, status, config, models, reflection, pruning, skill
  export/import, review queue, benchmarks, self-healing, registry, MCP installer.
- **MCP server** — tools for agents: `acrux_remember_session`, `acrux_recall`,
  `acrux_context`, `acrux_remember_fact`, `acrux_get_skills`, `acrux_user_correction`,
  `acrux_reflect`, `acrux_record_outcome`, and more. stdio or HTTP transport.
- **HTTP API** (FastAPI) — status, recall, context, skills, tests, dependencies,
  reviews, and reflection endpoints. Requires `Authorization: Bearer <token>` or
  `X-Acrux-Token`; the token is generated at init and stored in
  `~/.acrux/config.yaml`. WebSocket chat is token-gated too.
- **Python SDK** (`acrux.sdk.AcruxClient`) — reads the token from the config
  automatically and covers the main API surface.

## Automatic capture

Acrux does not depend on agents remembering to log:

- `acrux wrap <command>` runs any command and records it as an episode with outcome and
  git context.
- A watcher (`kimi_watcher`) monitors agent session transcripts and records episodes
  automatically after a period of inactivity.
- `acrux ingest-code <path>` parses Python AST (modules, classes, functions,
  docstrings, import edges) into facts and dependency records.

## Resource profiles

Profiles bound RAM, storage, and model choices so Acrux can run alongside other
workloads, from 4 GB servers (`minimal`, no local LLM) to workstations (`workstation`,
full vector embeddings and local reflection). See the
[Operating Guide](OPERATING.md#resource-profiles) for the full table.

## Native macOS app

`swift_app/` contains a SwiftUI + SpriteKit app (no webview) that spawns the Python
backend as a child process and talks to it over HTTP/WebSocket: task chat with tool
approval, past chats, daemon control, and a live view of what the memory knows.

## Design rules

- **Local-first** — no data leaves the machine unless an online reflection provider is
  explicitly configured.
- **Nothing learned without validation** — structured outputs, review queues, and
  verification stand between raw episodes and long-term knowledge.
- **Agent-agnostic** — any MCP-capable agent can use it; prompts and captured episodes
  avoid agent-specific assumptions.
