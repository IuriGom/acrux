# Acrux Installer

One command installs Acrux on a new machine:

```bash
curl -fsSL https://acrux.dev/install.sh | sh
```

This implements the plan in [`docs/installation-plan.md`](../docs/installation-plan.md).

## What gets installed

1. **uv** — the fast Python package manager (falls back to `python3 -m venv`).
2. **A virtualenv** at `~/.pia/venv` (Python 3.12), isolated from system Python.
3. **The acrux package** — from a SHA256-verified GitHub release tarball
   (stable channel) or from the git repo (`--channel main`).
4. **Configuration** via `acrux init --profile standard`, which creates
   `~/.acrux/config.yaml`, the data directories, and generates the API token.
   An existing config is never overwritten, so reinstalls keep your token.
5. **A user service** running `acrux daemon --background --mcp http`:
   - macOS: `~/Library/LaunchAgents/dev.pia.acrux.plist` (launchd)
   - Linux: `~/.config/systemd/user/pia-acrux.service` (systemd user unit)
6. **Optionally** the signed macOS app (stable channel) and the Kimi Code MCP
   integration (`acrux install-mcp --agent kimi --transport http`, only when
   the `kimi` CLI is detected).

Nothing runs as root; everything lives in your home directory.

## One-liner variants

```bash
# Stable release (default)
curl -fsSL https://acrux.dev/install.sh | sh

# Latest main branch
curl -fsSL https://acrux.dev/install.sh | sh -s -- --channel main

# Specific release version
curl -fsSL https://acrux.dev/install.sh | sh -s -- --version 1.0.0

# No macOS app
curl -fsSL https://acrux.dev/install.sh | sh -s -- --no-app

# Custom install dir (venv goes to <dir>/venv)
curl -fsSL https://acrux.dev/install.sh | sh -s -- --prefix "$HOME/.local/pia"

# In-place upgrade
curl -fsSL https://acrux.dev/install.sh | sh -s -- --upgrade
```

### install.sh options

| Option | Effect |
|---|---|
| `--channel stable\|main` | Install from a GitHub release (default) or from `main`. |
| `--version X.Y.Z` | Release version for the stable channel (default `1.0.0`). |
| `--prefix DIR` | Install prefix; venv at `DIR/venv` (default `~/.pia`). |
| `--no-app` | Skip the optional macOS app. |
| `--upgrade` | Upgrade in place: new package, `acrux doctor`, daemon restart. |
| `--no-service` | Write service files but do not load/start the daemon. |

Environment overrides: `PIA_HOME`, `PIA_HOME`, `ACRUX_GH_REPO`,
`ACRUX_VERSION`, `PYTHON_VERSION`, `ACRUX_NO_SERVICE=1` (same as
`--no-service`, useful for headless machines and tests).

## Upgrade

```bash
curl -fsSL https://acrux.dev/upgrade.sh | sh
```

`upgrade.sh` stops the daemon, creates a checked backup with `acrux backup create`,
runs `uv pip install --upgrade` (latest GitHub release by default; `--channel main`
or `--version X.Y.Z` to override), validates data with `acrux doctor`, and restarts
the daemon. A backup failure aborts the upgrade before installation. Your
`~/.acrux/config.yaml` is untouched.

Backup and recovery commands:

```bash
acrux backup create                 # create a checked SQLite backup
acrux backup list                   # show IDs, sizes, and validation state
acrux backup restore BACKUP_ID      # validate, create a safety backup, then restore
```

Restore requires the daemon to be stopped and asks for confirmation; use `--yes`
for an explicit noninteractive confirmation. Backups default to `~/.acrux/backups`
and exclude configuration, API tokens, logs, lock/PID files, and derived indexes.

## Uninstall

```bash
curl -fsSL https://acrux.dev/uninstall.sh | sh -s -- --yes
```

| Option | Effect |
|---|---|
| `--purge` | Also remove `~/.acrux` (config, API token, **all memory data**). |
| `--remove-app` | Also remove `/Applications/Acrux.app` (macOS). |
| `--prefix DIR` | Remove a custom install prefix. |
| `--yes` | Skip the confirmation prompt (required when piped via curl). |

By default the uninstaller removes the service and `~/.pia` but **keeps**
`~/.acrux`, so your memories survive a reinstall.

## Paths

| Path | Purpose |
|---|---|
| `~/.pia/venv` | Isolated Python environment with the `acrux` CLI. |
| `~/.acrux/config.yaml` | Configuration and generated API token. |
| `~/.acrux/data` | Memory stores (episodic, semantic, procedural). |
| `~/.acrux/logs` | Daemon and service logs. |
| `~/.acrux/acrux.pid` | Daemon pid file. |
| `~/Library/LaunchAgents/dev.pia.acrux.plist` | macOS LaunchAgent. |
| `~/.config/systemd/user/pia-acrux.service` | Linux systemd user unit. |

## Managing the daemon

The service starts the daemon at login and restarts it if it dies. Day-to-day
commands:

```bash
~/.pia/venv/bin/acrux status    # is it running?
~/.pia/venv/bin/acrux stop      # stop the daemon
~/.pia/venv/bin/acrux logs      # tail the daemon log
```

macOS (launchd):

```bash
launchctl bootout gui/$(id -u)/dev.pia.acrux            # stop + unload
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/dev.pia.acrux.plist
```

Linux (systemd user):

```bash
systemctl --user status pia-acrux.service
systemctl --user restart pia-acrux.service
# To start at boot without logging in, once:
sudo loginctl enable-linger "$USER"
```

Note: `acrux daemon --background` self-daemonizes and writes
`~/.acrux/acrux.pid`. The systemd unit uses `Type=forking` with that pid file
so systemd tracks the real daemon; the launchd job relies on the CLI's
pid-file guard to keep `KeepAlive` respawns idempotent.

## Manual install

Equivalent steps by hand:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

uv venv ~/.pia/venv --python 3.12
uv pip install --python ~/.pia/venv/bin/python \
    "git+https://github.com/<org>/acrux.git@main"

~/.pia/venv/bin/acrux init --profile standard
~/.pia/venv/bin/acrux daemon --background --mcp http
```

For development from a local checkout, see the repo `README.md`
(`pip install -e .`).

## Security notes

- Release tarballs are verified against `checksums.txt` (SHA256) from the same
  GitHub release before anything is installed.
- The scripts refuse to run as root; the daemon runs as your user.
- The API token is generated by `acrux init` on first run and is never
  hardcoded or transmitted.
- Serve `install.sh`/`uninstall.sh`/`upgrade.sh` over HTTPS only.

## Troubleshooting

- **"uv not found"** — the installer adds `~/.local/bin` and `~/.cargo/bin` to
  `PATH` for its own run; open a new shell or export one of those paths.
- **Daemon not running after install** — check `~/.acrux/logs/` and, on macOS,
  `~/Library/LaunchAgents` load errors via
  `launchctl print gui/$(id -u)/dev.pia.acrux`; on Linux
  `journalctl --user -u pia-acrux.service`.
- **Linux: service does not start at boot** — enable lingering:
  `sudo loginctl enable-linger "$USER"`.
- **Headless / CI machines** — use `--no-service` (or `ACRUX_NO_SERVICE=1`) to
  install without touching launchd/systemd, then run
  `acrux daemon --background --mcp http` yourself.
