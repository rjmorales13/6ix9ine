# 6ix9ine — Claude Code Plugin

Keeps macOS awake while Claude works, releases sleep when sessions end.

## Installation

```bash
npm install
npm run install:plugin
```

This modifies `~/.claude/settings.json` to add lifecycle hooks that
communicate with the 6ix9ine daemon via Unix domain socket.

## How It Works

| Event | Action |
|-------|--------|
| You submit a prompt | `acquire <session_id>` — daemon blocks sleep |
| Claude finishes | `release <session_id>` — daemon unblocks sleep if count=0 |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SIXNINE_DAEMON_SOCKET` | `~/Library/Application Support/6ix9ine/cli.sock` | Daemon socket path |

## Security

- All communication uses Unix domain sockets (no shell execution)
- No command injection vector
- No secrets, no network calls
- All failures are silent — never blocks a Claude Code session

## Files

| File | Purpose |
|------|---------|
| `plugin.json` | Plugin manifest |
| `index.ts` | Plugin implementation with hook handlers |
| `install.ts` | Install/uninstall hooks in Claude Code settings |
| `hooks.json` | Hook definitions |
| `package.json` | Dependencies and scripts |
