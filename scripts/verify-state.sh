#!/usr/bin/env bash
# Reports 6ix9ine's actual install state by querying real system state
# directly (brew, launchctl/ps, filesystem) — does NOT trust brew's or
# uninstall.sh's own reported success/failure, and does NOT need you to
# tell it what to expect. Just run it from anywhere:
#
#   ./scripts/verify-state.sh
#
# Exit code: 0 if every component agrees (fully installed or fully
# uninstalled), 1 if the state is mixed/inconsistent.
set -uo pipefail

GREEN=$'\033[0;32m'
RED=$'\033[0;31m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m'

present() { printf " ${GREEN}PRESENT${NC}   %s\n" "$1"; }
absent()  { printf " ${RED}ABSENT${NC}    %s\n" "$1"; }
info()    { printf " ${YELLOW}INFO${NC}      %s\n" "$1"; }

echo "== 6ix9ine install state =="
echo ""

INSTALLED_COUNT=0
ABSENT_COUNT=0

# --- Homebrew formula ---
if brew list --formula 6ix9ine &>/dev/null; then
    present "Homebrew formula"
    INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
else
    absent "Homebrew formula"
    ABSENT_COUNT=$((ABSENT_COUNT + 1))
fi

# --- Homebrew tap ---
if brew tap 2>/dev/null | grep -qx "rjmorales13/6ix9ine"; then
    present "Homebrew tap (rjmorales13/6ix9ine)"
    INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
else
    absent "Homebrew tap (rjmorales13/6ix9ine)"
    ABSENT_COUNT=$((ABSENT_COUNT + 1))
fi

# --- Binary presence + correctness ---
BREW_PREFIX="$(brew --prefix 2>/dev/null || true)"
if [ -n "$BREW_PREFIX" ] && [ -x "$BREW_PREFIX/bin/6ix9ine" ]; then
    present "Homebrew 6ix9ine binary (\$(brew --prefix)/bin/6ix9ine)"
    INSTALLED_COUNT=$((INSTALLED_COUNT + 1))

    VERSION_OUT="$("$BREW_PREFIX/bin/6ix9ine" --version 2>&1)"
    if echo "$VERSION_OUT" | grep -q "^6ix9ine v"; then
        info "'6ix9ine --version' → $VERSION_OUT"
    else
        printf " ${RED}BROKEN${NC}    binary exists but '--version' output looks wrong: %s\n" "$VERSION_OUT"
    fi

    if "$BREW_PREFIX/bin/t69" --help 2>&1 | grep -q "^usage: t69"; then
        info "'t69 --help' looks correct"
    else
        printf " ${RED}BROKEN${NC}    t69 --help output looks wrong\n"
    fi

    for CMD in 6ix9ine t69; do
        RESOLVED="$(command -v "$CMD" 2>/dev/null || echo "<not found>")"
        if [ "$RESOLVED" != "$BREW_PREFIX/bin/$CMD" ]; then
            printf " ${YELLOW}SHADOWED${NC}  bare '%s' on PATH resolves to %s instead of the Homebrew binary\n" "$CMD" "$RESOLVED"
            continue
        fi
        # Path resolution alone isn't enough — actually run the bare command,
        # since a shadowing binary can be present on PATH but itself broken
        # (e.g. a shim pointing at a deleted venv), which path resolution
        # can't detect but a real user typing the command hits immediately.
        BARE_OUT="$("$CMD" --help 2>&1)"
        if [ $? -ne 0 ] || ! echo "$BARE_OUT" | grep -qi "usage"; then
            printf " ${RED}BROKEN${NC}    bare '%s' resolves to the Homebrew binary but running it failed:\n" "$CMD"
            echo "$BARE_OUT" | sed 's/^/            /'
        else
            info "bare '$CMD' resolves to the Homebrew binary and runs correctly"
        fi
    done
else
    absent "Homebrew 6ix9ine binary"
    ABSENT_COUNT=$((ABSENT_COUNT + 1))
fi

# --- Daemon process ---
if pgrep -f "6ix9ine/daemon.py" &>/dev/null || pgrep -f "com.rjmorales.6ix9ine.daemon" &>/dev/null; then
    present "Daemon process (running)"
    INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
else
    absent "Daemon process (not running)"
    ABSENT_COUNT=$((ABSENT_COUNT + 1))
fi

# --- Privileged helper ---
if [ -f "/Library/LaunchDaemons/com.rjmorales.6ix9ine.helper.plist" ] || [ -f "/Library/PrivilegedHelperTools/com.rjmorales.6ix9ine.helper" ]; then
    present "Privileged helper (plist and/or binary on disk)"
    INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
    if pgrep -f "PrivilegedHelperTools/com.rjmorales.6ix9ine.helper" &>/dev/null; then
        info "privileged helper process is running"
    else
        info "privileged helper installed but not currently running"
    fi
else
    absent "Privileged helper"
    ABSENT_COUNT=$((ABSENT_COUNT + 1))
fi

# --- State directory ---
STATE_DIR="$HOME/Library/Application Support/6ix9ine"
if [ -d "$STATE_DIR" ]; then
    present "State directory ($STATE_DIR)"
    INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
else
    absent "State directory"
    ABSENT_COUNT=$((ABSENT_COUNT + 1))
fi

echo ""
echo "== Verdict =="
if [ "$ABSENT_COUNT" -eq 0 ]; then
    printf "${GREEN}Fully installed${NC} — every component present.\n"
    exit 0
elif [ "$INSTALLED_COUNT" -eq 0 ]; then
    printf "${GREEN}Fully uninstalled${NC} — nothing found on this system.\n"
    exit 0
else
    printf "${YELLOW}Mixed state${NC} — %d component(s) present, %d absent (see above).\n" "$INSTALLED_COUNT" "$ABSENT_COUNT"
    printf "This is expected mid-setup (e.g. right after 'brew install', before running\n"
    printf "'setup-privileged-helper'/'daemon-start') — not necessarily a bug.\n"
    exit 1
fi
