# Installation Guide

6ix9ine supports three installation methods. Choose the one that fits your workflow.

---

## Option 1: Homebrew (Recommended)

```sh
brew install rjmorales13/staywoke/staywoke
staywoke setup-privileged-helper
staywoke daemon-start
staywoke install-hooks --all
staywoke dashboard
```

### Upgrading from 6ix9ine

Wait for active tasks to finish before restarting the background services.
The [Homebrew installer](../scripts/install-staywoke-homebrew.sh) handles both
the original `6ix9ine` formula and `staywoke` on the old tap. Run it from a
checkout of this repository:

```sh
bash scripts/install-staywoke-homebrew.sh
```

To update manually, add and trust the new tap's formula before updating:

```sh
brew tap rjmorales13/staywoke
brew trust --formula rjmorales13/staywoke/staywoke
brew update
```

If the original `6ix9ine` formula is still installed, run:

```sh
brew migrate --formula rjmorales13/6ix9ine/6ix9ine
brew upgrade rjmorales13/staywoke/staywoke
```

If you already had `staywoke` and Homebrew still reports it as installed from
`rjmorales13/6ix9ine`, run `brew reinstall rjmorales13/staywoke/staywoke` to
move the installed package to the new tap. Omit `brew trust` on older Homebrew
versions that lack that command.

After a package upgrade, run:

```sh
staywoke setup-privileged-helper
staywoke daemon-restart
staywoke install-hooks --all
staywoke status
```

Run the helper setup as your normal user and enter your Mac password when
prompted. Reinstalling hooks updates the managed Claude Code and OpenCode
hooks. Update your own aliases, scripts, and launchers to call `staywoke` or
`staywoke dashboard`.

The upgrade reuses the existing launchd labels, sockets, and Application Support
directory. An existing `SIXNINE_STATE_DIR` override remains supported. If you
use it, export it before restarting the daemon.

### Cutting a Release (For Maintainers)

The release workflow builds and smoke-tests both macOS architectures for PRs,
manual runs, and release tags. A pushed version tag publishes the verified
archives and checksum files. Update the separate `homebrew-staywoke` tap PR
with the published archive URLs and matching SHA-256 checksums. The application
workflow does not write to the tap.

## Option 2: npm (For Node.js Developers)

```bash
# Install globally
npm install -g @rjmorales/6ix9ine

# Set up the privileged helper (one-time, requires admin password)
6ix9ine setup-privileged-helper

# Install agent hooks
6ix9ine install-hooks --all

# Start the daemon
6ix9ine daemon-start

# Launch the TUI
t69
```

### npm Package Structure (For Maintainers)

The npm package should:
1. Include a `postinstall` script that checks for Python 3.13+ and required packages
2. Install binaries to a known location
3. Provide wrapper scripts in `node_modules/.bin/`
4. **NOT** run `setup-privileged-helper` automatically

```json
{
  "name": "@rjmorales/6ix9ine",
  "version": "1.0.0",
  "bin": {
    "6ix9ine": "./bin/6ix9ine",
    "t69": "./bin/t69"
  },
  "scripts": {
    "postinstall": "node scripts/check-python.js"
  }
}
```

---

## Option 3: Manual Installation

```bash
# Clone the repo
git clone https://github.com/rjmorales13/6ix9ine.git
cd 6ix9ine

# Run the install script
./install.sh
```

`install.sh` does **not** require `sudo` and does **not** touch root or `launchd`. It:

1. Finds a Python 3.13+ interpreter (errors out with a `brew install python@3.13` hint if none is found)
2. Creates a dedicated venv at `~/Library/Application Support/6ix9ine/venv` and installs
   `requirements.txt` into it
3. Copies `daemon.py` and its sibling modules into
   `~/Library/Application Support/6ix9ine/` (this is where the daemon actually runs from,
   per [ARCHITECTURE.md](ARCHITECTURE.md) — not the git checkout, so the checkout can move or be
   deleted without breaking a running daemon)
4. Installs `6ix9ine` and `t69` wrapper scripts into `~/.local/bin/` (each just `exec`s the venv's
   Python against `bin/cli.py` / `bin/tui.py` in your checkout — the CLI/TUI themselves are run
   from the repo, unlike the daemon)
5. Generates `~/Library/LaunchAgents/com.rjmorales.6ix9ine.daemon.plist` **on the fly** — this
   can't be a static file shipped in the repo because launchd plists can't expand `~` or `$HOME`,
   and the absolute path differs per machine
6. Prints next steps, including a `PATH` reminder if `~/.local/bin` isn't already on it

It's safe to re-run — every step is idempotent (existing venv is reused, files are just
overwritten, the plist is regenerated with the same content if nothing changed).

Root is only ever touched by the separate, explicit step below.

---

## The Privileged Helper Setup

This is the **only** step that requires root access. It installs a tiny LaunchDaemon that controls sleep.

### What It Does

```bash
6ix9ine setup-privileged-helper
```

1. Copies `helper.py` to `/Library/PrivilegedHelperTools/com.rjmorales.6ix9ine.helper`
2. Copies `com.rjmorales.6ix9ine.helper.plist` to `/Library/LaunchDaemons/`
3. Sets ownership to `root:wheel` and permissions to `755`
4. Loads the daemon with `sudo launchctl load ...`
5. Verifies the helper is running

### Why This Is Safe

- The helper is **~50 lines of Python** with a single mutating endpoint
- It only accepts connections from the verified 6ix9ine-daemon
- It auto-resets `pmset disablesleep 0` on every boot
- It logs all actions to `/var/log/6ix9ine-helper.log`
- You can inspect the source code before running: `cat bin/helper.py` (from your checkout)

### Uninstalling the Helper

```bash
6ix9ine uninstall-helper
```

This:
1. Unloads the LaunchDaemon
2. Removes the plist and helper binary
3. Resets `pmset disablesleep 0`

---

## Starting the Daemon

After installation, start the user-level daemon:

```bash
# Start
6ix9ine daemon-start

# Check status
6ix9ine daemon-status

# Stop
6ix9ine daemon-stop

# Restart
6ix9ine daemon-restart
```

The daemon auto-starts on login via its LaunchAgent plist.

---

## Upgrading

Follow [Upgrading from 6ix9ine](#upgrading-from-6ix9ine) for the formula
rename. For subsequent Stay Woke releases, run `brew upgrade staywoke`, refresh
the privileged helper with `staywoke setup-privileged-helper`, and restart the
daemon with `staywoke daemon-restart`. For a source installation, rerun
`./install.sh` from the updated checkout.

## Verifying Installation

```bash
# Check CLI works
6ix9ine --version

# Check daemon is running
6ix9ine daemon-status

# Check helper is running
6ix9ine helper-status

# Test acquire/release
6ix9ine acquire test-session --tool manual --reason "installation test"
6ix9ine status
6ix9ine release test-session
6ix9ine status
```

---

## Requirements

- **macOS 14+** (Sonoma or later)
- **Python 3.13+**
- **Admin rights** (only for `setup-privileged-helper`)

---

## Troubleshooting

### "Permission denied" when running setup-privileged-helper

You must be an admin user. The helper requires root to control system sleep.

### "Daemon not running" after install

```bash
6ix9ine daemon-start
# Or manually:
launchctl load ~/Library/LaunchAgents/com.rjmorales.6ix9ine.daemon.plist
```

### "Helper not running" after setup

```bash
sudo launchctl load /Library/LaunchDaemons/com.rjmorales.6ix9ine.helper.plist
```

### Python dependencies missing

```bash
pip3 install psutil textual
```
