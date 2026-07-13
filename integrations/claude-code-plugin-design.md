# Claude Code Plugin — Architecture & Design

> **Work Order:** OpusWO-001
> **Status:** Implemented

## Architecture

```
UserPromptSubmit ──► plugin.ts ──► UDS ──► daemon ──► helper ──► pmset
Stop             ──► plugin.ts ──► UDS ──► daemon ──► helper ──► pmset
```

## Communication

- **Direct Unix domain socket** — no CLI, no shell, no command injection
- Messages are newline-delimited JSON matching the daemon's native IPC protocol
- Socket at `~/Library/Application Support/6ix9ine/cli.sock`

## Security

- All user-controlled input (`session_id`, `reason`) is transmitted as JSON
  fields over a Unix socket — never interpolated into a shell command
- Failures are always silent — never blocks a Claude Code turn
- Exit code 2 is blocking for both UserPromptSubmit and Stop

## Installation

The `install.ts` script modifies `~/.claude/settings.json` to add Python-based
lifecycle hooks (same approach as `hooks/claude.py`). Hooks run the 6ix9ine CLI
(safe because arguments are passed as an array via `subprocess.run`, not as a
shell string).

## Files

| File | Purpose |
|------|---------|
| `plugin.json` | Plugin manifest |
| `index.ts` | Plugin implementation with async hook handlers |
| `install.ts` | Install/uninstall hooks in Claude Code settings |
| `hooks.json` | Hook point definitions |
| `package.json` | Dependencies and scripts |
| `__tests__/plugin.test.ts` | Unit tests |

## Testing

- 14 automated Jest tests covering all handlers, error paths, and security
- Tests verify daemon unreachable, empty inputs, and error swallowing
- No manual shell-script tests needed
