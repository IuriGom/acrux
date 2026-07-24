# Acrux Operating Guide

A local, self-training memory system for coding agents. It stores what happened, reflects on it to extract facts and skills, and recalls them when needed. It is **not** a RAG wrapper: it learns from every session and keeps the knowledge on disk.

This acrux is designed to be small enough to run alongside other workloads, including on low-end servers.

---

## What lives where

| Path | Purpose |
|------|---------|
| `~/.acrux/config.yaml` | Acrux configuration (profile, models, retention) |
| `~/.acrux/data/` | All persisted memories (episodes, facts, skills, embeddings) |
| `~/.acrux/logs/` | Logs from the acrux daemon and MCP server |
| `~/.kimi-code/mcp.json` | Kimi Code MCP client configuration |
| `~/acrux/acrux/` | Source code and virtual environment |

> **Important:** Kimi Code can compact or reset its own conversation context, but the data in `~/.acrux/data/` stays on disk. That is how memory survives across sessions.

---

## Quick start

```bash
# Make sure the virtual environment exists and the CLI is callable.
~/acrux/acrux/.venv/bin/acrux --help

# Initialize once (already done on this machine).
acrux init --profile workstation

# See current status.
acrux status --storage

# Switch reflection / embedding models.
acrux use-model qwen3:14b

# Edit ~/.acrux/config.yaml and set:
#   reflection.embedding_model: bge-m3

# Run reflection now to turn recent episodes into facts and skills.
acrux reflect --project <project-name>
```

To use the acrux from anywhere in your terminal, add the binary to your `PATH`:

```bash
export PATH="~/acrux/acrux/.venv/bin:$PATH"
```

You can put that line in `~/.zshrc` or `~/.bashrc` so it is always available.

---

## Resource profiles

Profiles control how much RAM, storage, and CPU the acrux tries to use. Pick one per machine.

| Profile | RAM target | Storage cap | Embeddings | Reflection provider | Best for |
|---------|-----------|-------------|------------|---------------------|----------|
| `minimal` | ~256 MB | 5 GB | None | none | 4 GB RAM servers, pure logging |
| `light` | ~512 MB | 15 GB | Optional (384-dim) | kimi (online) | 8 GB RAM servers |
| `standard` | ~1 GB | 50 GB | Vector (384-dim) | ollama | Dedicated acrux machine |
| `workstation` | ~2 GB | Unlimited | Vector (full) | ollama | This Mac |

Set a profile during init:

```bash
acrux init --profile light
```

Or edit `~/.acrux/config.yaml`:

```yaml
acrux:
  profile: light
```

### Suggested machine mapping

- **This machine (Mac, lots of RAM):** `workstation` with `qwen3:14b` + `bge-m3`. Runs offline because both models are local.
- **8 GB RAM servers:** `light` with `acrux use-model kimi` and a small embedding model only if you have disk space. Stays online for reflection.
- **4 GB RAM server:** `minimal` with `acrux use-model none`. It records episodes but does not reflect locally; you can copy the data to a stronger machine and reflect there.

---

## Command reference

All commands are subcommands of `acrux`.

### Core

```bash
acrux --help                      # Show top-level help
acrux init --profile <profile>    # Create ~/.acrux and pick a profile
acrux status                      # Show running state, provider, projects
acrux status --storage            # Also show disk and data usage
acrux config                      # Print the merged configuration
acrux doctor                      # Validate data integrity
```

### Reflection and learning

```bash
acrux models                      # List available Ollama models
acrux use-model qwen3:14b         # Use a local Ollama model for reflection
acrux use-model kimi              # Use Kimi (online) for reflection
acrux use-model none              # Disable local reflection

acrux reflect                     # Reflect across all projects
acrux reflect --project foo       # Reflect on one project only
acrux reflect --batch-size 5      # Smaller batches for weak hardware
```

Reflection reads recent `episodes`, extracts `facts` and `skills`, and writes them back to `~/.acrux/data/`. It is the "self-training" step.

