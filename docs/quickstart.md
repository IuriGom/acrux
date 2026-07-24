# Quickstart

Get Acrux running in a few minutes. For the full installer design see the
[Installation Plan](installation-plan.md); for day-to-day operation see the
[Operating Guide](OPERATING.md).

## 1. Install

Requires Python 3.10+.

```bash
pip install -e .
```

This installs the `acrux` package and the `acrux` CLI (built with click).

## 2. Initialize

```bash
acrux init --profile standard
```

This creates `~/.acrux/config.yaml`, the data directories under `~/.acrux/data/`, and
generates an API token. Pick a profile that matches your machine:

| Profile | RAM target | Best for |
|---------|-----------|----------|
| `minimal` | ~256 MB | 4 GB RAM servers, pure logging |
| `light` | ~512 MB | 8 GB RAM servers |
| `standard` | ~1 GB | dedicated Acrux machine |
| `workstation` | ~2 GB | developer workstations |

## 3. Check status

```bash
acrux status --storage
```

## 4. Choose a reflection model

Reflection is the "self-training" step that turns raw episodes into facts and skills.

```bash
acrux use-model qwen3:14b   # local via Ollama, works offline
acrux use-model kimi        # online, no local RAM/disk cost
acrux use-model none        # disable reflection, keep memory storage
```

For semantic search, set an embedding model in `~/.acrux/config.yaml`:

```yaml
reflection:
  embedding_model: bge-m3
```

## 5. Run

```bash
# MCP server over stdio (what coding agents connect to)
acrux start

# Or the unified daemon: MCP + scheduled reflection + HTTP API in one process
acrux daemon --background --mcp http --port 11436
```

## 6. Connect your agent

```bash
acrux install-mcp --agent kimi      # also: claude, cursor, codex, gemini
```

This writes the Acrux MCP server entry into the agent's config file. The agent then calls
tools such as `acrux_remember_session`, `acrux_recall`, `acrux_context`, and
`acrux_reflect` automatically.

## 7. Learn from sessions

```bash
acrux reflect --project myrepo    # consolidate recent episodes into facts and skills
```

Semantic recall is exposed to agents through the `acrux_recall` / `acrux_context` MCP
tools and the Python SDK (`acrux.sdk.AcruxClient`); the CLI measures its quality with
`acrux recall-bench --project myrepo`.

## Verify the install

```bash
acrux doctor        # validate data integrity
pytest acrux/tests -v
```
