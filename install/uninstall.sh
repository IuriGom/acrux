#!/bin/sh
# =============================================================================
# PIA / Acrux uninstaller
#
#   curl -fsSL https://acrux.dev/uninstall.sh | sh -s -- --yes
#
# Removes:
#   - the launchd LaunchAgent (macOS) or systemd user unit (Linux)
#   - the virtualenv and everything under ~/.pia
#   - optionally ~/.acrux (config + all memory data) with --purge
#   - optionally /Applications/Acrux.app with --remove-app
#
# The script never runs as root and never touches anything outside the paths
# listed above.
# =============================================================================
set -eu

# ---------------------------------------------------------------------------
# Configuration (same defaults as install.sh).
# ---------------------------------------------------------------------------
INSTALL_HOME="${PIA_HOME:-$HOME/.pia}"     # venv lives at $INSTALL_HOME/venv
DATA_HOME="${ACRUX_HOME:-$HOME/.acrux}"    # config + data
PURGE=0                                     # 1 = also remove $DATA_HOME
REMOVE_APP=0                                # 1 = also remove /Applications/Acrux.app
ASSUME_YES=0                                # 1 = skip the confirmation prompt

log()  { printf '%s\n' "==> $*"; }
warn() { printf '%s\n' "warning: $*" >&2; }
die()  { printf '%s\n' "error: $*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

usage() {
    cat <<'EOF'
Usage: uninstall.sh [options]

Options:
  --purge        Also remove ~/.acrux (config, API token, all memory data).
  --remove-app   Also remove /Applications/Acrux.app (macOS).
  --prefix DIR   Install prefix to remove (default: ~/.pia).
  --yes          Do not ask for confirmation (required when piped via curl).
  -h, --help     Show this help.
EOF
}

# ---------------------------------------------------------------------------
# Parse flags.
# ---------------------------------------------------------------------------
while [ $# -gt 0 ]; do
    case "$1" in
        --purge)      PURGE=1; shift ;;
        --remove-app) REMOVE_APP=1; shift ;;
        --prefix)     INSTALL_HOME="${2:-}"; [ -n "$INSTALL_HOME" ] || die "--prefix needs a value"; shift 2 ;;
        --prefix=*)   INSTALL_HOME="${1#*=}"; shift ;;
        --yes|-y)     ASSUME_YES=1; shift ;;
        -h|--help)    usage; exit 0 ;;
        *)            die "unknown option: $1 (see --help)" ;;
    esac
done

ACRUX_BIN="$INSTALL_HOME/venv/bin/acrux"
PLIST_PATH="$HOME/Library/LaunchAgents/dev.pia.acrux.plist"
SYSTEMD_UNIT="$HOME/.config/systemd/user/pia-acrux.service"

# Never run as root: all managed files are user-level.
if [ "$(id -u)" = "0" ]; then
    die "do not run the uninstaller as root"
fi

# ---------------------------------------------------------------------------
# Confirmation — required, because --purge is irreversible.
# ---------------------------------------------------------------------------
confirm() {
    if [ "$ASSUME_YES" = "1" ]; then
        return 0
    fi
    if [ -t 0 ]; then
        extra=""
        if [ "$PURGE" = "1" ]; then
            extra=" including $DATA_HOME (ALL memory data)"
        fi
        printf 'This will remove the acrux service and %s%s. Continue? [y/N] ' "$INSTALL_HOME" "$extra"
        read -r reply
        case "$reply" in
            y|Y|yes|YES|Yes) return 0 ;;
            *) die "aborted" ;;
        esac
    fi
    # Non-interactive (e.g. curl | sh): require an explicit --yes.
    die "non-interactive shell; re-run with --yes to confirm"
}
confirm

# ---------------------------------------------------------------------------
# rm -rf guard: refuse obviously wrong targets.
# ---------------------------------------------------------------------------
safe_rm_rf() {
    case "$1" in
        ""|"/"|"$HOME"|"$HOME/") die "refusing to remove '$1'" ;;
    esac
    if [ -e "$1" ]; then
        rm -rf "$1"
        log "Removed $1"
    fi
}

# ---------------------------------------------------------------------------
# Step 1: stop the daemon. `acrux stop` works via the pid file regardless of
# how the daemon was started; the service managers are stopped below.
# ---------------------------------------------------------------------------
if [ -x "$ACRUX_BIN" ]; then
    "$ACRUX_BIN" stop >/dev/null 2>&1 || true
fi

# ---------------------------------------------------------------------------
# Step 2: unload and remove the user service.
# ---------------------------------------------------------------------------
OS="$(uname -s)"
if [ "$OS" = "Darwin" ]; then
    if have launchctl; then
        # Modern form first, legacy unload as fallback; both may legitimately
        # fail when the agent is not loaded, so errors are ignored.
        launchctl bootout "gui/$(id -u)/dev.pia.acrux" >/dev/null 2>&1 || true
        if [ -f "$PLIST_PATH" ]; then
            launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
        fi
    fi
    if [ -f "$PLIST_PATH" ]; then
        rm -f "$PLIST_PATH"
        log "Removed $PLIST_PATH"
    fi
elif [ "$OS" = "Linux" ]; then
    if have systemctl; then
        systemctl --user disable --now pia-acrux.service >/dev/null 2>&1 || true
    fi
    if [ -f "$SYSTEMD_UNIT" ]; then
        rm -f "$SYSTEMD_UNIT"
        log "Removed $SYSTEMD_UNIT"
    fi
    if have systemctl; then
        systemctl --user daemon-reload >/dev/null 2>&1 || true
    fi
fi

# ---------------------------------------------------------------------------
# Step 3: remove the install prefix (venv + everything uv created).
# ---------------------------------------------------------------------------
safe_rm_rf "$INSTALL_HOME"

# ---------------------------------------------------------------------------
# Step 4: optionally purge config + data, and remove the macOS app.
# ---------------------------------------------------------------------------
if [ "$PURGE" = "1" ]; then
    safe_rm_rf "$DATA_HOME"
else
    log "Kept $DATA_HOME (use --purge to remove config and data)"
fi

if [ "$REMOVE_APP" = "1" ] && [ "$OS" = "Darwin" ]; then
    if [ -d "/Applications/Acrux.app" ]; then
        if rm -rf "/Applications/Acrux.app" 2>/dev/null; then
            log "Removed /Applications/Acrux.app"
        else
            warn "could not remove /Applications/Acrux.app (permissions?)"
        fi
    fi
fi

log "Uninstall complete."
