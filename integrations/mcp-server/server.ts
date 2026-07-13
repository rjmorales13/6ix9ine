import { execSync } from "node:child_process"
import { existsSync, readFileSync, readdirSync } from "node:fs"
import { homedir } from "node:os"
import { join, resolve } from "node:path"

const HOME = homedir()
const DEFAULT_CLI_PATH = join(HOME, ".local", "bin", "6ix9ine")
const CLAUDE_SESSIONS_DIR = join(HOME, ".claude", "sessions")
const DAEMON_SOCKET = join(HOME, "Library", "Application Support", "6ix9ine", "cli.sock")

const CLI_PATH = process.env.SIXNINE_CLI_PATH || DEFAULT_CLI_PATH
const IDLE_TIMEOUT = parseInt(process.env.SIXNINE_MCP_IDLE_TIMEOUT || "300000", 10)
const AUTO_DETECT = (process.env.SIXNINE_AUTO_DETECT || "true") === "true"

const MCP_PROTOCOL_VERSION = "2025-03-26"

interface SessionEntry {
  sessionId: string
  clientId: string
  acquiredAt: number
  lastActivity: number
}

interface ClientConnection {
  id: string
  sessions: Map<string, SessionEntry>
}

interface JsonRpcMessage {
  jsonrpc: string
  id?: string | number
  method?: string
  params?: Record<string, unknown>
  result?: unknown
  error?: { code: number; message: string; data?: unknown }
}

interface StdioTransport {
  onMessage: (msg: JsonRpcMessage) => void
  send: (msg: JsonRpcMessage) => void
  close: () => void
}

const CLIENTS = new Map<string, ClientConnection>()
let nextClientId = 1
let nextRequestId = 1

function runCli(args: string[], timeout: number = 5000): string {
  try {
    return execSync(`${CLI_PATH} ${args.join(" ")}`, {
      timeout,
      encoding: "utf-8",
      stdio: ["ignore", "pipe", "pipe"],
    }).trim()
  } catch (err) {
    throw new Error(`6ix9ine CLI error: ${(err as Error).message}`)
  }
}

function acquireSession(clientId: string, sessionId: string, reason: string): void {
  runCli(["acquire", sessionId, "--tool", "claude", "--reason", reason.slice(0, 80)])
  const client = CLIENTS.get(clientId)
  if (client) {
    client.sessions.set(sessionId, {
      sessionId,
      clientId,
      acquiredAt: Date.now(),
      lastActivity: Date.now(),
    })
  }
}

function releaseSession(clientId: string, sessionId: string): void {
  runCli(["release", sessionId])
  const client = CLIENTS.get(clientId)
  if (client) {
    client.sessions.delete(sessionId)
  }
}

function releaseAllForClient(clientId: string): number {
  const client = CLIENTS.get(clientId)
  if (!client) return 0
  const count = client.sessions.size
  for (const sessionId of client.sessions.keys()) {
    try {
      runCli(["release", sessionId])
    } catch {
      // best-effort release on disconnect
    }
  }
  client.sessions.clear()
  return count
}

function scanClaudeSessions(): Array<{ id: string; reason: string }> {
  if (!existsSync(CLAUDE_SESSIONS_DIR)) return []
  try {
    const files = readdirSync(CLAUDE_SESSIONS_DIR).filter((f) => f.endsWith(".json"))
    const sessions: Array<{ id: string; reason: string }> = []
    for (const file of files) {
      try {
        const data = JSON.parse(readFileSync(join(CLAUDE_SESSIONS_DIR, file), "utf-8"))
        if (data.status === "busy" && data.sessionId) {
          sessions.push({ id: data.sessionId, reason: data.name || "auto-detected" })
        }
      } catch {
        continue
      }
    }
    return sessions
  } catch {
    return []
  }
}

function createError(code: number, message: string, data?: unknown): JsonRpcMessage {
  return { jsonrpc: "2.0", error: { code, message, data } }
}

function createResult(id: string | number | undefined, result: unknown): JsonRpcMessage {
  return { jsonrpc: "2.0", id, result }
}

function handleInitialize(params: Record<string, unknown>): JsonRpcMessage {
  return createResult((params as { requestId?: string | number }).requestId, {
    protocolVersion: MCP_PROTOCOL_VERSION,
    capabilities: {
      tools: { listChanged: true },
      resources: { subscribe: true },
    },
    serverInfo: {
      name: "6ix9ine-mcp-server",
      version: "1.0.0",
    },
  })
}

