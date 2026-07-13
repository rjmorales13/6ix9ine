# MCP Server Integration — Architecture & Design

> **Work Order:** OpusWO-001 — FableWO-001
> **Branch:** `feat/opus-mcp-design`
> **Status:** Design Review

---

## Overview

The 6ix9ine MCP Server exposes the 6ix9ine daemon's session management capabilities through the [Model Context Protocol (MCP)](https://modelcontextprotocol.io). This allows any MCP-compatible agent — Claude Code, Aider, Cline, Continue, and others — to acquire/release sleep-blocking sessions without native hook support.

MCP is an open standard for AI-agent tool integration. By implementing an MCP server, 6ix9ine becomes available to the entire MCP ecosystem with a single integration point.

---

## Architecture

```
┌──────────────────────────────┐
│     MCP Client (Agent)         │
│  ┌──────────────────────────┐ │
│  │ Claude Code              │ │
│  │ Aider                    │ │
│  │ Cline                    │ │
│  │ Continue                 │ │
│  │ Any MCP-compatible agent │ │
│  └──────────┬───────────────┘ │
│             │ stdio / TCP       │
└─────────────┼──────────────────┘
              │
              ▼
┌──────────────────────────────┐
│    6ix9ine MCP Server         │
│  ┌──────────────────────────┐ │
│  │ Protocol Handler          │ │
│  │  ├─ initialize            │ │
│  │  ├─ tools/list            │ │
│  │  ├─ tools/call            │ │
│  │  ├─ resources/list        │ │
│  │  └─ notifications        │ │
│  └──────────┬───────────────┘ │
│             │ UDS               │
└─────────────┼──────────────────┘
              │
              ▼
┌──────────────────────────────┐
│    6ix9ine Daemon             │
│  SessionRegistry (refcount)   │
└──────────────────────────────┘
```

### MCP Protocol Version

The server implements MCP protocol version **2025-03-26** (latest stable).

---

## MCP Tools

The server exposes the following tools:

### `6ix9ine_acquire`

Acquire a sleep-blocking session.

```json
{
  "name": "6ix9ine_acquire",
  "description": "Acquire a sleep-blocking session — keeps macOS awake while the agent is working.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "session_id": {
        "type": "string",
        "description": "Unique session identifier (UUID)"
      },
      "reason": {
        "type": "string",
        "description": "Brief description of the work (max 80 chars)"
      }
    },
    "required": ["session_id"]
  }
}
```

### `6ix9ine_release`

Release a sleep-blocking session.

```json
{
  "name": "6ix9ine_release",
  "description": "Release a previously acquired session — allows macOS sleep when no sessions remain.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "session_id": {
        "type": "string",
        "description": "Session identifier to release"
      }
    },
    "required": ["session_id"]
  }
}
```

### `6ix9ine_status`

Query daemon status.

```json
{
  "name": "6ix9ine_status",
  "description": "Query the current daemon status: active sessions, holds, sleep state, lid position.",
  "inputSchema": {
    "type": "object",
    "properties": {}
  }
}
```

### `6ix9ine_hold`

Add a timed hold (sleep blocked for a fixed duration).

```json
{
  "name": "6ix9ine_hold",
  "description": "Add a timed hold — blocks sleep for a fixed duration regardless of agent activity.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "reason": {
        "type": "string",
        "description": "Reason for the hold"
      },
      "duration": {
        "type": "string",
        "description": "Duration (e.g., '30m', '2h', '45s')"
      }
    },
    "required": ["reason", "duration"]
  }
}
```

---

## Protocol Handlers

### Initialize

```typescript
// Server responds to initialize with capabilities
{
  "protocolVersion": "2025-03-26",
  "capabilities": {
    "tools": {
      "listChanged": true
    },
    "resources": {
      "subscribe": true
    }
  },
  "serverInfo": {
    "name": "6ix9ine-mcp-server",
    "version": "1.0.0"
  }
}
```

### Tools List

Returns all exposed tools with their schemas. Tools are static (no dynamic registration needed for this server).

### Tools Call

Dispatches to the appropriate handler, which calls the 6ix9ine daemon via Unix socket (same LineJSON protocol used by the CLI).

### Resources

The server exposes a single read-only resource:

| URI | Description |
|---|---|
| `6ix9ine://status` | Current daemon state (JSON) |

---

## Session Lifecycle

### Auto-Detection

The MCP server can optionally auto-detect Claude Code agent sessions by scanning `~/.claude/sessions/` for JSON files with `status: "busy"`. When detected, the server acquires a session on behalf of the agent.

This enables sleep-blocking for agents that don't explicitly call the MCP tools, as long as they share the same filesystem.

### Multi-Client Support

The server supports multiple concurrent MCP clients. Each client connection gets its own session tracking context:

```
Client A (Claude Code) ──► acquire session_1 ──► Daemon refcount: 1
Client B (Aider)       ──► acquire session_2 ──► Daemon refcount: 2
Client A releases      ──► release session_1 ──► Daemon refcount: 1
Client B releases      ──► release session_2 ──► Daemon refcount: 0 → sleep
```

Client sessions are tracked by MCP connection ID + tool call correlation ID. If a client disconnects without releasing, the server auto-releases any sessions held by that client (graceful cleanup).

### Cleanup

| Scenario | Behavior |
|---|---|
| Client disconnects gracefully | Release all sessions held by that client |
| Client crashes | Connection closed → server detects → auto-release |
| Server receives SIGTERM | Release all sessions, flush, shutdown |
| Idle timeout (configurable) | Release stale sessions > timeout |

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SIXNINE_CLI_PATH` | `~/.local/bin/6ix9ine` | Path to 6ix9ine CLI |
| `SIXNINE_MCP_HOST` | `localhost` | MCP server bind host |
| `SIXNINE_MCP_PORT` | `0` | MCP server port (0 = stdio mode) |
| `SIXNINE_MCP_IDLE_TIMEOUT` | `300000` | Idle session timeout (ms) |
| `SIXNINE_AUTO_DETECT` | `true` | Enable agent session auto-detection |

### Transport

The server supports two transport modes:

1. **stdio** (default): Standard input/output transport — works with Claude Code's native MCP client integration. The agent launches the MCP server as a subprocess and communicates via stdin/stdout.

2. **TCP** (optional): Network socket transport — useful for multi-agent scenarios or when running the server in a separate terminal. Bind to `localhost` only (not exposed to the network).

---

## Integration with Existing Architecture

The MCP server is additive — it does not replace or modify any existing 6ix9ine component.

```
Before MCP:
  hooks/claude.py ──► 6ix9ine CLI ──► daemon ──► helper

With MCP:
  hooks/claude.py ──► 6ix9ine CLI ──► daemon ──► helper
  MCP client       ──► MCP server  ──► 6ix9ine CLI ──► daemon ──► helper
```

Both paths converge at the daemon. The MCP server simply provides an alternative entry point for MCP-compatible agents.

---

## Testing

| Test | Description |
|---|---|
| MCP initialization | Verify protocol handshake succeeds |
| Tool discovery | Verify `tools/list` returns all 4 tools |
| Acquire via MCP | Call `6ix9ine_acquire`, verify daemon registers session |
| Release via MCP | Call `6ix9ine_release`, verify daemon deregisters |
| Concurrent clients | Two MCP clients acquire/release independently |
| Client disconnect cleanup | Kill client, verify auto-release triggered |
| Error handling | Call acquire with empty session_id, verify error response |
| Status query | Call `6ix9ine_status`, verify response shape |
