#!/usr/bin/env bash
# One-command installer for 6ix9ine.
#
#   git clone https://github.com/rjmorales13/6ix9ine.git && cd 6ix9ine && ./install.sh
#
# Safe to re-run — every step is idempotent.
set -euo pipefail

BOLD=$'\033[1m'
GREEN=$'\033[0;32m'
CYAN=$'\033[0;36m'
YELLOW=$'\033[1;33m'
RED=$'\033[0;31m'
NC=$'\033[0m'
DIM=$'\033[2m'

step()  { printf " ${CYAN}⚙${NC}  ${BOLD}$1${NC}\n"; }
ok()    { printf " ${GREEN}✓${NC}  $1\n"; }
warn()  { printf " ${YELLOW}⚠${NC}  $1\n"; }
fail()  { printf " ${RED}✗${NC}  ${BOLD}$1${NC}\n" >&2; exit 1; }
detail(){ printf "     ${DIM}$1${NC}\n"; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_SUPPORT_DIR="$HOME/Library/Application Support/6ix9ine"
VENV_DIR="$APP_SUPPORT_DIR/venv"
BIN_DIR="$HOME/.local/bin"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
DAEMON_BUNDLE_ID="com.rjmorales.6ix9ine.daemon"
DAEMON_PLIST_DST="$LAUNCH_AGENTS_DIR/${DAEMON_BUNDLE_ID}.plist"
RUNTIME_MODULES=(daemon.py daemon_commands.py ipc.py lid_monitor.py shared.py thermal_monitor.py idle_tracker.py session_registry.py)

# ── header ──────────────────────────────────────────────────────────────

cat <<EOF

  ${BOLD}6ix9ine${NC} ${DIM}— the snitch that rats on sleep${NC}
  ${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}

EOF

# ── 1. Python ──────────────────────────────────────────────────────────

step "Finding Python 3.13+"

find_python313() {
  for candidate in python3.13 /opt/homebrew/bin/python3.13 /usr/local/bin/python3.13; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

PYTHON313="$(find_python313)" || fail "Python 3.13+ not found.\n     Install it first: ${BOLD}brew install python@3.13${NC}"
PYVER="$("$PYTHON313" --version 2>&1)"
detail "$PYVER · $PYTHON313"
ok "$PYVER"

# ── 2. Runtime directory ───────────────────────────────────────────────

step "Preparing runtime directory"
mkdir -p "$APP_SUPPORT_DIR"
ok "$APP_SUPPORT_DIR"

# ── 3. Virtualenv ──────────────────────────────────────────────────────

step "Creating virtualenv"
if [ ! -x "$VENV_DIR/bin/python3" ]; then
  "$PYTHON313" -m venv "$VENV_DIR"
  ok "virtualenv created at $VENV_DIR"
else
  detail "already exists, reusing"
  ok "virtualenv ready"
fi

# ── 4. Dependencies ────────────────────────────────────────────────────

step "Installing Python dependencies"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$REPO_ROOT/requirements.txt"
ok "dependencies installed"

# ── 5. Runtime copy ────────────────────────────────────────────────────

step "Copying daemon runtime files"
for module in "${RUNTIME_MODULES[@]}"; do
  cp "$REPO_ROOT/bin/$module" "$APP_SUPPORT_DIR/$module"
done
detail "${#RUNTIME_MODULES[@]} modules copied"
ok "runtime files ready"

# ── 6. CLI wrappers ────────────────────────────────────────────────────

step "Installing CLI wrappers → $BIN_DIR"
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/6ix9ine" <<EOF
#!/bin/sh
exec "$VENV_DIR/bin/python3" "$REPO_ROOT/bin/cli.py" "\$@"
EOF
chmod 755 "$BIN_DIR/6ix9ine"

cat > "$BIN_DIR/t69" <<EOF
#!/bin/sh
exec "$VENV_DIR/bin/python3" "$REPO_ROOT/bin/tui.py" "\$@"
EOF
chmod 755 "$BIN_DIR/t69"
ok "6ix9ine and t69 installed"

# ── 7. LaunchAgent plist ───────────────────────────────────────────────

step "Generating LaunchAgent plist"
mkdir -p "$LAUNCH_AGENTS_DIR"
cat > "$DAEMON_PLIST_DST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>$DAEMON_BUNDLE_ID</string>
	<key>ProgramArguments</key>
	<array>
		<string>$VENV_DIR/bin/python3</string>
		<string>$APP_SUPPORT_DIR/daemon.py</string>
	</array>
	<key>WorkingDirectory</key>
	<string>$APP_SUPPORT_DIR</string>
	<key>RunAtLoad</key>
	<true/>
	<key>KeepAlive</key>
	<true/>
	<key>ThrottleInterval</key>
	<integer>10</integer>
	<key>StandardOutPath</key>
	<string>$APP_SUPPORT_DIR/daemon.log</string>
	<key>StandardErrorPath</key>
	<string>$APP_SUPPORT_DIR/daemon.err.log</string>
</dict>
</plist>
EOF
ok "LaunchAgent plist generated"

# ── 8. Privileged helper ───────────────────────────────────────────────

step "Setting up privileged helper"
if "$BIN_DIR/6ix9ine" helper-status >/dev/null 2>&1; then
  detail "already installed and running, skipping"
else
  "$BIN_DIR/6ix9ine" setup-privileged-helper
  sleep 1
fi
ok "privileged helper ready"

# ── 9. Hooks ───────────────────────────────────────────────────────────

step "Installing agent hooks"
HOOK_OUTPUT="$("$BIN_DIR/6ix9ine" install-hooks --all 2>&1)"
INSTALLED="$(echo "$HOOK_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(' '.join(d.get('installed',[])))" 2>/dev/null || true)"
if [ -n "$INSTALLED" ]; then
  detail "hooks installed for: $INSTALLED"
fi
SKIPPED="$(echo "$HOOK_OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(' '.join(d.get('skipped',[])))" 2>/dev/null || true)"
FAILED_ITEMS="$(echo "$HOOK_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for k, v in d.get('failed', {}).items():
    # shorten the pending-research message
    print(k.replace('codex', 'Codex CLI').replace('antigravity', 'Antigravity CLI'))
" 2>/dev/null || true)"
if [ -n "$FAILED_ITEMS" ]; then
  while IFS= read -r line; do
    detail "$line — hook integration pending research"
  done <<< "$FAILED_ITEMS"
fi
ok "hooks configured"

# ── 10. Daemon ─────────────────────────────────────────────────────────

step "Starting background daemon"
if "$BIN_DIR/6ix9ine" daemon-status >/dev/null 2>&1; then
  detail "already running, skipping"
else
  "$BIN_DIR/6ix9ine" daemon-start
  sleep 1
fi
ok "daemon running"

# ── PATH reminder ──────────────────────────────────────────────────────

PATH_MSG=""
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    PATH_MSG="yes"
    warn "$BIN_DIR not on PATH"
    detail "Add this to your shell profile:"
    detail "  ${BOLD}export PATH=\"\$PATH:$BIN_DIR\"${NC}"
    ;;
esac

# ── Done ───────────────────────────────────────────────────────────────

echo ""
printf " ${GREEN}✓${NC}  ${BOLD}6ix9ine installed and running${NC}\n\n"

# ── Launch dashboard ───────────────────────────────────────────────────

if [ -x "$BIN_DIR/t69" ]; then
  # Try Terminal.app first, then iTerm2
  if osascript >/dev/null 2>&1 <<'AS'
tell application "Terminal"
  set installWin to front window
  do script "t69"
  delay 0.5
  close installWin
end tell
AS
  then
    detail "open ${BOLD}t69${NC} in a new Terminal window"
  elif osascript >/dev/null 2>&1 <<'AS'
tell application "iTerm2"
  set newWin to (create window with default profile)
  tell current session of newWin to write text "t69"
  delay 0.5
  close (every window whose id is not (id of newWin))
end tell
AS
  then
    detail "open ${BOLD}t69${NC} in a new iTerm2 window"
  else
    printf " ${YELLOW}⚠${NC}  run ${BOLD}t69${NC} to open the dashboard\n"
  fi
fi

exit 0
