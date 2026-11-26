#!/usr/bin/env bash
# Install Stay Woke or migrate an existing Homebrew install.
set -euo pipefail

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    printf '%s\n' "Usage: bash $0" \
        "Install or upgrade Stay Woke with Homebrew, refresh its services and hooks," \
        "and check the result. Run after active tasks finish. Helper setup uses sudo."
    exit 0
fi
if (( $# != 0 )); then
    printf 'Unexpected argument: %s\n' "$1" >&2
    exit 2
fi
if [[ "$(uname -s)" != Darwin ]] || ! command -v brew >/dev/null 2>&1; then
    printf '%s\n' 'Stay Woke requires macOS and Homebrew.' >&2
    exit 1
fi

tap="rjmorales13/staywoke"
legacy_tap="rjmorales13/6ix9ine"
formula="$tap/staywoke"

if ! brew tap | grep -Fx "$tap" >/dev/null; then
    brew tap "$tap"
fi
if brew command trust >/dev/null 2>&1; then
    brew trust --formula "$formula"
fi
brew update

cellar="$(brew --cellar)"
if compgen -G "$cellar/6ix9ine/*/INSTALL_RECEIPT.json" >/dev/null; then
    if ! brew tap | grep -Fx "$legacy_tap" >/dev/null; then
        brew tap "$legacy_tap"
    fi
    brew migrate --formula "$legacy_tap/6ix9ine"
fi

prefix="$(brew --prefix)"
installed="$(brew list --versions "$formula" 2>/dev/null || true)"
if [[ -n "$installed" ]]; then
    outdated="$(brew outdated --quiet --formula "$formula")"
    if [[ -n "$outdated" ]]; then
        brew upgrade "$formula"
    fi
    receipt="$prefix/opt/staywoke/INSTALL_RECEIPT.json"
    if [[ -f "$receipt" ]] &&
        [[ "$(plutil -extract source.tap raw -o - "$receipt")" == "$legacy_tap" ]]; then
        brew reinstall "$formula"
    fi
else
    brew install "$formula"
fi

# Use Homebrew's installed command even if PATH contains a source wrapper.
cli="$prefix/bin/staywoke"
"$cli" --version
"$cli" dashboard --help >/dev/null
"$cli" setup-privileged-helper
"$cli" daemon-restart

# These are the supported lifecycle hooks. A missing agent is normal.
for agent in claude opencode; do
    if "$cli" install-hooks --agent "$agent"; then
        continue
    else
        result=$?
        if (( result != 6 )); then
            exit "$result"
        fi
    fi
done

"$cli" status
for legacy in 6ix9ine t69; do
    if legacy_path="$(command -v "$legacy")"; then
        printf 'Legacy command still on PATH: %s\n' "$legacy_path" >&2
    fi
done
printf 'Dashboard: %q dashboard\n' "$cli"
