# 6ix9ine — MCP Server

> Expose 6ix9ine's sleep-blocking daemon through the Model Context Protocol. Any MCP-compatible agent can acquire/release sleep sessions.

## Quick Start

```bash
# stdio mode (default) — for Claude Code's MCP client
npx tsx server.ts

# TCP mode — for multi-agent setups
SIXNINE_MCP_PORT=9100 npx tsx server.ts
```

## MCP Tools

| Tool | Description |
|---|---|
| `6ix9ine_acquire` | Acquire a sleep-blocking session |
| `6ix9ine_release` | Release a previously acquired session |
| `6ix9ine_status` | Query daemon status (sessions, sleep state, lid, thermal) |
| `6ix9ine_hold` | Add a timed hold for a fixed duration |

## Resources

| URI | Description |
|---|---|
| `6ix9ine://status` | Current daemon state as JSON |

## Configuration

| Variable | Default | Description |
|---|---|---|
| `SIXNINE_CLI_PATH` | `~/.local/bin/6ix9ine` | Path to 6ix9ine CLI |
| `SIXNINE_MCP_PORT` | `0` | TCP port (0 = stdio mode) |
| `SIXNINE_MCP_IDLE_TIMEOUT` | `300000` | Idle session timeout (ms) |
| `SIXNINE_AUTO_DETECT` | `true` | Auto-detect Claude sessions on connect |
| `SIXNINE_CLI_TIMEOUT` | `5000` | CLI command timeout (ms) |

## Claude Code Configuration

Add to your `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "6ix9ine": {
      "command": "npx",
      "args": ["tsx", "/path/to/6ix9ine/integrations/mcp-server/server.ts"]
    }
  }
}
```

## Architecture

```
MCP Client ──► stdio/TCP ──► MCP Server ──► 6ix9ine CLI ──► Daemon ──► Helper ──► pmset
```

The MCP server translates MCP tool calls into 6ix9ine CLI commands. It is stateless with respect to the daemon — all session state is maintained by the daemon's SessionRegistry.

### Multi-Client Support

The server tracks which sessions belong to which MCP client. If a client disconnects (gracefully or by crash), all its sessions are auto-released:
- **Graceful disconnect:** stdin `end` event → release all
- **Crash:** TCP connection close → release all
- **Idle timeout:** Sessions with no activity for > 5 minutes are auto-released

## Files

| File | Purpose |
|---|---|
| `server.ts` | Main MCP server with stdio/TCP transports |
| `handlers.ts` | Tool and resource handlers (pure functions) |
| `config.json` | MCP manifest (tools, resources, capabilities) |
| `README.md` | This file |

## Testing

```bash
# Test stdio mode (send initial handshake)
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | npx tsx server.ts

# Test TCP mode
SIXNINE_MCP_PORT=9100 npx tsx server.ts &
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | nc localhost 9100
```