### Memory tools (used by Kimi Code via MCP)

Kimi Code talks to the acrux through these MCP tools:

- `acrux_remember_session` — store a finished task.
- `acrux_recall` — search memories by meaning.
- `acrux_remember_fact` — store a single fact.
- `acrux_get_skills` — fetch procedural skills for a task.
- `acrux_user_correction` — record a high-priority correction.
- `acrux_reflect` — trigger reflection from inside a chat.

You do not call these by hand; Kimi calls them automatically when the MCP server is running.

### Maintenance

```bash
acrux logs                        # Tail recent logs
acrux prune                       # Remove episodes older than retention.episodes_days
acrux prune --older-than 90d      # Remove episodes older than 90 days
acrux export-skills > skills.yaml # Export verified skills
acrux import-skills skills.yaml   # Import skills
acrux reset                       # DESTROY all acrux data (ask for confirmation)
```

### Server modes

```bash
acrux start                       # Start the MCP server (stdio, used by Kimi)
acrux daemon                      # Run long-running daemon with scheduled reflection
acrux daemon --background         # Run daemon in the background
acrux daemon --mcp http --port 11436   # Run HTTP MCP server
acrux stop                        # Stop a background daemon
```

For Kimi Code integration, **stdio** transport is used. The daemon is only needed if you want scheduled reflection or an HTTP endpoint.

---

## Switching models

### Reflection model (the "thinking" LLM)

```bash
acrux use-model qwen3:14b         # Local Ollama, works offline, needs ~8.6 GB disk
acrux use-model kimi              # Online, no local RAM/disk cost
acrux use-model none              # No reflection; pure memory storage
```

You can also edit `~/.acrux/config.yaml`:

```yaml
reflection:
  provider: ollama
  model: qwen3:14b
  host: http://localhost:11434
```

### Embedding model (for semantic search)

Edit `~/.acrux/config.yaml` directly:

```yaml
reflection:
  embedding_model: bge-m3
```

Then run a reflection to test it:

```bash
acrux reflect --project test-server
```

Currently installed local embedding models:

- `bge-m3` (1.2 GB) — best general-purpose multilingual embeddings. **Recommended.**
- `nomic-embed-text:v1.5` (261 MB) — smaller, good if disk is tight.

For a weak server, `nomic-embed-text` is a reasonable fallback.

---

## Storage and retention

Everything is stored in `~/.acrux/data/`. The acrux does not send your data anywhere unless you configure an online reflection provider.

Control storage in `~/.acrux/config.yaml`:

```yaml
retention:
  episodes_days: 30        # Keep raw episodes for 30 days
  max_storage_gb: 10       # Hard cap; 0 means unlimited (or profile default)
```

- `episodes` are the largest and oldest data. Facts and skills are tiny.
- `acrux prune` removes old episodes without touching facts/skills.
- The profile default cap applies when `max_storage_gb` is `0`.

For your machines:

| Machine | Suggested profile | Suggested `max_storage_gb` |
|---------|-------------------|---------------------------|
| This Mac | `workstation` | `0` (unlimited, you have ~400 GB free) |
| 8 GB / 512 GB server | `light` or `standard` | `30` |
| 8 GB / 200 GB server | `light` | `15` |
| 4 GB / 180 GB server | `minimal` | `5` |

---

## Offline vs online operation

- **Offline:** Set `reflection.provider: ollama` and make sure the model is pulled. Reflection and recall both work without internet.
- **Online-only machines:** Use `acrux use-model kimi` so the acrux sends reflections to Kimi instead of running a local LLM.
- **No LLM at all:** Use `acrux use-model none`. The acrux still records episodes and facts manually; you can reflect later on a stronger machine by copying `~/.acrux/data/`.

---

## Kimi Code integration

Kimi Code connects to the acrux through MCP. The relevant part of `~/.kimi-code/mcp.json` looks like this:

