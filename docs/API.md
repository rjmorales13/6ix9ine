# CLI & API Reference

## Global Commands

### `6ix9ine --version`

Print version and component status.

```bash
$ 6ix9ine --version
6ix9ine v1.0.0
  daemon: running (pid 12345)
  helper: running (pid 67, root)
  agents: claude, opencode
```

---

## Session Management

### `6ix9ine acquire <session-key> --tool <agent> [--reason <str>] [--pid <int>]`

Acquire a sleep-blocking assertion. If this is the first active assertion, the daemon calls the helper to block sleep.

**Arguments:**
- `session-key` (required): Unique identifier for this session/turn. Use UUIDs.
- `--tool` (required): Agent name. Must be one of: `claude`, `opencode`, `codex`, `antigravity`, `manual`
- `--reason` (optional): Human-readable description of the task. Shown in TUI and lid-open summary.
- `--pid` (optional): PID of the caller's long-lived host process (e.g. OpenCode's plugin passing its own `process.pid`). The daemon resolves this pid's `create_time` server-side and uses it as a defense-in-depth cleanup path if the caller ever fails to send an explicit `release` (crash, force-quit, connection drop) -- guarded against OS PID reuse and exempt from CPU-idle pruning. Session identity/refcounting is still purely by `session-key`; omit `--pid` for callers (like Claude's hook-acquire) that don't have a stable long-lived pid to offer.

**Examples:**
```bash
6ix9ine acquire abc-123 --tool claude --reason "building project"
6ix9ine acquire def-456 --tool opencode --reason "refactoring"
```

**Returns:**
```json
{"ok": true, "status": "ACTIVE", "count": 1}
```

**Latency budget:** < 50ms

---

### `6ix9ine release <session-key>`

Release a previously acquired assertion. When the last assertion is released, sleep blocking is disabled.

**Arguments:**
- `session-key` (required): The same key passed to `acquire`.

**Examples:**
```bash
6ix9ine release abc-123
```

**Returns:**
```json
{"ok": true, "status": "IDLE", "count": 0}
```

---

### `6ix9ine hold --for <duration> --reason <str>`

Time-boxed sleep block. Useful for background tasks that outlive an agent's reply (e.g., long builds, deployments).

**Arguments:**
- `--for` (required): Duration. Format: `30m`, `2h`, `1h30m`
- `--reason` (required): Description of the hold.

**Examples:**
```bash
6ix9ine hold --for 30m --reason "deploy to production"
6ix9ine hold --for 2h --reason "training model"
```

**Returns:**
```json
{"ok": true, "hold_id": "hold-abc-123", "expires_at": 1720000000}
```

**Auto-release:** The daemon automatically releases the hold when the timer expires.

---

## Status & Introspection

### `6ix9ine status`

Print current state as JSON.

```bash
$ 6ix9ine status
```

**Output:**
```json
{
  "ok": true,
  "status": "ACTIVE",
  "count": 2,
  "active_sessions": {
    "abc-123": {
      "agent": "claude",
      "timestamp": 1720000000.0,
      "pid": 12345,
      "reason": "building project",
      "held_for": "15m 32s"
    },
    "def-456": {
      "agent": "opencode",
      "timestamp": 1720000100.0,
      "pid": 12346,
      "reason": "refactoring",
      "held_for": "13m 42s"
    }
  },
  "holds": [
    {
      "id": "hold-abc-123",
      "reason": "deploy to production",
      "expires_in": "18m 45s"
    }
  ],
  "thermal": {
    "current_temp": 62.5,
    "peak_temp": 78.2,
    "cutout_threshold": 85.0,
    "cutout_fired": false
  },
  "lid": "closed",
  "sleep_blocked": true
}
```

---

## Hook Management

### `6ix9ine install-hooks [--agent <name> | --all]`

Install 6ix9ine hooks into agent configurations.

**Options:**
- `--agent <name>`: Install for a specific agent (`claude`, `opencode`, `codex`, `antigravity`)
- `--all`: Install for all detected agents

**Examples:**
```bash
6ix9ine install-hooks --agent claude
6ix9ine install-hooks --all
```

**Behavior:**
1. Detects agent installation
2. Backs up existing config to `.bak`
3. Writes hook configuration
4. Verifies by running a test

**Returns:**
```json
{"ok": true, "installed": ["claude", "opencode"], "skipped": ["codex", "antigravity"]}
```

---

### `6ix9ine uninstall-hooks [--agent <name> | --all]`

Remove 6ix9ine hooks from agent configurations. Restores from `.bak` files.

**Examples:**
```bash
6ix9ine uninstall-hooks --agent claude
6ix9ine uninstall-hooks --all
```

---

## Daemon Control