function handleToolsList(clientId: string): JsonRpcMessage {
  const tools = [
    {
      name: "6ix9ine_acquire",
      description: "Acquire a sleep-blocking session — keeps macOS awake while the agent is working.",
      inputSchema: {
        type: "object",
        properties: {
          session_id: { type: "string", description: "Unique session identifier (UUID)" },
          reason: { type: "string", description: "Brief work description (max 80 chars)" },
        },
        required: ["session_id"],
      },
    },
    {
      name: "6ix9ine_release",
      description: "Release a previously acquired session — allows macOS sleep when no sessions remain.",
      inputSchema: {
        type: "object",
        properties: {
          session_id: { type: "string", description: "Session identifier to release" },
        },
        required: ["session_id"],
      },
    },
    {
      name: "6ix9ine_status",
      description: "Query daemon status: active sessions, holds, sleep state, lid position.",
      inputSchema: {
        type: "object",
        properties: {},
      },
    },
    {
      name: "6ix9ine_hold",
      description: "Add a timed hold — blocks sleep for a fixed duration.",
      inputSchema: {
        type: "object",
        properties: {
          reason: { type: "string", description: "Reason for the hold" },
          duration: {
            type: "string",
            description: "Duration (e.g., '30m', '2h', '45s')",
          },
        },
        required: ["reason", "duration"],
      },
    },
  ]
  return createResult(nextRequestId++, { tools })
}

function handleToolCall(clientId: string, params: Record<string, unknown>): JsonRpcMessage {
  const name = params.name as string
  const args = (params.arguments || {}) as Record<string, unknown>
  const toolCallId = params.id as string || String(nextRequestId++)

  try {
    switch (name) {
      case "6ix9ine_acquire": {
        const sessionId = args.session_id as string
        if (!sessionId) {
          return createResult(toolCallId, {
            content: [{ type: "text", text: "Error: session_id is required" }],
            isError: true,
          })
        }
        const reason = (args.reason as string) || "mcp acquire"
        acquireSession(clientId, sessionId, reason)
        return createResult(toolCallId, {
          content: [{ type: "text", text: `Session ${sessionId} acquired (sleep blocked)` }],
        })
      }

      case "6ix9ine_release": {
        const sessionId = args.session_id as string
        if (!sessionId) {
          return createResult(toolCallId, {
            content: [{ type: "text", text: "Error: session_id is required" }],
            isError: true,
          })
        }
        releaseSession(clientId, sessionId)
        return createResult(toolCallId, {
          content: [{ type: "text", text: `Session ${sessionId} released` }],
        })
      }

      case "6ix9ine_status": {
        const output = runCli(["status"])
        return createResult(toolCallId, {
          content: [{ type: "text", text: output }],
        })
      }

      case "6ix9ine_hold": {
        const reason = args.reason as string
        const duration = args.duration as string
        if (!reason || !duration) {
          return createResult(toolCallId, {
            content: [{ type: "text", text: "Error: reason and duration are required" }],
            isError: true,
          })
        }
        runCli(["hold", "--for", duration, "--reason", reason])
        return createResult(toolCallId, {
          content: [{ type: "text", text: `Hold acquired: ${reason} (${duration})` }],
        })
      }

      default:
        return createResult(toolCallId, {
          content: [{ type: "text", text: `Unknown tool: ${name}` }],
          isError: true,
        })
    }
  } catch (err) {
    return createResult(toolCallId, {
      content: [{ type: "text", text: `Error: ${(err as Error).message}` }],
      isError: true,
    })
  }
}

function handleResourcesList(): JsonRpcMessage {
  return createResult(nextRequestId++, {
    resources: [
      {
        uri: "6ix9ine://status",
        name: "Daemon Status",
        description: "Current daemon state with active sessions and sleep status",
        mimeType: "application/json",
      },
    ],
  })
}

function handleResourceRead(uri: string): JsonRpcMessage {
  if (uri === "6ix9ine://status") {
    try {
      const output = runCli(["status"])
      return createResult(nextRequestId++, {
        contents: [
          {
            uri,
            mimeType: "application/json",
            text: output,
          },
        ],
      })
    } catch (err) {
      return createError(-32603, `Failed to read resource: ${(err as Error).message}`)
    }
  }
  return createError(-32602, `Unknown resource: ${uri}`)
}

function handleNotification(clientId: string, method: string, params: Record<string, unknown>): void {
  switch (method) {
    case "notifications/initialized":
      if (AUTO_DETECT) {
        const detected = scanClaudeSessions()
        for (const session of detected) {
          acquireSession(clientId, session.id, session.reason)
        }
      }
      break

    case "notifications/cancelled":
      // no-op: MCP protocol allows servers to ignore cancellation
      break
  }
}

