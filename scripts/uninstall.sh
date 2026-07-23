#!/usr/bin/env bash
# Fully removes 6ix9ine from this Mac: agent hooks, the background daemon,
# the root-privileged helper, and the Homebrew formula/tap.
#
# Order matters: the daemon/helper/hooks teardown must run *before* the
# `6ix9ine` binary is uninstalled, since those steps shell out to the CLI's
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
            echo "                 this script's job is to fully uninstall 6ix9ine."
            exit 0
            ;;
    esac
done

# Prefer the Homebrew-installed binary explicitly. A bare `6ix9ine` on PATH
# can resolve to an unrelated install (e.g. a leftover from-source
# ./install.sh shim in ~/.local/bin) if it happens to sit earlier in PATH —
# `brew install` warns about exactly this kind of shadowing. Falls back to
# PATH lookup only when there's no Homebrew install to prefer, so this script
# still works for a from-source-only install.
SIXNINE_BIN="6ix9ine"
if command -v brew &>/dev/null; then
    BREW_PREFIX="$(brew --prefix 2>/dev/null || true)"
    if [ -n "$BREW_PREFIX" ] && [ -x "$BREW_PREFIX/bin/6ix9ine" ]; then
        SIXNINE_BIN="$BREW_PREFIX/bin/6ix9ine"
    fi
fi

if command -v "$SIXNINE_BIN" &>/dev/null; then
    log "Removing agent hooks..."
    "$SIXNINE_BIN" uninstall-hooks --all || fail "uninstall-hooks failed (continuing)"

    log "Stopping the background daemon..."
    "$SIXNINE_BIN" daemon-stop || fail "daemon-stop failed (continuing; it may not have been running)"

    log "Removing the privileged helper (requires sudo)..."
    "$SIXNINE_BIN" uninstall-helper || fail "uninstall-helper failed — the root LaunchDaemon may still be installed (continuing)"
else
    warn "6ix9ine command not found — skipping hooks/daemon/helper teardown."
    warn "If a daemon or privileged helper is still running from a prior install,"
    warn "remove them manually (see 6ix9ine-rap-sheet-docs/INSTALL.md)."
fi

# Ask brew directly about this one formula rather than grepping the full
# `brew list --formula` dump for an exact-line match — a direct query's exit
# code is the same signal `brew uninstall`/`brew untap` use internally, so it
# can't disagree with them the way a separately-parsed list can.
if brew list --formula 6ix9ine &>/dev/null; then
    log "Uninstalling the Homebrew formula..."
    brew uninstall rjmorales13/6ix9ine/6ix9ine 2>/dev/null || brew uninstall 6ix9ine || fail "brew uninstall failed"
else
    log "Homebrew formula not installed, skipping."
fi

if brew tap 2>/dev/null | grep -qx "rjmorales13/6ix9ine"; then
    log "Removing the rjmorales13/6ix9ine tap..."
    brew untap rjmorales13/6ix9ine || fail "brew untap failed"
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
    warn "6ix9ine uninstall completed with warnings — see above. Some components may not be fully removed."
    exit 1
fi

log "6ix9ine has been uninstalled."
