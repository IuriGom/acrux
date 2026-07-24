#!/bin/sh
# =============================================================================
# PIA / Acrux in-place upgrade
#
#   curl -fsSL https://acrux.dev/upgrade.sh | sh
#
# Flow (per docs/installation-plan.md):
#   1. Stop the daemon (pid-file stop + user service).
#   2. `uv pip install --upgrade` the acrux package into ~/.pia/venv.
#   3. Run `acrux doctor` to validate data integrity.
#   4. Restart the daemon via the user service (or directly).
#
# The existing ~/.acrux/config.yaml (with its API token) is left untouched.
# =============================================================================
set -eu

# ---------------------------------------------------------------------------
# Configuration (same defaults as install.sh).
# ---------------------------------------------------------------------------
PIA_HOME="${PIA_HOME:-$HOME/.pia}"
PIA_HOME="${PIA_HOME:-$HOME/.acrux}"
# TODO: point this at the real GitHub org/user before publishing releases.
ACRUX_GH_REPO="${ACRUX_GH_REPO:-IuriGom/acrux}"
ACRUX_VERSION="${ACRUX_VERSION:-}"        # empty = resolve latest GitHub release
CHANNEL="stable"                          # stable | main
NO_SERVICE="${ACRUX_NO_SERVICE:-0}"       # 1 = never touch launchctl/systemctl

log()  { printf '%s\n' "==> $*"; }
warn() { printf '%s\n' "warning: $*" >&2; }
die()  { printf '%s\n' "error: $*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

TMP_DIR=""
cleanup() {
    if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
        rm -rf "$TMP_DIR"
    fi
}
trap cleanup EXIT INT TERM

usage() {
    cat <<'EOF'
Usage: upgrade.sh [options]

Options:
  --channel stable|main   Upgrade to the latest GitHub release (default) or to
                          the current main branch.
  --version X.Y.Z         Upgrade to a specific release (stable channel).
  --prefix DIR            Install prefix (default: ~/.pia).
  -h, --help              Show this help.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --channel)    CHANNEL="${2:-}"; [ -n "$CHANNEL" ] || die "--channel needs a value"; shift 2 ;;
        --channel=*)  CHANNEL="${1#*=}"; shift ;;
        --version)    ACRUX_VERSION="${2:-}"; [ -n "$ACRUX_VERSION" ] || die "--version needs a value"; shift 2 ;;
        --version=*)  ACRUX_VERSION="${1#*=}"; shift ;;
        --prefix)     PIA_HOME="${2:-}"; [ -n "$PIA_HOME" ] || die "--prefix needs a value"; shift 2 ;;
        --prefix=*)   PIA_HOME="${1#*=}"; shift ;;
        -h|--help)    usage; exit 0 ;;
        *)            die "unknown option: $1 (see --help)" ;;
    esac
done
case "$CHANNEL" in
    stable|main) : ;;
    *) die "unknown channel '$CHANNEL'" ;;
esac

VENV="$PIA_HOME/venv"
ACRUX_BIN="$VENV/bin/acrux"
PLIST_PATH="$HOME/Library/LaunchAgents/dev.pia.acrux.plist"
SYSTEMD_UNIT="$HOME/.config/systemd/user/pia-acrux.service"

OS="$(uname -s)"
case "$OS" in
    Darwin)  PLATFORM="macos" ;;
    Linux)   PLATFORM="linux" ;;
    MINGW*|MSYS*|CYGWIN*|Windows_NT)
        die "Windows is not supported natively. Please upgrade inside WSL2." ;;
    *) die "unsupported operating system: $OS" ;;
esac

if [ "$(id -u)" = "0" ]; then
    die "do not run the upgrade as root"
fi

# An upgrade needs an existing installation.
[ -x "$VENV/bin/python" ] || die "no installation found at $VENV — run install.sh first"
[ -x "$ACRUX_BIN" ] || die "acrux CLI not found at $ACRUX_BIN — run install.sh first"

# ---------------------------------------------------------------------------
# Step 1: stop the daemon. `acrux stop` uses the pid file and works no matter
# how the daemon was started; the service manager entries are stopped too.
# ---------------------------------------------------------------------------
stop_daemon() {
    "$ACRUX_BIN" stop >/dev/null 2>&1 || true
    if [ "$NO_SERVICE" = "1" ]; then
        return 0
    fi
    if [ "$PLATFORM" = "macos" ]; then
        launchctl bootout "gui/$(id -u)/dev.pia.acrux" >/dev/null 2>&1 || true
    else
        systemctl --user stop pia-acrux.service >/dev/null 2>&1 || true
    fi
}

