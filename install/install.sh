#!/bin/sh
# =============================================================================
# PIA / Acrux one-line installer
#
#   curl -fsSL https://acrux.dev/install.sh | sh
#
# What it does:
#   1. Detects the platform (macOS / Linux; Windows is told to use WSL2).
#   2. Installs uv (https://astral.sh/uv) if missing; falls back to
#      `python3 -m venv` when uv cannot be installed.
#   3. Creates an isolated virtualenv at ~/.pia/venv (Python 3.12).
#   4. Installs the acrux package from a GitHub release tarball (stable
#      channel, SHA256-verified against checksums.txt) or straight from the
#      git repo (--channel main).
#   5. Runs `acrux init --profile standard` on first install (an existing
#      ~/.acrux/config.yaml is never overwritten, so the API token survives
#      reinstalls and upgrades).
#   6. Installs and starts a *user* service that runs
#      `acrux daemon --background --mcp http`:
#        - macOS: ~/Library/LaunchAgents/dev.pia.acrux.plist (launchd)
#        - Linux: ~/.config/systemd/user/pia-acrux.service (systemd --user)
#   7. Optionally installs the signed macOS app and registers the acrux MCP
#      server with Kimi Code when the `kimi` CLI is detected.
#
# Safety: nothing here runs as root; the venv, config, data and services all
# live in the user's home directory.
# =============================================================================
set -eu

# ---------------------------------------------------------------------------
# Configuration — everything can be overridden via environment or flags.
# ---------------------------------------------------------------------------
INSTALL_HOME="${PIA_HOME:-$HOME/.pia}"      # install prefix; venv at $INSTALL_HOME/venv
ACRUX_HOME="${ACRUX_HOME:-$HOME/.acrux}"     # acrux config + data (see acrux/config.py)
# TODO: point this at the real GitHub org/user before publishing releases.
ACRUX_GH_REPO="${ACRUX_GH_REPO:-IuriGom/acrux}"
ACRUX_VERSION="${ACRUX_VERSION:-1.0.0}"   # release version for the stable channel
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"  # interpreter requested from uv
CHANNEL="stable"                          # stable | main
WITH_APP=1                                # try to install the macOS app
UPGRADE=0                                 # --upgrade mode
NO_SERVICE="${ACRUX_NO_SERVICE:-0}"       # 1 = write unit files but do not load/start
USE_UV=1                                  # flipped to 0 when falling back to python3

TMP_DIR=""                                # set once downloads happen; cleaned on exit

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
log()  { printf '%s\n' "==> $*"; }
warn() { printf '%s\n' "warning: $*" >&2; }
die()  { printf '%s\n' "error: $*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

cleanup() {
    # Remove the temporary download directory, if one was created.
    if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
        rm -rf "$TMP_DIR"
    fi
}
trap cleanup EXIT INT TERM

usage() {
    cat <<'EOF'
Usage: install.sh [options]

Options:
  --channel stable|main   Install from a GitHub release (default) or from the
                          main branch of the repo.
  --version X.Y.Z         Release version for the stable channel (default: 1.0.0).
  --prefix DIR            Install prefix; the venv goes to DIR/venv
                          (default: ~/.pia; same as setting INSTALL_HOME).
  --no-app                Do not download the optional macOS app.
  --upgrade               Upgrade an existing installation in place
                          (equivalent to running upgrade.sh).
  --no-service            Write service files but do not load/start the daemon
                          (also via ACRUX_NO_SERVICE=1; useful for headless tests).
  -h, --help              Show this help.

Environment overrides: INSTALL_HOME, ACRUX_HOME, ACRUX_GH_REPO, ACRUX_VERSION,
PYTHON_VERSION, ACRUX_NO_SERVICE.
EOF
}

# ---------------------------------------------------------------------------
# Parse command-line flags (POSIX-safe: no arrays, no getopt dependency).
# ---------------------------------------------------------------------------
while [ $# -gt 0 ]; do
    case "$1" in
        --channel)    CHANNEL="${2:-}"; [ -n "$CHANNEL" ] || die "--channel needs a value"; shift 2 ;;
        --channel=*)  CHANNEL="${1#*=}"; shift ;;
        --version)    ACRUX_VERSION="${2:-}"; [ -n "$ACRUX_VERSION" ] || die "--version needs a value"; shift 2 ;;
        --version=*)  ACRUX_VERSION="${1#*=}"; shift ;;
        --prefix)     INSTALL_HOME="${2:-}"; [ -n "$INSTALL_HOME" ] || die "--prefix needs a value"; shift 2 ;;
        --prefix=*)   INSTALL_HOME="${1#*=}"; shift ;;
        --no-app)     WITH_APP=0; shift ;;
        --upgrade)    UPGRADE=1; shift ;;
        --no-service) NO_SERVICE=1; shift ;;
        -h|--help)    usage; exit 0 ;;
        *)            die "unknown option: $1 (see --help)" ;;
    esac
