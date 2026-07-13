#!/usr/bin/env bash
# Optimized build script for 6ix9ine.
# Builds the CLI, TUI, daemon, and helper binaries as standalone executables.
set -euo pipefail

BOLD=$'\033[1m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
RED=$'\033[0;31m'
NC=$'\033[0m'

log()   { printf " ${GREEN}*${NC}  ${BOLD}$1${NC}\n"; }
warn()  { printf " ${YELLOW}!${NC}  $1\n"; }
error() { printf " ${RED}x${NC}  ${BOLD}$1${NC}\n" >&2; exit 1; }

# Determine version
VERSION=${1:-""}
if [ -z "$VERSION" ]; then
    VERSION=$(grep -E '^VERSION = ' bin/shared.py | cut -d '"' -f 2)
    log "No version specified, extracted v${VERSION} from bin/shared.py"
fi

if [ "$(uname)" != "Darwin" ]; then
    error "6ix9ine only supports building on macOS."
fi

# Find python3.13
PYTHON_BIN=""
for cmd in .venv313/bin/python3 python3.13 /opt/homebrew/bin/python3.13; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON_BIN="$cmd"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    error "Python 3.13 is required but was not found."
fi

# Create venv if not already inside a valid .venv313
if [[ "$PYTHON_BIN" != *".venv313"* ]]; then
    log "Creating virtual environment .venv313..."
    "$PYTHON_BIN" -m venv .venv313
    .venv313/bin/pip install --upgrade pip
    .venv313/bin/pip install pyinstaller psutil textual
    PYTHON_BIN=".venv313/bin/python3"
fi

# Clean previous builds
log "Cleaning previous build artifacts..."
rm -rf build dist *.spec

# Inject version into shared.py
log "Injecting version v${VERSION} into bin/shared.py..."
"$PYTHON_BIN" -c "import re, pathlib; p = pathlib.Path('bin/shared.py'); c = p.read_text(); p.write_text(re.sub(r'VERSION = \"[^\"]+\"', 'VERSION = \"' + '$VERSION' + '\"', c))"

# Detect universal2 compatibility
ARCH_FLAGS=""
log "Detecting architecture build capabilities..."
if "$PYTHON_BIN" -c "import sys; sys.exit(0 if 'universal2' in sys.version or 'fat' in sys.version else 1)" 2>/dev/null; then
    log "Universal2 Python detected, building universal2 binaries..."
    ARCH_FLAGS="--target-architecture universal2"
else
    warn "Host Python is not universal2. Building native architecture binary ($(uname -m))."
    ARCH_FLAGS=""
fi

# Build binaries
log "Building binaries with PyInstaller..."
for script in cli tui daemon helper; do
    name="6ix9ine"
    entry="bin/cli.py"
    if [ "$script" = "tui" ]; then
        name="t69"
        entry="bin/tui.py"
    elif [ "$script" = "daemon" ]; then
        name="com.rjmorales.6ix9ine.daemon"
        entry="bin/daemon.py"
    elif [ "$script" = "helper" ]; then
        name="com.rjmorales.6ix9ine.helper"
        entry="bin/helper.py"
    fi

    log "Building $name..."
    # We use --strip to apply symbol stripping to the bootloader and libraries
    .venv313/bin/pyinstaller --onefile --strip --clean $ARCH_FLAGS --name "$name" "$entry"
done

# Revert version injection so git is clean
log "Reverting changes to bin/shared.py..."
git checkout bin/shared.py

# Create release package
log "Packaging build..."
RELEASE_DIR="dist/release"
mkdir -p "$RELEASE_DIR"
cp dist/6ix9ine "$RELEASE_DIR/"
cp dist/t69 "$RELEASE_DIR/"
cp dist/com.rjmorales.6ix9ine.daemon "$RELEASE_DIR/"
cp dist/com.rjmorales.6ix9ine.helper "$RELEASE_DIR/"
cp -r docs/man "$RELEASE_DIR/man"
cp plists/com.rjmorales.6ix9ine.helper.plist "$RELEASE_DIR/"

TARBALL="dist/6ix9ine-v${VERSION}.tar.gz"
tar -czf "$TARBALL" -C "$RELEASE_DIR" 6ix9ine t69 com.rjmorales.6ix9ine.daemon com.rjmorales.6ix9ine.helper man com.rjmorales.6ix9ine.helper.plist
rm -rf "$RELEASE_DIR"

# Compute SHA256 hash
log "Computing SHA256 hash..."
shasum -a 256 "$TARBALL" > "${TARBALL}.sha256"
SHA_HASH=$(cut -d ' ' -f 1 "${TARBALL}.sha256")
log "SHA256: ${SHA_HASH}"

log "Build completed successfully! Tarball: $TARBALL"
printf "\nUse the following hash for the Homebrew formula:\n${SHA_HASH}\n\n"
