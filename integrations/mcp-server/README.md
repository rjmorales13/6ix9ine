# 6ix9ine MCP Server

Exposes 6ix9ine's sleep-blocking daemon through the Model Context Protocol.
Any MCP-compatible agent (Claude Code, Aider, Cline, Continue) can acquire
and release sleep sessions.

## Quick Start

```bash
npm install
npm start                          # stdio mode (default)
SIXNINE_MCP_PORT=9100 npm start    # TCP mode
```

## Tools

| Tool | Description |
|------|-------------|
| `6ix9ine_acquire` | Acquire a sleep-blocking session |
| `6ix9ine_release` | Release a previously acquired session |
| `6ix9ine_status`  | Query daemon status |
| `6ix9ine_hold`    | Block sleep for a fixed duration |

## Claude Code Configuration

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "6ix9ine": {
      "command": "npx",
      "args": ["tsx", "/absolute/path/to/server.ts"]
    }
  }
}
```

## Security

- All daemon communication is via Unix domain socket — no shell execution,
  no command injection
- No hardcoded paths or secrets
- Socket authentication is PID-based (kernel-verified peer PID on macOS)

## Files

| File | Purpose |
|------|---------|
| `server.ts` | MCP server with stdio/TCP transports |
| `handlers.ts` | Pure tool/resource handler functions |
| `config.json` | MCP manifest |
| `package.json` | Dependencies and scripts |