# ---------------------------------------------------------------------------
# Step 2: resolve and install the new package version.
# ---------------------------------------------------------------------------
sha256_of() {
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
    awk -v n="$2" '{ f = $2; sub(/^\*/, "", f); if (f == n) print $1 }' "$1"
}

ensure_uv() {
    if have uv; then
        return 0
    fi
    # The venv was created by install.sh, so uv should exist; try the two
    # standard locations before attempting a fresh bootstrap.
    for d in "$HOME/.local/bin" "$HOME/.cargo/bin"; do
        if [ -d "$d" ]; then
            PATH="$d:$PATH"
        fi
    done
    export PATH
    if ! have uv; then
        log "Installing uv ..."
        curl -LsSf https://astral.sh/uv/install.sh | sh || die "could not install uv"
        for d in "$HOME/.local/bin" "$HOME/.cargo/bin"; do
            if [ -d "$d" ]; then
                PATH="$d:$PATH"
            fi
        done
        export PATH
    fi
    have uv || die "uv not found"
}

resolve_latest_version() {
    # Ask GitHub for the latest release tag when --version was not given.
    have curl || die "curl is required to resolve the latest release (or pass --version)"
    api="https://api.github.com/repos/$ACRUX_GH_REPO/releases/latest"
    tag="$(curl -fsSL "$api" | sed -n 's/.*"tag_name":[[:space:]]*"v\{0,1\}\([^"]*\)".*/\1/p' | head -n 1)"
    [ -n "$tag" ] || die "could not resolve the latest release of $ACRUX_GH_REPO"
    ACRUX_VERSION="$tag"
}

resolve_package_spec() {
    # Sets PKG_SPEC to the thing uv should install.
    if [ "$CHANNEL" = "main" ]; then
        PKG_SPEC="git+https://github.com/$ACRUX_GH_REPO.git@main"
        return 0
    fi
    if [ -z "$ACRUX_VERSION" ]; then
        resolve_latest_version
    fi
    log "Upgrading to v$ACRUX_VERSION ..."
    base="https://github.com/$ACRUX_GH_REPO/releases/download/v$ACRUX_VERSION"
    name="acrux-$ACRUX_VERSION.tar.gz"
    TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/pia-upgrade.XXXXXX")"
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

upgrade_package() {
    resolve_package_spec
    log "Installing upgrade ($CHANNEL channel) ..."
    uv pip install --python "$VENV/bin/python" --upgrade "$PKG_SPEC" \
        || die "package upgrade failed"
}

# ---------------------------------------------------------------------------
# Step 4: restart the daemon, preferring the user service when present.
# ---------------------------------------------------------------------------
start_daemon() {
    if [ "$NO_SERVICE" != "1" ] && [ "$PLATFORM" = "macos" ] && [ -f "$PLIST_PATH" ]; then
        launchctl bootout "gui/$(id -u)/dev.pia.acrux" >/dev/null 2>&1 || true
        if launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH" 2>/dev/null \
            || launchctl load -w "$PLIST_PATH" >/dev/null 2>&1; then
            log "LaunchAgent dev.pia.acrux restarted"
            return 0
        fi
        warn "could not load LaunchAgent; starting daemon directly"
    elif [ "$NO_SERVICE" != "1" ] && [ "$PLATFORM" = "linux" ] && [ -f "$SYSTEMD_UNIT" ] && have systemctl; then
        systemctl --user daemon-reload >/dev/null 2>&1 || true
        if systemctl --user start pia-acrux.service >/dev/null 2>&1; then
            log "systemd user service pia-acrux.service restarted"
            return 0
        fi
        warn "could not start systemd user service; starting daemon directly"
    fi
    "$ACRUX_BIN" daemon --background --mcp http || die "daemon restart failed"
}

# ---------------------------------------------------------------------------
# Main flow: stop -> upgrade -> doctor -> restart.
# ---------------------------------------------------------------------------
stop_daemon
ensure_uv
upgrade_package

log "Running acrux doctor ..."
"$ACRUX_BIN" doctor || warn "acrux doctor reported issues — check the output above"

start_daemon
log "Upgrade complete."
"$ACRUX_BIN" status || true
