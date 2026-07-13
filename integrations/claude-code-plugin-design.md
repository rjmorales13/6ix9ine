# Claude Code Plugin — Architecture & Design

> **Work Order:** OpusWO-001 — FableWO-001
> **Branch:** `feat/opus-claude-integration-design`
> **Status:** Design Review

---

## Overview

The 6ix9ine Claude Code Plugin bridges Claude Code sessions to the 6ix9ine sleep-blocking daemon. It hooks into Claude Code's lifecycle events — prompt submit, stop, and tool use — and translates them into `acquire`/`release` calls against the 6ix9ine daemon's Unix socket.

Unlike the existing Python-based hook in `hooks/claude.py` (which modifies `~/.claude/settings.json` with inline Python snippets), this plugin is a structured, installable TypeScript package with formal manifest, typed hook definitions, and proper lifecycle management.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Claude Code Process                       │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              settings.json hooks                       │ │
│  │  UserPromptSubmit ──► plugin.ts ──► 6ix9ine acquire │ │
│  │  Stop             ──► plugin.ts ──► 6ix9ine release  │ │
│  │  PreToolUse       ──► plugin.ts ──► 6ix9ine track    │ │
│  └──────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│              Unix Domain Socket (cli.sock)                   │
│                           │                                 │
│                           ▼                                 │
│                   6ix9ine Daemon                             │
│              SessionRegistry (refcount)                     │
└──────────────────────────────────────────────────────────┘
```

### Hook Points

| Hook Event | Trigger | Action | Payload |
|---|---|---|---|
| `UserPromptSubmit` | User sends a prompt | `acquire <session_id> --tool claude --reason <prompt[:80]>` | `session_id`, `prompt` |
| `Stop` | Claude finishes a turn | `release <session_id>` | `session_id` |
| `PreToolUse` (Bash) | Before a Bash tool runs | `track <session_id> --tool claude --pids <pid>` | `session_id`, `tool_input.command` |

### Plugin API Surface

```
Plugin {
  name: string              // "6ix9ine"
  version: string           // "1.0.0"
  hooks: HookDefinition[]   // registered hook points
  onActivate?: () => void   // called when plugin loads
  onDeactivate?: () => void  // called when plugin unloads
}

HookDefinition {
  event: string             // lifecycle event name
  handler: (payload: any) => Promise<void>
  matcher?: string          // optional tool name filter
}
```

### Request Lifecycle

```
User submits prompt
  │
  ▼
UserPromptSubmit fires
  │
  ▼
plugin.ts handler parses stdin JSON
  │
  ├─ session_id extracted
  ├─ prompt truncated to 80 chars
  │
  ▼
execSync(`6ix9ine acquire <session_id> --tool claude --reason <prompt>`)
  │
  ├─ Daemon increments refcount (via UDS)
  ├─ If refcount goes 0→1: helper blocks sleep via pmset
  │
  ▼
Claude processes the turn
  │
  ▼
Stop fires
  │
  ▼
plugin.ts handler parses stdin JSON
  │
  ▼
execSync(`6ix9ine release <session_id>`)
  │
  ├─ Daemon decrements refcount
  ├─ If refcount goes 1→0: helper unblocks sleep
```

---

## Error Handling

**Golden rule:** 6ix9ine failures must NEVER block the Claude Code session.

| Failure Scenario | Behavior |
|---|---|
| 6ix9ine CLI not found | `try/catch` swallows — no error propagated |
| Daemon socket unreachable | Timeout after 3s — silent catch |
| Daemon returns error | Logged to stderr — never exit code 2 |
| JSON parse failure on stdin | `try/catch` with empty defaults |

All handlers wrap their body in `try/catch` and always exit 0. Exit code 2 is `BLOCKING` for both `UserPromptSubmit` (erases the prompt) and `Stop` (prevents Claude from stopping).

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SIXNINE_CLI_PATH` | `~/.local/bin/6ix9ine` | Path to 6ix9ine CLI wrapper |
| `SIXNINE_ACQUIRE_TIMEOUT` | `3000` | Timeout (ms) for acquire call |
| `SIXNINE_RELEASE_TIMEOUT` | `3000` | Timeout (ms) for release call |
| `SIXNINE_TRACK_TIMEOUT` | `3000` | Timeout (ms) for track call |

### Hook Timeouts

Each hook invocation has an independent timeout. If the daemon is unresponsive, the hook fails silently within the budget rather than blocking the agent indefinitely.

### Detection Logic

On activation, the plugin:
1. Checks `~/.claude/settings.json` exists → indicates Claude Code is installed
2. Checks `~/.local/bin/6ix9ine` exists → indicates 6ix9ine is installed
3. Checks daemon socket at `~/Library/Application Support/6ix9ine/cli.sock` → daemon reachable
4. Logs a warning (non-blocking) if any check fails

---

## File Structure

```
integrations/claude-code-plugin/
├── plugin.json           # Plugin manifest (name, version, hooks)
├── index.ts              # Main plugin implementation
├── hooks.json            # Hook point definitions (machine-readable)
└── README.md             # Installation & usage documentation
```

---

## Security

- Plugin runs in-process within Claude Code — no elevated privileges
- Acquire/release commands go through 6ix9ine CLI → daemon → helper chain
- No secrets, no network calls, no filesystem access beyond config
- Socket authentication is PID-based (kernel-verified peer PID on macOS)

---

## Integration with 6ix9ine Daemon

The plugin communicates with the daemon through the 6ix9ine CLI (`~/.local/bin/6ix9ine`), not directly via socket. This provides:
- Single entry point for all daemon interactions
- Consistent argument parsing and error handling
- Established timeout and retry behavior
- No dependency on IPC protocol internals

The daemon's `SessionRegistry` handles reference counting, PID tracking, and background command process monitoring — the plugin only needs to fire acquire/release/track at the right moments.

---

## Testing

| Test | Description |
|---|---|
| Plugin manifest validation | `plugin.json` schema matches Claude Code expectations |
| Hook registration | Verify hooks.json entries match index.ts exports |
| Acquire on prompt submit | Simulate UserPromptSubmit stdin, verify acquire called |
| Release on stop | Simulate Stop stdin, verify release called |
| Error swallowing | Verify no exception propagates through handler |
| Timeout handling | Verify handler completes within 3s even if daemon unreachable |
| Cleanup on deactivation | Verify no zombie processes on plugin unload |
