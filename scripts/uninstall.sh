#!/usr/bin/env bash
# Fully removes Stay Woke from this Mac: agent hooks, the background daemon,
# the root-privileged helper, and the Homebrew formula/tap.
#
# Order matters: the daemon/helper/hooks teardown must run *before* the
# `staywoke` binary is uninstalled, since those steps shell out to the CLI's
# own subcommands (which know the exact LaunchAgent/LaunchDaemon paths) rather
# than re-deriving them here, so this script can't drift out of sync with
# bin/shared.py.
set -uo pipefail

BOLD=$'\033[1m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m'

log()  { printf " ${GREEN}*${NC}  %s\n" "$1"; }
warn() { printf " ${YELLOW}!${NC}  %s\n" "$1"; }

FAILED=0
fail() { warn "$1"; FAILED=1; }

KEEP_STATE=0
for arg in "$@"; do
    case "$arg" in
        --keep-state)
            KEEP_STATE=1
            ;;
        -h|--help)
            echo "Usage: $0 [--keep-state]"
            echo ""
            echo "  --keep-state   Do NOT delete ~/Library/Application Support/6ix9ine"
            echo "                 (logs, socket, local state). Removed by default, since"
            echo "                 this script's job is to fully uninstall Stay Woke."
            exit 0
            ;;
    esac
done

# Prefer the installed Homebrew command, then try a source install.
STAYWOKE_BIN=""
if command -v brew &>/dev/null; then
    BREW_PREFIX="$(brew --prefix 2>/dev/null || true)"
    if [ -n "$BREW_PREFIX" ]; then
        for name in staywoke 6ix9ine; do
            if [ -x "$BREW_PREFIX/bin/$name" ]; then
                STAYWOKE_BIN="$BREW_PREFIX/bin/$name"
                break
            fi
        done
    fi
fi
if [ -z "$STAYWOKE_BIN" ]; then
    STAYWOKE_BIN="$(command -v staywoke || command -v 6ix9ine || true)"
fi

if [ -n "$STAYWOKE_BIN" ]; then
    log "Removing agent hooks..."
    "$STAYWOKE_BIN" uninstall-hooks --all || fail "uninstall-hooks failed (continuing)"

    log "Stopping the background daemon..."
    "$STAYWOKE_BIN" daemon-stop || fail "daemon-stop failed (continuing; it may not have been running)"

    log "Removing the privileged helper (requires sudo)..."
    "$STAYWOKE_BIN" uninstall-helper || fail "uninstall-helper failed — the root LaunchDaemon may still be installed (continuing)"
else
    warn "Stay Woke command not found — skipping hooks/daemon/helper teardown."
    warn "If a daemon or privileged helper is still running from a prior install,"
    warn "remove them manually (see docs/INSTALL.md)."
fi

# Ask brew directly about this one formula rather than grepping the full
# `brew list --formula` dump for an exact-line match — a direct query's exit
# code is the same signal `brew uninstall`/`brew untap` use internally, so it
# can't disagree with them the way a separately-parsed list can.
for formula in rjmorales13/staywoke/staywoke rjmorales13/6ix9ine/staywoke rjmorales13/6ix9ine/6ix9ine; do
    if brew list --formula --full-name 2>/dev/null | grep -Fx "$formula" >/dev/null; then
        log "Uninstalling $formula from the Homebrew tap..."
        brew uninstall "$formula" || fail "brew uninstall failed for $formula"
    fi
done

for tap in rjmorales13/staywoke rjmorales13/6ix9ine; do
    if brew tap 2>/dev/null | grep -Fx "$tap" >/dev/null; then
        log "Removing the $tap tap..."
        brew untap "$tap" || fail "brew untap failed for $tap"
    fi
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_BIN="$HOME/.local/bin/staywoke"
SOURCE_PYTHON="$HOME/Library/Application Support/6ix9ine/venv/bin/python3"
if [ -f "$SOURCE_BIN" ] && [ ! -L "$SOURCE_BIN" ] &&
    printf '#!/bin/sh\nexec "%s" "%s/bin/cli.py" "$@"\n' "$SOURCE_PYTHON" "$REPO_ROOT" | cmp -s - "$SOURCE_BIN"; then
    rm -f "$SOURCE_BIN" || fail "could not remove the source wrapper"
fi

STATE_DIR="${SIXNINE_STATE_DIR:-$HOME/Library/Application Support/6ix9ine}"
if [ -d "$STATE_DIR" ]; then
    if [ "$KEEP_STATE" -eq 1 ]; then
        warn "Keeping state directory (--keep-state): $STATE_DIR"
    else
        log "Removing state directory: $STATE_DIR"
        rm -rf "$STATE_DIR"
    fi
fi

if [ "$FAILED" -eq 1 ]; then
    warn "Stay Woke uninstall completed with warnings — see above. Some components may not be fully removed."
    exit 1
fi

log "Stay Woke has been uninstalled."