done
case "$CHANNEL" in
    stable|main) : ;;
    *) die "unknown channel '$CHANNEL' (expected 'stable' or 'main')" ;;
esac

# Derived paths (after flag parsing so --prefix is honored).
VENV="$INSTALL_HOME/venv"
ACRUX_BIN="$VENV/bin/acrux"
PLIST_PATH="$HOME/Library/LaunchAgents/dev.pia.acrux.plist"
SYSTEMD_UNIT="$HOME/.config/systemd/user/pia-acrux.service"

# ---------------------------------------------------------------------------
# Step 1: detect platform.
# ---------------------------------------------------------------------------
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
    Darwin)  PLATFORM="macos" ;;
    Linux)   PLATFORM="linux" ;;
    MINGW*|MSYS*|CYGWIN*|Windows_NT)
        die "Windows is not supported natively. Please install inside WSL2: https://learn.microsoft.com/windows/wsl/install" ;;
    *) die "unsupported operating system: $OS" ;;
esac
case "$ARCH" in
    x86_64|amd64|arm64|aarch64) : ;;  # supported architectures
    *) warn "untested architecture: $ARCH (continuing anyway)" ;;
esac

# Never run as root: everything below is user-level (venv, LaunchAgent,
# systemd --user). Running as root would put files in the wrong home.
if [ "$(id -u)" = "0" ]; then
    die "do not run this installer as root — everything installs into the user's home directory"
fi

log "Platform: $OS/$ARCH, prefix: $INSTALL_HOME, channel: $CHANNEL"

# ---------------------------------------------------------------------------
# Step 2: make sure uv is available (fallback: python3 -m venv).
# ---------------------------------------------------------------------------
ensure_uv() {
    if have uv; then
        return 0
    fi
    log "Installing uv ..."
    if have curl; then
        curl -LsSf https://astral.sh/uv/install.sh | sh || warn "uv installer failed"
    else
        warn "curl not found; cannot bootstrap uv automatically"
    fi
    # The uv installer drops the binary in ~/.local/bin (current) or
    # ~/.cargo/bin (legacy). Pick up both without requiring a new shell.
    for d in "$HOME/.local/bin" "$HOME/.cargo/bin"; do
        if [ -d "$d" ]; then
            PATH="$d:$PATH"
        fi
    done
    export PATH
    if ! have uv; then
        if have python3; then
            warn "uv unavailable; falling back to python3 -m venv + pip"
            USE_UV=0
        else
            die "neither uv nor python3 found; install uv manually: https://docs.astral.sh/uv/"
        fi
    fi
}

# ---------------------------------------------------------------------------
# Step 3: create the isolated virtualenv at $INSTALL_HOME/venv.
# ---------------------------------------------------------------------------
create_venv() {
    if [ -x "$VENV/bin/python" ]; then
        log "Reusing existing virtualenv at $VENV"
        return 0
    fi
    log "Creating virtualenv at $VENV (Python $PYTHON_VERSION) ..."
    mkdir -p "$INSTALL_HOME"
    if [ "$USE_UV" = "1" ]; then
        uv venv "$VENV" --python "$PYTHON_VERSION" || die "uv venv failed"
    else
        python3 -m venv "$VENV" || die "python3 -m venv failed"
    fi
}

# ---------------------------------------------------------------------------
# Step 4: resolve + verify + install the acrux package.
# ---------------------------------------------------------------------------
sha256_of() {
    # Print the SHA256 of $1 using whichever tool the platform provides.
    if have shasum; then
        shasum -a 256 "$1" | awk '{print $1}'
    elif have sha256sum; then
        sha256sum "$1" | awk '{print $1}'
    else
        die "need shasum or sha256sum to verify release checksums"
    fi
}

checksum_for() {
    # Extract the expected SHA256 for file $2 from checksums.txt ($1).
    # Handles both "hash  name" and "hash *name" formats.
    awk -v n="$2" '{ f = $2; sub(/^\*/, "", f); if (f == n) print $1 }' "$1"
}

