import { createServer } from "node:net"
import { existsSync, readFileSync, readdirSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"
import { acquire, release, isDaemonReachable, daemonSocketPath } from "../shared/daemon-client"
import {
  TOOLS,
  RESOURCES,
  handleAcquire,
  handleRelease,
  handleStatus,
  handleHold,
  handleResourceRead,
  getCapabilities,
} from "./handlers"

const IDLE_TIMEOUT = parseInt(process.env.SIXNINE_MCP_IDLE_TIMEOUT || "300000", 10)
const AUTO_DETECT = (process.env.SIXNINE_AUTO_DETECT || "true") === "true"
const CLAUDE_SESSIONS_DIR = join(homedir(), ".claude", "sessions")
const STATUS_RESOURCE_URI = RESOURCES[0]?.uri ?? "6ix9ine://status"

interface SessionEntry {
  sessionId: string
  acquiredAt: number
  clientId: string
}

interface ClientState {
  id: string
  sessions: Map<string, SessionEntry>
}

export const CLIENTS = new Map<string, ClientState>()
let nextClientId = 1

export function registerClient(clientId: string): void {
  CLIENTS.set(clientId, { id: clientId, sessions: new Map() })
}

function sendJson(write: (s: string) => void, msg: Record<string, unknown>): void {
  write(JSON.stringify(msg) + "\n")
}

function rpcError(code: number, message: string, id?: string | number | null): Record<string, unknown> {
  const msg: Record<string, unknown> = { jsonrpc: "2.0", error: { code, message } }
  if (id !== undefined && id !== null) msg.id = id
  return msg
}

function rpcResult(id: string | number, result: unknown): Record<string, unknown> {
  return { jsonrpc: "2.0", id, result }
}

export function scanClaudeSessions(): Array<{ id: string; reason: string }> {
  if (!existsSync(CLAUDE_SESSIONS_DIR)) return []
  const results: Array<{ id: string; reason: string }> = []
  try {
    for (const f of readdirSync(CLAUDE_SESSIONS_DIR)) {
      if (!f.endsWith(".json")) continue
      try {
        const data = JSON.parse(readFileSync(join(CLAUDE_SESSIONS_DIR, f), "utf-8"))
        if (data.status === "busy" && data.sessionId) {
          results.push({ id: data.sessionId, reason: data.name || "auto-detected" })
        }
      } catch {
        // skip unreadable session files
      }
    }
  } catch {
    // sessions dir inaccessible
  }
  return results
}

// Dispatch a tools/call to the shared handler implementations in handlers.ts,
// then perform the client-session bookkeeping used for disconnect auto-release.
export async function handleToolCall(
  id: string | number,
  name: string,
  args: Record<string, unknown>,
  clientId: string
): Promise<Record<string, unknown>> {
  try {
    switch (name) {
      case "6ix9ine_acquire": {
        const sessionId = (args.session_id as string) || ""
        const reason = (args.reason as string) || "mcp acquire"
        const result = await handleAcquire(sessionId, reason)
        if (!result.isError && sessionId) {
          const client = CLIENTS.get(clientId)
          if (client) {
            client.sessions.set(sessionId, { sessionId, acquiredAt: Date.now(), clientId })
          }
        }
        return rpcResult(id, result)
      }

      case "6ix9ine_release": {
        const sessionId = (args.session_id as string) || ""
        const result = await handleRelease(sessionId)
        if (!result.isError && sessionId) {
          const client = CLIENTS.get(clientId)
          if (client) client.sessions.delete(sessionId)
        }
        return rpcResult(id, result)
      }

      case "6ix9ine_status":
        return rpcResult(id, await handleStatus())

      case "6ix9ine_hold":
        return rpcResult(id, await handleHold((args.duration as string) || "", (args.reason as string) || ""))

      default:
        return rpcResult(id, { content: [{ type: "text", text: `unknown tool: ${name}` }], isError: true })
    }
  } catch (err) {
    return rpcResult(id, { content: [{ type: "text", text: `internal error: ${(err as Error).message}` }], isError: true })
  }
}

export async function handleMessage(
  msg: Record<string, unknown>,
  clientId: string
): Promise<Record<string, unknown> | null> {
  if (msg.jsonrpc !== "2.0") {
    return rpcError(-32600, "invalid json-rpc: must be jsonrpc 2.0")
  }

  const method = msg.method as string | undefined
  const id = (msg.id !== undefined ? msg.id : null) as string | number | null

  if (!method) {
    return rpcError(-32600, "method required", id)
  }

  if (method.startsWith("notifications/")) {
    if (method === "notifications/initialized" && AUTO_DETECT) {
      const detected = scanClaudeSessions()
      for (const session of detected) {
        try {
          await acquire(session.id, session.reason)
          const client = CLIENTS.get(clientId)
          if (client) {
            client.sessions.set(session.id, { sessionId: session.id, acquiredAt: Date.now(), clientId })
          }
        } catch {
          // best-effort auto-detect
        }
      }
    }
    return null
  }

  if (id === null) {
    return rpcError(-32600, "request must include id", null)
  }

  switch (method) {
    case "initialize":
      return rpcResult(id, getCapabilities())
    case "tools/list":
      return rpcResult(id, { tools: TOOLS })
    case "tools/call": {
      const params = msg.params as Record<string, unknown> | undefined
      return handleToolCall(id, (params?.name as string) || "", (params?.arguments as Record<string, unknown>) || {}, clientId)
    }
    case "resources/list":
      return rpcResult(id, { resources: RESOURCES })
    case "resources/read": {
      const params = msg.params as Record<string, unknown> | undefined
      const uri = params?.uri as string
      if (uri === STATUS_RESOURCE_URI) {
        const contents = await handleResourceRead()
        return rpcResult(id, { contents: [contents] })
      }
      return rpcError(-32602, "unknown resource", id)
    }
    case "resources/subscribe":
    case "resources/unsubscribe":
      return rpcResult(id, {})
    default:
      return rpcError(-32601, `method not found: ${method}`, id)
  }
}

export function releaseClientSessions(clientId: string): number {
  const client = CLIENTS.get(clientId)
  if (!client) return 0
  const count = client.sessions.size
  for (const sid of client.sessions.keys()) {
    release(sid).catch(() => {})
  }
  client.sessions.clear()
  CLIENTS.delete(clientId)
  return count
}

export function createLineBuffer(onLine: (line: string) => void): (chunk: Buffer) => void {
  let buf = ""
  return (chunk: Buffer) => {
    buf += chunk.toString("utf-8")
    const lines = buf.split("\n")
    buf = lines.pop() || ""
    for (const line of lines) {
      if (line.trim()) onLine(line)
    }
  }
}

export function startStdio(): void {
  const clientId = `stdio-${nextClientId++}`
  registerClient(clientId)

  const feed = createLineBuffer(async (line: string) => {
    let msg: Record<string, unknown>
    try {
      msg = JSON.parse(line)
    } catch {
      sendJson((s) => process.stdout.write(s), rpcError(-32700, "parse error"))
      return
    }
    try {
      const resp = await handleMessage(msg, clientId)
      if (resp) {
        sendJson((s) => process.stdout.write(s), resp)
      }
    } catch (err) {
      sendJson((s) => process.stdout.write(s), rpcError(-32603, (err as Error).message, msg.id as string | number | null))
    }
  })

  process.stdin.on("data", feed)
  process.stdin.on("end", () => {
    const n = releaseClientSessions(clientId)
    if (n > 0) console.error(`[6ix9ine] released ${n} session(s) on stdin close`)
  })
  process.on("SIGTERM", () => process.exit(0))
  process.on("SIGINT", () => process.exit(0))
}

export function startTcp(port: number): import("node:net").Server {
  const srv = createServer((socket) => {
    const clientId = `tcp-${nextClientId++}`
    registerClient(clientId)

    const feed = createLineBuffer(async (line: string) => {
      let msg: Record<string, unknown>
      try {
        msg = JSON.parse(line)
      } catch {
        sendJson((s) => socket.write(s), rpcError(-32700, "parse error"))
        return
      }
      try {
        const resp = await handleMessage(msg, clientId)
        if (resp) {
          sendJson((s) => socket.write(s), resp)
        }
      } catch (err) {
        sendJson((s) => socket.write(s), rpcError(-32603, (err as Error).message, msg.id as string | number | null))
      }
    })

    socket.on("data", feed)
    socket.on("end", () => {
      const n = releaseClientSessions(clientId)
      if (n > 0) console.error(`[6ix9ine] released ${n} session(s) from tcp client ${clientId}`)
    })
    socket.on("error", () => {
      releaseClientSessions(clientId)
    })
  })

  srv.listen(port, "127.0.0.1", () => {
    const addr = srv.address()
    const boundPort = typeof addr === "object" && addr ? addr.port : port
    console.error(`[6ix9ine] MCP server listening on 127.0.0.1:${boundPort}`)
  })

  const shutdown = () => {
    for (const cid of CLIENTS.keys()) releaseClientSessions(cid)
    srv.close()
    process.exit(0)
  }
  process.on("SIGTERM", shutdown)
  process.on("SIGINT", shutdown)
  return srv
}

export function startIdleReaper(): ReturnType<typeof setInterval> {
  return setInterval(() => {
    const now = Date.now()
    for (const [, client] of CLIENTS) {
      for (const [sid, entry] of client.sessions) {
        if (now - entry.acquiredAt > IDLE_TIMEOUT) {
          release(sid).catch(() => {})
          client.sessions.delete(sid)
        }
      }
    }
  }, 60000)
}

export function main(): void {
  if (!isDaemonReachable()) {
    console.error(`[6ix9ine] daemon socket not found at ${daemonSocketPath()}`)
    process.exit(1)
  }

  const port = parseInt(process.env.SIXNINE_MCP_PORT || "0", 10)

  if (port > 0) {
    startTcp(port)
  } else {
    startStdio()
  }

  startIdleReaper()
}

// Only auto-run as a script (tsx server.ts), never when imported under Jest.
if (!process.env.JEST_WORKER_ID) {
  main()
}
