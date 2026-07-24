# PIA Installer Plan

**Goal:** one command installs the Acrux on a new machine.

```bash
curl -fsSL https://acrux.dev/install.sh | sh
```

---

## What gets installed

1. Python environment (isolated, not system Python)
2. Acrux package (from GitHub release or PyPI)
3. Configuration (`~/.acrux/config.yaml`)
4. Daemon (launchd on macOS, systemd on Linux)
5. Optional macOS app (from GitHub Releases)
6. Optional Kimi Code MCP integration

---

## Files to add to the repo

```
install/
├── install.sh          # one-line installer
├── uninstall.sh        # clean removal
├── upgrade.sh          # in-place upgrade
├── pia.rb              # Homebrew formula (optional)
└── README.md           # manual install docs
```

---

## install.sh logic

### 1. Detect platform

```bash
OS="$(uname -s)"
ARCH="$(uname -m)"
```

Support:
- macOS (arm64 + x86_64)
- Linux (x86_64 + arm64)

Fail on Windows with a message pointing to WSL2.

### 2. Install Python tooling

Use `uv` (fast, modern Python package manager):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"
```

Fallback: `python3 -m venv`.

### 3. Create isolated environment

```bash
ACRUX_HOME="${ACRUX_HOME:-$HOME/.pia}"
uv venv "$ACRUX_HOME/venv" --python 3.12
source "$ACRUX_HOME/venv/bin/activate"
```

### 4. Install the Acrux package

From GitHub release tarball (stable):

```bash
uv pip install "acrux @ https://github.com/<user>/pia/releases/download/v1.0.0/pia-1.0.0.tar.gz"
```

Or from the repo (latest):

```bash
uv pip install "git+https://github.com/<user>/acrux.git@main"
```

### 5. Initialize

```bash
acrux init --profile standard
```

Creates `~/.acrux/config.yaml`, data dirs, and generates the API token.

### 6. Install the daemon

**macOS** — create `~/Library/LaunchAgents/dev.acrux.acrux.plist`:

```xml
<plist>
  <dict>
    <key>Label</key><string>dev.acrux.acrux</string>
    <key>ProgramArguments</key>
    <array>
      <string>$ACRUX_HOME/venv/bin/acrux</string>
      <string>daemon</string>
      <string>--background</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
  </dict>
</plist>
```

**Linux** — create `~/.config/systemd/user/acrux.service`:

```ini
[Unit]
Description=PIA Acrux Daemon

[Service]
ExecStart=%h/.pia/venv/bin/acrux daemon --background
Restart=always

[Install]
WantedBy=default.target
```

### 7. Optional macOS app

```bash
curl -fsSL -o /tmp/Acrux.zip "https://github.com/<user>/pia/releases/download/v1.0.0/Acrux.zip"
unzip -q /tmp/Acrux.zip -d /Applications/
```

### 8. Optional Kimi Code MCP integration

Add a `acrux install-mcp` command that writes the MCP server config to Kimi Code's config directory. The installer calls it if `kimi` is detected.

---

## Release artifacts

| Artifact | Purpose |
|---|---|
| `acrux-<version>.tar.gz` | Python source tarball for `uv pip install` |
| `Acrux.zip` | Signed macOS app bundle |
| `install.sh` | The one-line installer |
| `checksums.txt` | SHA256 for all artifacts |

---

## Upgrade flow

```bash
curl -fsSL https://acrux.dev/install.sh | sh -s -- --upgrade
```

- Stops daemon
- `uv pip install --upgrade acrux`
- Runs `acrux doctor`
- Restarts daemon

---

## Uninstall flow

```bash
curl -fsSL https://acrux.dev/uninstall.sh | sh
```

- Stops daemon
- Removes `~/.pia` (venv)
- Optionally removes `~/.acrux` (data) with `--purge`
- Removes LaunchAgent/systemd unit
- Optionally removes `/Applications/Acrux.app`

---

## Security and safety

- `install.sh` must be checksummed and served over HTTPS.
- Do not run anything as root; use user-level LaunchAgent/systemd.
- Verify GitHub release checksums before installing.
- The daemon's API token is generated on first run and never hardcoded.

---

## One-liner variants

```bash
# Stable
curl -fsSL https://acrux.dev/install.sh | sh

# Latest main
curl -fsSL https://acrux.dev/install.sh | sh -s -- --channel main

# No macOS app
curl -fsSL https://acrux.dev/install.sh | sh -s -- --no-app

# Custom install dir
curl -fsSL https://acrux.dev/install.sh | sh -s -- --prefix "$HOME/.local/pia"
```

---

## Pre-open-source checklist

1. Rename the package from `acrux` to `pia` (or public name).
2. Add a `pyproject.toml` script entry for the CLI.
3. Create a GitHub Release with the tarball and app.
4. Add `acrux install-mcp` for Kimi Code auto-config.
5. Write and test the installer scripts on a clean machine.
6. Set up GitHub Actions to build the release tarball and app on tag push.