```json
{
  "mcpServers": {
    "acrux": {
      "command": "~/acrux/acrux/.venv/bin/acrux",
      "args": ["start"]
    }
  }
}
```

When Kimi starts, it runs `acrux start`, which launches the stdio MCP server. Kimi then calls `acrux_remember_session`, `acrux_recall`, etc. as needed. Because the acrux writes to disk, memory survives even when Kimi compacts its own context.

---

## How the data is organized

```
~/.acrux/data/
├── global/
│   ├── episodes.db        # Raw task traces
│   ├── facts.db           # Extracted semantic facts
│   ├── skills.db          # Procedural skills
│   └── embeddings/        # Vector index for semantic search
└── <project>/             # Project-scoped memories (same structure)
```

- **Episodes:** "What happened." Large, pruned after `episodes_days`.
- **Facts:** "What is true." Small, kept long-term.
- **Skills:** "How to do it." Small, kept long-term.
- **Embeddings:** Vectors used for semantic recall. Size depends on the model and amount of text.

---

## Acrux App (native Swift UI)

A real native macOS app is included. It is built in SwiftUI + SpriteKit, runs the Python backend as a child process, and talks to it over HTTP/WebSocket. There is no webview.

### Install and pin to Dock

```bash
~/acrux/acrux/acrux/app_bundle/install_app.sh
```

Then:

1. Open **Finder → Go → Home → Applications**.
2. Right-click `Acrux.app` and choose **Open** the first time (to bypass Gatekeeper).
3. Drag `Acrux.app` to your Dock.
4. Right-click the Dock icon → **Options → Keep in Dock**.

The app shows **Acrux** in the menu bar and App Switcher, not Python.

### What the app does

- **Home screen:** animated SpriteKit particle-network background.
- **New Task:** choose a workspace folder with the native macOS picker, pick an Ollama model, enable/disable tools, and toggle auto-accept.
- **Chat:**
  - Shows model reasoning when the model emits `\<think\>...\</think\>`.
  - Shows every tool call with approve/deny buttons (or auto-executes if enabled).
  - Streams the final answer as it arrives.
- **Past Chats:** resume previous conversations.
- **Acrux Status:** start/stop the acrux daemon and expand "What it knows" to see an LLM-generated summary of stored facts and skills.

### Rebuild after code changes

```bash
cd ~/acrux/acrux/swift_app/Acrux
./build_app.sh
```

### Tool permissions

In the New Task screen you choose which tools the model may use:

- `read_file` — read a file inside the selected workspace.
- `list_files` — list files inside the workspace.
- `run_command` — run a shell command inside the workspace.
- `acrux_recall` — search the acrux's memory.
- `acrux_remember_fact` — save a new fact to the acrux.

`run_command` is the most dangerous; keep auto-accept off unless you trust the model.

---

## Troubleshooting

### `acrux: command not found`

Use the full path or add it to `PATH`:

```bash
export PATH="~/acrux/acrux/.venv/bin:$PATH"
```

### Reflection is slow or fails

- Check that Ollama is running: `ollama ps`
- Try a smaller batch: `acrux reflect --batch-size 3`
- Switch to Kimi if the machine is online: `acrux use-model kimi`

### MCP server times out

- Make sure `acrux start` works manually.
- Check `acrux logs` for errors.
- If using HTTP transport, check the port is free.

### Disk is filling up

- Lower `retention.max_storage_gb`.
- Reduce `retention.episodes_days`.
- Run `acrux prune --older-than 7d`.

### Semantic search returns nothing

- Verify an embedding model is set: `acrux config | grep embedding_model`
- Run reflection at least once so there are facts to search.
- Check that the profile is not `minimal`.

---

## Uninstall / reset

```bash
acrux reset          # Delete all acrux data but keep the program
```

To remove everything manually:

```bash
rm -rf ~/.acrux
rm -rf ~/acrux/acrux/.venv
```

Then remove the `acrux` entry from `~/.kimi-code/mcp.json` if you no longer want Kimi to use it.