resolve_package_spec() {
    # Sets PKG_SPEC to the thing uv/pip should install.
    if [ "$CHANNEL" = "main" ]; then
        # Latest development build straight from the repo.
        PKG_SPEC="git+https://github.com/$ACRUX_GH_REPO.git@main"
        return 0
    fi
    # Stable: download the release tarball and verify it against checksums.txt
    # before installing (see "Security and safety" in docs/installation-plan.md).
    have curl || die "curl is required for the stable channel (or use --channel main)"
    base="https://github.com/$ACRUX_GH_REPO/releases/download/v$ACRUX_VERSION"
    name="acrux-$ACRUX_VERSION.tar.gz"
    TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/pia-install.XXXXXX")"
    log "Downloading $name (v$ACRUX_VERSION) ..."
    curl -fsSL -o "$TMP_DIR/$name" "$base/$name" \
        || die "download failed: $base/$name"
    curl -fsSL -o "$TMP_DIR/checksums.txt" "$base/checksums.txt" \
        || die "checksums.txt not found for release v$ACRUX_VERSION"
    expected="$(checksum_for "$TMP_DIR/checksums.txt" "$name")"
    [ -n "$expected" ] || die "no checksum entry for $name in checksums.txt"
    actual="$(sha256_of "$TMP_DIR/$name")"
    if [ "$expected" != "$actual" ]; then
        die "checksum mismatch for $name (expected $expected, got $actual) — aborting"
    fi
    log "Checksum verified for $name"
    PKG_SPEC="$TMP_DIR/$name"
}

install_package() {
    resolve_package_spec
    if [ "$UPGRADE" = "1" ]; then
        PIP_FLAGS="--upgrade"
    else
        PIP_FLAGS=""
    fi
    log "Installing acrux package ($CHANNEL channel) ..."
    if [ "$USE_UV" = "1" ]; then
        # --python targets the venv interpreter, no shell activation needed.
        # PIP_FLAGS is intentionally unquoted: it is empty or a single flag.
        uv pip install --python "$VENV/bin/python" $PIP_FLAGS "$PKG_SPEC" \
            || die "package install failed"
    else
        "$VENV/bin/pip" install $PIP_FLAGS "$PKG_SPEC" || die "package install failed"
    fi
    [ -x "$ACRUX_BIN" ] || die "acrux CLI not found at $ACRUX_BIN after install"
}

# ---------------------------------------------------------------------------
# Step 5: initialize acrux (first install only — never clobber an existing
# config, because it holds the generated API token).
# ---------------------------------------------------------------------------
run_init() {
    CONFIG_HOME="${ACRUX_HOME:-$HOME/.acrux}"
    if [ -f "$CONFIG_HOME/config.yaml" ]; then
        log "Keeping existing config at $CONFIG_HOME/config.yaml (init skipped)"
        return 0
    fi
    log "Initializing acrux (profile: standard) ..."
    "$ACRUX_BIN" init --profile standard || die "acrux init failed"
}

# ---------------------------------------------------------------------------
# Step 6: user service for `acrux daemon --background --mcp http`.
# ---------------------------------------------------------------------------
write_plist() {
    mkdir -p "$HOME/Library/LaunchAgents" "$ACRUX_HOME/logs"
    cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>dev.pia.acrux</string>
    <!-- acrux daemon --background self-daemonizes and exits; the pid-file
         guard in acrux makes launchd respawns a no-op while the real daemon
         is alive. ThrottleInterval keeps the respawn cadence sane. -->
    <key>ProgramArguments</key>
    <array>
        <string>$ACRUX_BIN</string>
        <string>daemon</string>
        <string>--background</string>
        <string>--mcp</string>
        <string>http</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>60</integer>
    <key>StandardOutPath</key>
    <string>$ACRUX_HOME/logs/launchd.out.log</string>
    <key>StandardErrorPath</key>
    <string>$ACRUX_HOME/logs/launchd.err.log</string>
</dict>
</plist>
EOF
}

write_systemd_unit() {
    mkdir -p "$HOME/.config/systemd/user"
    cat > "$SYSTEMD_UNIT" <<EOF
[Unit]
Description=PIA Acrux Daemon
After=network-online.target

[Service]
# acrux daemon --background forks and writes its pid file, so Type=forking
# with PIDFile lets systemd track the real daemon process (and Restart
# only fires when the daemon itself dies, not when the wrapper exits).
Type=forking
PIDFile=$INSTALL_HOME/acrux.pid
ExecStart=$ACRUX_BIN daemon --background --mcp http
ExecStop=$ACRUX_BIN stop
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF
}

