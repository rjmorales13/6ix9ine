# Architecture

## Design Philosophy

6ix9ine follows a **three-tier privilege model** inspired by macOS security best practices. The privileged surface is intentionally minimal, auditable, and isolated. All policy logic lives in unprivileged user space.

```
┌──────────────────────────────────────────────────────────────┐
│  t69  (Textual TUI, optional, runs on demand)                │
│  • Status dashboard, process tables, manual controls           │
│  • Pure view layer — can quit/restart without affecting state    │
└─────────────────────────────┬────────────────────────────────┘
                              │ Unix Domain Socket
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  6ix9ine-daemon  (LaunchAgent, runs as user, always-on)      │
│  • Reference-counted assertion registry                        │
│  • Process watchers (psutil + kqueue NOTE_EXIT)                │
│  • Thermal monitor (SMC / powermetrics)                        │
│  • Lid-state monitor (IORegistry)                            │
│  • Lid-close chime + lid-open summary                        │
│  • Idle release (dead or CPU-idle assertions auto-drop)      │
│  • CLI socket at ~/Library/Application Support/6ix9ine/cli.sock│
└─────────────────────────────┬────────────────────────────────┘
                              │ XPC (Mach Service)
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  6ix9ine-helper  (LaunchDaemon, runs as root)                  │
│  • The ONLY component that touches sleep-blocking APIs         │
│  • Single mutating endpoint: set_sleep_blocked(bool)           │
│  • Read-only introspection: get_version(), get_state()         │
│  • Verifies caller code-signing requirement                    │
│  • Auto-resets pmset disablesleep 0 on boot / respawn          │
└──────────────────────────────────────────────────────────────┘
```

## Why Three Tiers?

### The Sleep Problem
On modern macOS, `caffeinate` and public `IOPMAssertion` APIs **do not** prevent clamshell (lid-closed) sleep. The only reliable way to block clamshell sleep is `pmset disablesleep 1`, which **requires root**.

If we ran `sudo pmset` from the CLI on every agent turn, users would type their password constantly. Worse, if the process crashes, `disablesleep 1` leaks forever.

### The Solution
1. **Helper** (root, tiny, permanent): Installed once via `SMAppService` or manual `launchctl`. Exposes `set_sleep_blocked(bool)`. Auto-resets on boot.
2. **Daemon** (user, always-on): Holds all policy. Refcounts, thermal cutouts, idle release, lid monitoring. Talks to helper via XPC.
3. **CLI / TUI** (user, on-demand): Thin clients. No root. No policy. Just talk to the daemon socket.

## Component Breakdown

### 1. 6ix9ine-helper (LaunchDaemon)

**Language:** Python (or Swift if ported later)
**Path:** `/Library/PrivilegedHelperTools/com.rjmorales.6ix9ine.helper`
**Plist:** `/Library/LaunchDaemons/com.rjmorales.6ix9ine.helper.plist`

**Responsibilities:**
- Listen on XPC Mach service `com.rjmorales.6ix9ine.helper`
- Accept `set_sleep_blocked(true/false)` from verified daemon only
- Execute `pmset disablesleep 1` or `pmset disablesleep 0`
- On startup, always reset to `disablesleep 0` (safety)
- Log all state changes to `/var/log/6ix9ine-helper.log`

**Security:**
- Verify calling process code signature matches daemon bundle ID
- Reject any caller that is not the registered 6ix9ine-daemon
- No file system access beyond `pmset` and logging

### 2. 6ix9ine-daemon (LaunchAgent)

**Language:** Python 3.13+
**Path:** `~/Library/Application Support/6ix9ine/daemon.py`
**Plist:** `~/Library/LaunchAgents/com.rjmorales.6ix9ine.daemon.plist`

**Responsibilities:**
- Maintain Unix domain socket at `~/Library/Application Support/6ix9ine/cli.sock`
- Maintain state file at `~/Library/Application Support/6ix9ine/state.json`
- Reference-count assertions by `session_key`:
  ```json
  {
    "status": "ACTIVE",
    "active_sessions": {
      "uuid-1": {"agent": "claude", "timestamp": 1720000000, "pid": 12345},
      "uuid-2": {"agent": "opencode", "timestamp": 1720000000, "pid": 12346}
    }
  }
  ```
- When count > 0: call helper `set_sleep_blocked(true)`
- When count == 0: call helper `set_sleep_blocked(false)`
- **Process watcher:** Monitor PIDs of held assertions. If a PID dies, auto-release its assertion.
- **Thermal monitor:** Read CPU/skin temp via `powermetrics` or SMC. If threshold crossed while lid closed, force-release all assertions.
- **Idle release:** If an assertion-owning process is CPU-idle for N minutes, drop it.
- **Lid monitor:** Watch `IORegistry` for lid state. On close, play chime if assertions held. On open, generate summary notification.

**Threading Model:**
- Use `asyncio` for socket server and timers
- Use `threading` for psutil process iteration and thermal polling
- Protect shared state with `asyncio.Lock`

### 3. CLI Client

**Language:** Python 3.13+
**Entry point:** `6ix9ine` command

