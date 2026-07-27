# Installation Guide

6ix9ine supports three installation methods. Choose the one that fits your workflow.

---

## Option 1: Homebrew (Recommended)

```bash
# Add the tap
brew tap rjmorales13/6ix9ine

# Install
brew install 6ix9ine

# Set up the privileged helper (one-time, requires admin password)
6ix9ine setup-privileged-helper

# Install agent hooks
6ix9ine install-hooks --all

# Start the daemon
6ix9ine daemon-start

# Launch the TUI
t69
```

### Cutting a Release (For Maintainers)

`.github/workflows/release.yml` triggers on a pushed `v*.*.*` tag, builds both arches, and
publishes a GitHub Release — that part works correctly. **Its final "Update Homebrew formula"
step has a known, unfixed bug**: the job's `actions/checkout` doesn't specify a `repository:`, so
`git push origin main` at the end pushes to *this* repo's own copy of `Formula/6ix9ine.rb`
(harmless, but not what anyone reads) instead of the real tap, `rjmorales13/homebrew-6ix9ine` — a
separate GitHub repo that `brew tap`/`brew upgrade` actually reads from. The workflow reports
green either way, because it did successfully push to *a* repo.

Until that's fixed, every release needs a manual follow-up after the workflow finishes:

```bash
# Get the real checksums from the just-published release
gh release download vX.Y.Z --repo rjmorales13/6ix9ine --pattern "*.sha256"

# Edit $(brew --repo rjmorales13/6ix9ine)/Formula/6ix9ine.rb by hand: version, both
# on_arm/on_intel urls, and both sha256 values -- mirror exactly what the workflow's
# own (misdirected) sed/regex step does, see release.yml's "Update Homebrew formula" step
cd "$(brew --repo rjmorales13/6ix9ine)"
git add Formula/6ix9ine.rb && git commit -m "Update formula to vX.Y.Z" && git push origin main
```

Before running `brew upgrade` against a fresh release, it's worth downloading and running the raw
binary standalone first (`gh release download`, extract, `xattr -d com.apple.quarantine`, run
directly) to confirm the artifact itself is good — this isolates "is the binary actually broken"
from "did something in Homebrew/the local environment go wrong," which otherwise look identical
from the crash you'd see.

### Homebrew Formula Structure (For Maintainers)

The Homebrew formula should:
1. Install Python 3.13+ dependency
2. Install `psutil` and `textual` Python packages
3. Copy `bin/` to `/opt/6ix9ine/`
4. Symlink `6ix9ine` and `t69` to `/usr/local/bin/`
5. Copy `plists/` to `/opt/6ix9ine/plists/`
6. **NOT** run `setup-privileged-helper` automatically (user must do this explicitly for security)

```ruby
# Formula template (for reference)
class SixNine < Formula
  desc "Keep your Mac awake only while AI agents are working"
  homepage "https://github.com/rjmorales13/6ix9ine"
  url "https://github.com/rjmorales13/6ix9ine/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "..."
  license "MIT"

  depends_on "python@3.13"
  depends_on "psutil" => :python
  depends_on "textual" => :python

  def install
    prefix.install "bin", "hooks", "plists"
    bin.install_symlink prefix/"bin/cli.py" => "6ix9ine"
    bin.install_symlink prefix/"bin/tui.py" => "t69"
  end

  def post_install
    ohai "Run '6ix9ine setup-privileged-helper' to complete installation"
  end
end
```

---

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

`brew upgrade 6ix9ine` (or the npm/manual equivalent) only replaces the files on disk — it does
**not** restart anything already running, and doesn't touch config generated by a previous
version. After upgrading, run all three of these, in order, to actually pick up the new version:

```bash
# 1. Restart the daemon so it's running the new binary, not the old one still in memory
6ix9ine daemon-start

# 2. Re-register the root-privileged helper (its LaunchDaemon plist points at the
#    versioned Cellar path, e.g. /opt/homebrew/Cellar/6ix9ine/1.0.4/, which no longer
#    exists once the Cellar entry rotates to the new version). Requires admin password.
6ix9ine setup-privileged-helper

# 3. Regenerate any installed agent hooks/plugins from the current template
6ix9ine install-hooks --all
```

Skipping step 2 leaves the daemon unable to reach the helper at all — `set_sleep_blocked` calls
fail silently, and `6ix9ine status` will report `sleep_blocked: false` even with active sessions,
with no error surfaced anywhere but the daemon's own logs. Skipping step 3 means any already-fixed
bug in a hook template (e.g. Case study 6's timeout fix) silently does not apply — the plugin file
on disk only changes when `install-hooks` actually rewrites it; the CLI binary being newer doesn't
regenerate it for you.

Also note: any agent process already running when you upgrade (e.g. an open OpenCode session)
loaded its hook/plugin at its own startup and won't see a regenerated one until it's restarted —
this applies per-session, not per-machine.

---

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