function handleMessage(clientId: string, msg: JsonRpcMessage): JsonRpcMessage | null {
  if (msg.jsonrpc !== "2.0") {
    return createError(-32600, "Invalid JSON-RPC: must be jsonrpc 2.0")
  }

  if (!msg.method) {
    return createError(-32600, "Invalid JSON-RPC: method required")
  }

  const method = msg.method
  const params = (msg.params || {}) as Record<string, unknown>

  if (method.startsWith("notifications/")) {
    handleNotification(clientId, method, params)
    return null
  }

  switch (method) {
    case "initialize":
      return handleInitialize(params)

    case "tools/list":
      return handleToolsList(clientId)

    case "tools/call":
      return handleToolCall(clientId, params)

    case "resources/list":
      return handleResourcesList()

    case "resources/read":
      return handleResourceRead(params.uri as string)

    case "resources/subscribe":
      return createResult(msg.id, {})

    case "resources/unsubscribe":
      return createResult(msg.id, {})

    default:
      return createError(-32601, `Method not found: ${method}`)
  }
}

function createStdioTransport(): StdioTransport {
  const transport: StdioTransport = {
    onMessage: () => {},
    send: () => {},
    close: () => {},
  }

  transport.send = (msg: JsonRpcMessage) => {
    process.stdout.write(JSON.stringify(msg) + "\n")
  }

  transport.close = () => {
    for (const [clientId] of CLIENTS) {
      releaseAllForClient(clientId)
    }
    CLIENTS.clear()
  }

  return transport
}

function createTcpTransport(port: number): void {
  const net = require("node:net")

  const server = net.createServer((socket: { on: (arg0: string, arg1: (data: Buffer) => void) => void; write: (arg0: string) => void; end: () => void }) => {
    const clientId = `tcp-${nextClientId++}`
    CLIENTS.set(clientId, { id: clientId, sessions: new Map() })
    let buffer = ""

    socket.on("data", (data: Buffer) => {
      buffer += data.toString()
      const lines = buffer.split("\n")
      buffer = lines.pop() || ""
      for (const line of lines) {
        if (!line.trim()) continue
        try {
          const msg = JSON.parse(line) as JsonRpcMessage
          const response = handleMessage(clientId, msg)
          if (response) {
            socket.write(JSON.stringify(response) + "\n")
          }
        } catch {
          const error = createError(-32700, "Parse error")
          socket.write(JSON.stringify(error) + "\n")
        }
      }
    })

    socket.on("end", () => {
      const released = releaseAllForClient(clientId)
      CLIENTS.delete(clientId)
      if (released > 0) {
        console.error(`[6ix9ine] Auto-released ${released} session(s) for disconnected client ${clientId}`)
      }
    })
  })

  server.listen(port, "localhost", () => {
    console.error(`[6ix9ine] MCP server listening on localhost:${port}`)
  })

  const shutdown = () => {
    for (const [cid] of CLIENTS) {
      releaseAllForClient(cid)
    }
    CLIENTS.clear()
    server.close()
    process.exit(0)
  }

  process.on("SIGTERM", shutdown)
  process.on("SIGINT", shutdown)
}

function start(): void {
  const port = parseInt(process.env.SIXNINE_MCP_PORT || "0", 10)

  if (!existsSync(CLI_PATH)) {
    console.error(`[6ix9ine] CLI not found at ${CLI_PATH}`)
    process.exit(1)
  }

  if (port > 0) {
    createTcpTransport(port)
  } else {
    const transport = createStdioTransport()
    const clientId = `stdio-${nextClientId++}`
    CLIENTS.set(clientId, { id: clientId, sessions: new Map() })

    let buffer = ""
    process.stdin.on("data", (data: Buffer) => {
      buffer += data.toString()
      const lines = buffer.split("\n")
      buffer = lines.pop() || ""
      for (const line of lines) {
        if (!line.trim()) continue
        try {
          const msg = JSON.parse(line) as JsonRpcMessage
          const response = handleMessage(clientId, msg)
          if (response) {
            transport.send(response)
          }
        } catch {
          const error = createError(-32700, "Parse error")
          transport.send(error)
        }
      }
    })

    process.stdin.on("end", () => {
      const released = releaseAllForClient(clientId)
      CLIENTS.delete(clientId)
      if (released > 0) {
        console.error(`[6ix9ine] Auto-released ${released} session(s) on stdin close`)
      }
    })

    process.on("SIGTERM", () => transport.close())
    process.on("SIGINT", () => transport.close())
  }

  setInterval(() => {
    const now = Date.now()
    for (const [clientId, client] of CLIENTS) {
      for (const [sessionId, entry] of client.sessions) {
        if (now - entry.lastActivity > IDLE_TIMEOUT) {
          try {
            runCli(["release", sessionId])
          } catch {
            // best-effort idle cleanup
          }
          client.sessions.delete(sessionId)
        }
      }
    }
  }, 60000)
}

start()