start_service() {
    # Always (re)write the unit files so they match the current install
    # prefix; ACRUX_NO_SERVICE=1 only skips loading/starting them.
    if [ "$PLATFORM" = "macos" ]; then
        write_plist
    else
        write_systemd_unit
    fi
    if [ "$NO_SERVICE" = "1" ]; then
        log "ACRUX_NO_SERVICE=1 — service files written but not loaded"
        return 0
    fi
    if [ "$PLATFORM" = "macos" ]; then
        # Replace any previously loaded agent, then load the new one.
        launchctl bootout "gui/$(id -u)/dev.pia.acrux" >/dev/null 2>&1 || true
        if launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH" 2>/dev/null; then
            log "LaunchAgent dev.pia.acrux loaded"
        else
            # Fallback for older macOS without launchctl bootstrap.
            launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
            if launchctl load -w "$PLIST_PATH" >/dev/null 2>&1; then
                log "LaunchAgent dev.pia.acrux loaded"
            else
                warn "could not load LaunchAgent; starting daemon directly instead"
                "$ACRUX_BIN" daemon --background --mcp http || warn "daemon start failed"
            fi
        fi
    else
        if have systemctl && systemctl --user daemon-reload >/dev/null 2>&1; then
            if systemctl --user enable --now pia-acrux.service >/dev/null 2>&1; then
                log "systemd user service pia-acrux.service enabled and started"
            else
                warn "could not start systemd user service; starting daemon directly"
                "$ACRUX_BIN" daemon --background --mcp http || warn "daemon start failed"
            fi
        else
            warn "systemd --user unavailable; starting daemon directly"
            "$ACRUX_BIN" daemon --background --mcp http || warn "daemon start failed"
        fi
    fi
}

# ---------------------------------------------------------------------------
# Step 7: optional macOS app (stable channel only; failure is not fatal).
# ---------------------------------------------------------------------------
install_macos_app() {
    [ "$PLATFORM" = "macos" ] || return 0
    [ "$WITH_APP" = "1" ] || return 0
    if [ "$CHANNEL" != "stable" ]; then
        log "Skipping macOS app on --channel main"
        return 0
    fi
    have curl || return 0
    base="https://github.com/$ACRUX_GH_REPO/releases/download/v$ACRUX_VERSION"
    if [ -z "$TMP_DIR" ]; then
        TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/pia-install.XXXXXX")"
    fi
    log "Downloading Acrux.app ..."
    if ! curl -fsSL -o "$TMP_DIR/Acrux.zip" "$base/Acrux.zip"; then
        warn "Acrux.app not available for v$ACRUX_VERSION; skipping (it is optional)"
        return 0
    fi
    # Verify against checksums.txt when it was fetched for the package install.
    if [ -f "$TMP_DIR/checksums.txt" ]; then
        expected="$(checksum_for "$TMP_DIR/checksums.txt" "Acrux.zip")"
        if [ -n "$expected" ] && [ "$expected" != "$(sha256_of "$TMP_DIR/Acrux.zip")" ]; then
            warn "checksum mismatch for Acrux.zip; skipping app install"
            return 0
        fi
    fi
    if unzip -q "$TMP_DIR/Acrux.zip" -d /Applications/ 2>/dev/null; then
        log "Installed /Applications/Acrux.app"
    else
        warn "could not unzip to /Applications (permissions?); skipping app install"
    fi
}

# ---------------------------------------------------------------------------
# Step 8: optional Kimi Code MCP integration (only when kimi is installed).
# Uses the http transport so Kimi talks to the daemon set up above.
# ---------------------------------------------------------------------------
install_kimi_mcp() {
    if have kimi; then
        log "Kimi Code detected — registering acrux MCP server ..."
        "$ACRUX_BIN" install-mcp --agent kimi --transport http \
            || warn "acrux install-mcp failed (continuing)"
    fi
}

# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------
ensure_uv
create_venv
install_package
run_init
start_service
install_macos_app
install_kimi_mcp

# On --upgrade, validate data integrity as the plan prescribes.
if [ "$UPGRADE" = "1" ]; then
    log "Running acrux doctor ..."
    "$ACRUX_BIN" doctor || warn "acrux doctor reported issues — check the output above"
fi

cat <<EOF

Install complete.
  venv:    $VENV
  config:  $ACRUX_HOME/config.yaml
  logs:    $ACRUX_HOME/logs
  service: $(if [ "$PLATFORM" = "macos" ]; then echo "$PLIST_PATH"; else echo "$SYSTEMD_UNIT"; fi)

Check status with:  $ACRUX_BIN status
Uninstall with:     sh $(dirname "$0")/uninstall.sh --yes
EOF
