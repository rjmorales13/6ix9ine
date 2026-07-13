# MCP Server Integration — Architecture & Design

> **Work Order:** OpusWO-001
> **Status:** Implemented

## Architecture

```
MCP Client ──► stdio/TCP ──► MCP Server ──► UDS ──► daemon ──► helper ──► pmset
```

## Communication

- **Direct Unix domain socket** to 6ix9ine daemon — no CLI, no shell
- Messages are newline-delimited JSON using the existing IPC protocol:
  `{"cmd":"ACQUIRE","session":"<uuid>","tool":"claude","reason":"..."}`

## Protocol Compliance

The server implements MCP protocol version **2025-03-26**:

- Correct JSON-RPC 2.0 `id` propagation in all responses
- Proper `initialize` handshake with capabilities declaration
- Notification handling (`notifications/initialized`)
- Standard error codes (`-32700`, `-32600`, `-32601`, `-32602`, `-32603`)

## Security

- No `execSync` or shell invocation in the daemon communication path
- All user input flows as JSON fields over Unix socket — no injection
- TCP server binds to `127.0.0.1` only

## Tools

| Tool | Required |
|------|----------|
| `6ix9ine_acquire` | `session_id` |
| `6ix9ine_release` | `session_id` |
| `6ix9ine_status` | — |
| `6ix9ine_hold` | `reason`, `duration` |

## Files

| File | Purpose |
|------|---------|
| `server.ts` | MCP server with stdio/TCP transports |
| `handlers.ts` | Pure tool/resource handler functions |
| `config.json` | MCP manifest |
| `package.json` | Dependencies and scripts |
| `__tests__/harness.test.ts` | Unit tests |

## Testing

- 13 automated Jest tests covering all tools, handlers, and error cases
- Daemon client is fully mocked for deterministic testing
- Tests verify protocol compliance, input validation, and error propagation
