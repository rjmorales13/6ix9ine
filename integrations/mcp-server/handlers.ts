import { execSync } from "node:child_process"
import { homedir } from "node:os"
import { join } from "node:path"

const HOME = homedir()
const DEFAULT_CLI_PATH = join(HOME, ".local", "bin", "6ix9ine")
const CLI_PATH = process.env.SIXNINE_CLI_PATH || DEFAULT_CLI_PATH
const CLI_TIMEOUT = parseInt(process.env.SIXNINE_CLI_TIMEOUT || "5000", 10)

export interface ToolDefinition {
  name: string
  description: string
  inputSchema: Record<string, unknown>
}

export interface ToolCallRequest {
  name: string
  arguments: Record<string, unknown>
}

export interface ToolCallResponse {
  content: Array<{ type: string; text: string }>
  isError?: boolean
}

export interface ResourceDefinition {
  uri: string
  name: string
  description: string
  mimeType: string
}

export interface ResourceContent {
  uri: string
  mimeType: string
  text: string
}

function cli(args: string[], timeout: number = CLI_TIMEOUT): string {
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

export const TOOLS: ToolDefinition[] = [
  {
    name: "6ix9ine_acquire",
    description:
      "Acquire a sleep-blocking session — keeps macOS awake while the agent is working. Call this when starting a task that should prevent sleep.",
    inputSchema: {
      type: "object",
      properties: {
        session_id: {
          type: "string",
          description: "Unique session identifier (UUID v4 recommended)",
        },
        reason: {
          type: "string",
          description: "Brief description of the work being done (max 80 characters)",
        },
      },
      required: ["session_id"],
    },
  },
  {
    name: "6ix9ine_release",
    description:
      "Release a previously acquired session. Call this when the task is complete. Sleep will unblock when all sessions are released.",
    inputSchema: {
      type: "object",
      properties: {
        session_id: {
          type: "string",
          description: "Session identifier to release (must match an acquired session)",
        },
      },
      required: ["session_id"],
    },
  },
  {
    name: "6ix9ine_status",
    description:
      "Query daemon status. Returns active sessions, held sessions, sleep state, lid position, and thermal readings.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "6ix9ine_hold",
    description:
      "Add a timed hold — blocks sleep for a fixed duration regardless of agent activity. Use for long-running background work.",
    inputSchema: {
      type: "object",
      properties: {
        reason: {
          type: "string",
          description: "Reason for the hold (e.g., 'long build', 'data sync')",
        },
        duration: {
          type: "string",
          description:
            "Duration string. Examples: '30m' (30 minutes), '2h' (2 hours), '45s' (45 seconds)",
        },
      },
      required: ["reason", "duration"],
    },
  },
]

export function handleAcquire(args: Record<string, unknown>): ToolCallResponse {
  const sessionId = args.session_id as string
  const reason = (args.reason as string) || "mcp acquire"

  if (!sessionId) {
    return {
      content: [{ type: "text", text: "Error: session_id is required" }],
      isError: true,
    }
  }

  cli(["acquire", sessionId, "--tool", "claude", "--reason", reason.slice(0, 80)])
  return {
    content: [{ type: "text", text: `✓ Session acquired: ${sessionId} (sleep blocked)` }],
  }
}

export function handleRelease(args: Record<string, unknown>): ToolCallResponse {
  const sessionId = args.session_id as string

  if (!sessionId) {
    return {
      content: [{ type: "text", text: "Error: session_id is required" }],
      isError: true,
    }
  }

  cli(["release", sessionId])
  return {
    content: [{ type: "text", text: `✓ Session released: ${sessionId}` }],
  }
}

export function handleStatus(): ToolCallResponse {
  try {
    const output = cli(["status"])
    return {
      content: [{ type: "text", text: output }],
    }
  } catch (err) {
    return {
      content: [
        {
          type: "text",
          text: `Error querying daemon: ${(err as Error).message}. Is 6ix9ine running?`,
        },
      ],
      isError: true,
    }
  }
}

export function handleHold(args: Record<string, unknown>): ToolCallResponse {
  const reason = args.reason as string
  const duration = args.duration as string

  if (!reason || !duration) {
    return {
      content: [{ type: "text", text: "Error: reason and duration are required" }],
      isError: true,
    }
  }

  cli(["hold", "--for", duration, "--reason", reason])
  return {
    content: [{ type: "text", text: `✓ Hold acquired: "${reason}" for ${duration}` }],
  }
}

export const RESOURCES: ResourceDefinition[] = [
  {
    uri: "6ix9ine://status",
    name: "Daemon Status",
    description: "Current daemon state with active sessions and sleep status",
    mimeType: "application/json",
  },
]

export function handleResourceRead(uri: string): ResourceContent | null {
  if (uri === "6ix9ine://status") {
    try {
      const output = cli(["status"])
      return {
        uri,
        mimeType: "application/json",
        text: output,
      }
    } catch {
      return {
        uri,
        mimeType: "application/json",
        text: JSON.stringify({ error: "daemon unreachable", status: "unknown" }),
      }
    }
  }
  return null
}

export interface ServerCapabilities {
  protocolVersion: string
  capabilities: {
    tools: { listChanged: boolean }
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
      tools: { listChanged: true },
      resources: { subscribe: true },
    },
    serverInfo: {
      name: "6ix9ine-mcp-server",
      version: "1.0.0",
    },
  }
}
