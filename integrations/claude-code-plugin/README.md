# 6ix9ine — Claude Code Plugin

> Keeps macOS awake while Claude Code works, releases sleep when sessions end.

## Installation

### Prerequisites

- [6ix9ine](https://github.com/rjmorales13/6ix9ine) installed and running
- Claude Code installed

### Install

```bash
# From the 6ix9ine project root
6ix9ine install-hooks --agent claude
```

This configures Claude Code's `~/.claude/settings.json` with lifecycle hooks that communicate with the 6ix9ine daemon. The plugin auto-detects 6ix9ine installation and the daemon socket on every hook invocation.

## How It Works

| Event | Plugin Action |
|---|---|
| You submit a prompt to Claude | `6ix9ine acquire <session_id> --tool claude --reason <prompt>` — blocks sleep |
| Claude finishes its turn | `6ix9ine release <session_id>` — sleep unblocks if no other sessions |
| Bash tool runs with background flag | Wraps the command with PID tracking for process-death detection |

### Architecture

```
UserPromptSubmit ──► plugin.ts ──► 6ix9ine acquire ──► daemon ──► helper ──► pmset disablesleep 1
Stop             ──► plugin.ts ──► 6ix9ine release ──► daemon ──► helper ──► pmset disablesleep 0
```

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `SIXNINE_CLI_PATH` | `~/.local/bin/6ix9ine` | Path to 6ix9ine CLI |
| `SIXNINE_ACQUIRE_TIMEOUT` | `3000` | Acquire call timeout (ms) |
| `SIXNINE_RELEASE_TIMEOUT` | `3000` | Release call timeout (ms) |
| `SIXNINE_TRACK_TIMEOUT` | `3000` | Track call timeout (ms) |

## Safety

6ix9ine failures are **always silent** — an exception in the plugin must never block, erase, or interfere with a Claude Code session. Every handler is wrapped in `try/catch`.

## Files

| File | Purpose |
|---|---|
| `plugin.json` | Plugin manifest (name, version, capabilities) |
| `index.ts` | Main plugin implementation with all hook handlers |
| `hooks.json` | Machine-readable hook point definitions |
| `README.md` | This file |
