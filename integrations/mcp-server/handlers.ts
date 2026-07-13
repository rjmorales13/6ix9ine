import { acquire, release, status, hold } from "../shared/daemon-client"

export interface McpTool {
  name: string
  description: string
  inputSchema: Record<string, unknown>
}

export interface McpResource {
  uri: string
  name: string
  description: string
  mimeType: string
}

export interface ContentItem {
  type: string
  text: string
}

export interface ToolResult {
  content: ContentItem[]
  isError?: boolean
}

export interface ResourceContents {
  uri: string
  mimeType: string
  text: string
}

export const TOOLS: McpTool[] = [
  {
    name: "6ix9ine_acquire",
    description: "Acquire a sleep-blocking session via 6ix9ine daemon",
    inputSchema: {
      type: "object",
      properties: {
        session_id: { type: "string", description: "Unique session identifier (UUID)" },
        reason: { type: "string", description: "Work description (max 80 chars)" },
      },
      required: ["session_id"],
    },
  },
  {
    name: "6ix9ine_release",
    description: "Release a previously acquired sleep-blocking session",
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
    description: "Query 6ix9ine daemon status (sessions, holds, sleep state)",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "6ix9ine_hold",
    description: "Add a timed hold blocking sleep for a fixed duration",
    inputSchema: {
      type: "object",
      properties: {
        reason: { type: "string", description: "Reason for the hold" },
        duration: { type: "string", description: "Duration e.g. '30m', '2h', '45s'" },
      },
      required: ["reason", "duration"],
    },
  },
]

export const RESOURCES: McpResource[] = [
  {
    uri: "6ix9ine://status",
    name: "Daemon Status",
    description: "Current 6ix9ine daemon state as JSON",
    mimeType: "application/json",
  },
]

export async function handleAcquire(sessionId: string, reason: string): Promise<ToolResult> {
  if (!sessionId) {
    return { content: [{ type: "text", text: "session_id is required" }], isError: true }
  }
  const resp = await acquire(sessionId, reason || "")
  if (!resp.ok) {
    return { content: [{ type: "text", text: `daemon error: ${resp.error || "unknown"}` }], isError: true }
  }
  return { content: [{ type: "text", text: `acquired ${sessionId} (sleep blocked)` }] }
}

export async function handleRelease(sessionId: string): Promise<ToolResult> {
  if (!sessionId) {
    return { content: [{ type: "text", text: "session_id is required" }], isError: true }
  }
  const resp = await release(sessionId)
  if (!resp.ok && resp.error !== "session not found") {
    return { content: [{ type: "text", text: `daemon error: ${resp.error}` }], isError: true }
  }
  return { content: [{ type: "text", text: `released ${sessionId}` }] }
}

export async function handleStatus(): Promise<ToolResult> {
  const resp = await status()
  return { content: [{ type: "text", text: JSON.stringify(resp, null, 2) }] }
}

export async function handleHold(duration: string, reasonText: string): Promise<ToolResult> {
  if (!duration || !reasonText) {
    return { content: [{ type: "text", text: "reason and duration are required" }], isError: true }
  }
  const resp = await hold(duration, reasonText)
  if (!resp.ok) {
    return { content: [{ type: "text", text: `daemon error: ${resp.error}` }], isError: true }
  }
  return { content: [{ type: "text", text: `hold acquired: ${reasonText} (${duration})` }] }
}

export async function handleResourceRead(): Promise<ResourceContents> {
  const resp = await status()
  return {
    uri: "6ix9ine://status",
    mimeType: "application/json",
    text: JSON.stringify(resp, null, 2),
  }
}

export interface ServerCapabilities {
  protocolVersion: string
  capabilities: {
    tools: Record<string, unknown>
    resources: { subscribe: boolean }
  }
  serverInfo: {
    name: string
    version: string
  }
}

export function getCapabilities(): ServerCapabilities {
  return {
    protocolVersion: "2025-03-26",
    capabilities: {
      tools: {},
      resources: { subscribe: true },
    },
    serverInfo: {
      name: "6ix9ine-mcp-server",
      version: "1.0.0",
    },
  }
}