### `6ix9ine daemon-start`

Start the user-level daemon (LaunchAgent).

```bash
6ix9ine daemon-start
```

Equivalent to:
```bash
launchctl load ~/Library/LaunchAgents/com.rjmorales.6ix9ine.daemon.plist
```

---

### `6ix9ine daemon-stop`

Stop the user-level daemon.

```bash
6ix9ine daemon-stop
```

**Important:** Stopping the daemon does **not** automatically release sleep blocking. If assertions were held, the helper may still have `disablesleep 1` active. Use `6ix9ine release --all` or `t69 --kill` first.

---

### `6ix9ine daemon-restart`

Restart the daemon. Preserves state file.

```bash
6ix9ine daemon-restart
```

---

### `6ix9ine daemon-status`

Check if daemon is running and print basic info.

```bash
$ 6ix9ine daemon-status
Daemon: running (pid 12345)
Uptime: 3h 45m
Sessions: 2 active
Last thermal: 62.5°C
```

---

## Privileged Helper

### `6ix9ine setup-privileged-helper`

One-time setup for the root helper. Requires admin password.

```bash
6ix9ine setup-privileged-helper
```

**What it does:**
1. Copies helper to `/Library/PrivilegedHelperTools/`
2. Copies plist to `/Library/LaunchDaemons/`
3. Sets ownership `root:wheel`, permissions `755`
4. Loads with `launchctl`
5. Verifies helper responds to ping

---

### `6ix9ine helper-status`

Check if privileged helper is running.

```bash
$ 6ix9ine helper-status
Helper: running (pid 67, root)
Version: 1.0.0
Sleep blocked: false
```

---

### `6ix9ine uninstall-helper`

Remove the privileged helper completely.

```bash
6ix9ine uninstall-helper
```

**What it does:**
1. Unloads LaunchDaemon
2. Removes helper binary and plist
3. Resets `pmset disablesleep 0`
4. Removes state file

---

## Emergency Controls

### `6ix9ine release --all`

Force-release ALL assertions and holds immediately.

```bash
6ix9ine release --all
```

This is the "soft kill switch" — it clears all sessions but keeps the daemon running.

---

### `t69 --kill`

The **hard kill switch**. Use this if everything is stuck or you need to restore normal sleep immediately.

```bash
t69 --kill
```

**What it does:**
1. Wipes `state.json`
2. Calls helper `set_sleep_blocked(false)`
3. Resets `pmset disablesleep 0`
4. Prints confirmation

**Use case:** Your Mac won't sleep and you don't know why. One command fixes it.

---

## TUI Dashboard (`t69`)

### `t69`

Launch the interactive Textual dashboard.

```bash
t69
```

### Keybindings

| Key | Action |
|-----|--------|
| `q` | Close TUI (daemon continues running) |
| `k` | Kill selected agent session (upper panel) |
| `x` | Purge ALL agent sessions |
| `a` | Ignore/hide selected auxiliary process (lower panel) |
| `r` | Restore hidden auxiliary processes |
| `↑/↓` or `j/k` | Navigate rows |
| `Tab` | Switch between upper/lower panels |

### Dashboard Layout

```
┌─────────────────────────────────────────────┐
│ 🌈 6ix9ine CORE - SLEEP PREVENTION REGISTRY │
│ [ ENGINE ACTIVE ] Clamshell Sleep Blocked   │
├─────────────────────────────────────────────┤
│ Session UUID │ Agent   │ Reason             │
│ abc-123      │ claude  │ building project   │
│ def-456      │ opencode│ refactoring        │
├─────────────────────────────────────────────┤
│ 📊 AUXILIARY WORKLOADS                      │
│ Process  │ PID   │ Status │ CPU  │ Memory   │
│ ollama   │ 9876  │ sleep  │ 0.0% │ 2.14 GB  │
│ dockerd  │ 5432  │ run    │ 1.2% │ 0.85 GB  │
└─────────────────────────────────────────────┘
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Invalid arguments |
| `3` | Daemon not running |
| `4` | Helper not running / not installed |
| `5` | Permission denied (need admin for helper setup) |
| `6` | Agent not detected (for hook install) |
| `7` | Session not found (for release) |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SIXNINE_STATE_DIR` | Directory for state and socket | `~/Library/Application Support/6ix9ine` |
| `SIXNINE_THERMAL_THRESHOLD` | Thermal cutout temperature (°C) | `85` |
| `SIXNINE_IDLE_TIMEOUT` | Minutes before idle process auto-release | `5` |
| `SIXNINE_SNIFFING` | Enable process sniffing fallback | `true` |
| `SIXNINE_LOG_LEVEL` | Logging verbosity (`debug`, `info`, `warn`, `error`) | `info` |