**Subcommands:**
- `acquire <session-key> --tool <agent> [--reason <str>]`
- `release <session-key>`
- `hold --for <duration> --reason <str>`
- `status` (JSON output)
- `install-hooks [--agent <name> | --all]`
- `uninstall-hooks [--agent <name> | --all]`
- `setup-privileged-helper` (one-time install)
- `daemon-start`, `daemon-stop`, `daemon-restart`

**Latency Budget:**
- `acquire` / `release` must round-trip in < 50ms
- Use static lookups (no heavy imports in hot path)
- Use thin socket protocol (not full HTTP/JSON in hot path)

### 4. TUI Dashboard (t69)

**Language:** Python 3.13+ with Textual
**Entry point:** `t69` command

**Features:**
- Upper panel: Active sleep-blocking sessions (DataTable)
- Lower panel: Auxiliary background workloads (Ollama, Docker, etc. via psutil)
- Keybindings:
  - `q` — Close TUI (daemon continues running)
  - `k` — Kill selected agent session
  - `x` — Purge all agent sessions
  - `a` — Ignore/hide selected auxiliary process
  - `r` — Restore hidden auxiliary processes
- `--kill` flag: Emergency kill switch. Wipes state, resets pmset, exits.

**Current visual direction:**
- Full-page `status view` layout
- Dark terminal base with restrained, meaningful color per row
- Distinct session identities with emoji labels for `claude`, `opencode`, and `codex`
- Held-time colors based on duration thresholds
- Sleep state shown as either `BLOCKED` or available via `😴` / `💤`

**Menu Bar Option (Optional):**
If user enables it, a `rumps`-based menu bar icon shows:
- Current status (Active/Idle)
- Assertion count
- Click to open TUI
- Right-click to force release all

## IPC Protocol

### Daemon ↔ Helper (XPC)

```python
# Simplified XPC message format
{
    "method": "set_sleep_blocked",
    "params": {"blocked": true},
    "auth": {
        "caller_pid": 12345,
        "caller_bundle_id": "com.rjmorales.6ix9ine.daemon"
    }
}
```

Helper verifies:
1. Caller PID matches registered daemon PID
2. Caller code signature bundle ID matches
3. Then executes `pmset disablesleep 1` or `0`

### CLI ↔ Daemon (Unix Domain Socket)

```python
# Thin wire protocol (newline-delimited JSON)
{"cmd": "ACQUIRE", "session": "uuid-1", "tool": "claude", "reason": "building"}
{"cmd": "RELEASE", "session": "uuid-1"}
{"cmd": "STATUS"}
{"cmd": "KILL_ALL"}
```

Daemon responds with single-line JSON:
```json
{"ok": true, "status": "ACTIVE", "count": 2}
```

## State File Schema

**Path:** `~/Library/Application Support/6ix9ine/state.json`

```json
{
  "version": 1,
  "status": "ACTIVE",
  "active_sessions": {
    "session-uuid-1": {
      "agent": "claude",
      "timestamp": 1720000000.0,
      "pid": 12345,
      "reason": "long build"
    }
  },
  "last_thermal_reading": 65.2,
  "thermal_cutout_fired": false,
  "lid_state": "open"
}
```

## File Layout (Installed)

```
/usr/local/bin/6ix9ine              -> symlink to CLI
/usr/local/bin/t69                  -> symlink to TUI
/opt/6ix9ine/
  ├── bin/
  │   ├── cli.py
  │   ├── tui.py
  │   ├── daemon.py
  │   ├── helper.py
  │   └── shared.py
  ├── hooks/
  │   ├── claude.py
  │   ├── opencode.py
  │   ├── codex.py          # placeholder
  │   └── antigravity.py    # placeholder
  └── plists/
      ├── com.rjmorales.6ix9ine.daemon.plist
      └── com.rjmorales.6ix9ine.helper.plist

~/Library/Application Support/6ix9ine/
  ├── state.json
  ├── cli.sock
  └── filter.json           # TUI ignored processes

/Library/PrivilegedHelperTools/
  └── com.rjmorales.6ix9ine.helper

/Library/LaunchDaemons/
  └── com.rjmorales.6ix9ine.helper.plist

~/Library/LaunchAgents/
  └── com.rjmorales.6ix9ine.daemon.plist
```

## Thermal Safety

If CPU or skin temperature exceeds threshold (default: 85°C) while lid is closed:
1. Daemon force-releases ALL assertions
2. Daemon calls helper `set_sleep_blocked(false)`
3. Sets `thermal_cutout_fired: true` in state
4. On lid-open, summary notification includes thermal warning

This prevents a bag-bound Mac from cooking itself.

## Idle Release

If an assertion-owning process:
- Dies (PID no longer exists)
- Has CPU usage < 1% for > 5 minutes

The daemon auto-releases its assertion. This prevents zombie sessions from keeping the Mac awake forever.

## Lid Events

**Lid Close:**
- If assertions held: play short chime (AudioToolbox or `afplay`)
- Screen is off, so no visual notification

**Lid Open:**
- Generate macOS notification (NotificationCenter or `osascript`)
- Show: duration held, peak temperature, agents that ran, whether thermal cutout fired
