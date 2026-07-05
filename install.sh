#!/usr/bin/env bash
# One-command installer for 6ix9ine. Run from a checkout of the repo:
#   git clone https://github.com/rjmorales13/6ix9ine.git && cd 6ix9ine && ./install.sh
#
# This does everything: venv, deps, the root helper (will prompt for your
# password once), agent hooks, and starts the daemon. Safe to re-run --
# every step is idempotent and skips anything already done.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_SUPPORT_DIR="$HOME/Library/Application Support/6ix9ine"
VENV_DIR="$APP_SUPPORT_DIR/venv"
BIN_DIR="$HOME/.local/bin"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
DAEMON_BUNDLE_ID="com.rjmorales.6ix9ine.daemon"
DAEMON_PLIST_DST="$LAUNCH_AGENTS_DIR/${DAEMON_BUNDLE_ID}.plist"

# daemon.py's own sibling-module imports (see bin/daemon.py) -- kept in sync
# by hand since there's no packaging step yet to derive this list from.
RUNTIME_MODULES=(daemon.py daemon_commands.py ipc.py lid_monitor.py shared.py thermal_monitor.py idle_tracker.py session_registry.py)

find_python313() {
  for candidate in python3.13 /opt/homebrew/bin/python3.13 /usr/local/bin/python3.13; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

echo "==> Checking for Python 3.13+"
if ! PYTHON313="$(find_python313)"; then
  echo "error: Python 3.13+ not found on PATH." >&2
  echo "       Install it first, e.g.: brew install python@3.13" >&2
  exit 1
fi
echo "    using $PYTHON313 ($("$PYTHON313" --version 2>&1))"

echo "==> Creating runtime directory at $APP_SUPPORT_DIR"
mkdir -p "$APP_SUPPORT_DIR"

echo "==> Creating virtualenv at $VENV_DIR"
if [ ! -x "$VENV_DIR/bin/python3" ]; then
  "$PYTHON313" -m venv "$VENV_DIR"
else
  echo "    already exists, reusing"
fi

echo "==> Installing Python dependencies into the venv"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$REPO_ROOT/requirements.txt"

echo "==> Copying daemon runtime files into $APP_SUPPORT_DIR"
for module in "${RUNTIME_MODULES[@]}"; do
  cp "$REPO_ROOT/bin/$module" "$APP_SUPPORT_DIR/$module"
done

echo "==> Installing 6ix9ine and t69 commands into $BIN_DIR"
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

echo "==> Generating the daemon LaunchAgent plist"
mkdir -p "$LAUNCH_AGENTS_DIR"
# Generated fresh (not copied from plists/) because launchd plists can't
# expand ~ or \$HOME -- the venv/runtime paths above are absolute and
# specific to this machine's home directory.
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

echo "==> Setting up the privileged helper (controls sleep; asks for your password once)"
if "$BIN_DIR/6ix9ine" helper-status >/dev/null 2>&1; then
  echo "    already installed and running, skipping"
else
  "$BIN_DIR/6ix9ine" setup-privileged-helper
fi

echo "==> Installing hooks for any AI agents detected on this machine"
"$BIN_DIR/6ix9ine" install-hooks --all

echo "==> Starting the background daemon"
if "$BIN_DIR/6ix9ine" daemon-status >/dev/null 2>&1; then
  echo "    already running, skipping"
else
  "$BIN_DIR/6ix9ine" daemon-start
fi

echo ""
echo "6ix9ine is installed and running."
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    echo ""
    echo "note: $BIN_DIR is not on your PATH yet. Add this to your shell profile:"
    echo "    export PATH=\"$BIN_DIR:\$PATH\""
    ;;
esac
echo ""
echo "Run 't69' any time to open the dashboard."
