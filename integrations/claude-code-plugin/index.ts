import { execSync } from "node:child_process"
import { existsSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"

const HOME = homedir()
const DEFAULT_CLI_PATH = join(HOME, ".local", "bin", "6ix9ine")
const DAEMON_SOCKET = join(HOME, "Library", "Application Support", "6ix9ine", "cli.sock")
const CLAUDE_CONFIG = join(HOME, ".claude", "settings.json")

const CLI_PATH = process.env.SIXNINE_CLI_PATH || DEFAULT_CLI_PATH
const ACQUIRE_TIMEOUT = parseInt(process.env.SIXNINE_ACQUIRE_TIMEOUT || "3000", 10)
const RELEASE_TIMEOUT = parseInt(process.env.SIXNINE_RELEASE_TIMEOUT || "3000", 10)
const TRACK_TIMEOUT = parseInt(process.env.SIXNINE_TRACK_TIMEOUT || "3000", 10)

interface UserPromptSubmitPayload {
  session_id: string
  prompt: string
  hook_event_name: string
}

interface StopPayload {
  session_id: string
  hook_event_name: string
}

interface PreToolUsePayload {
  session_id: string
  tool_input: {
    command: string
    run_in_background?: boolean
  }
  hook_event_name: string
}

interface EventPayload {
  event: {
    type: string
    properties?: Record<string, unknown>
  }
}

function isInstalled(): boolean {
  return existsSync(CLI_PATH) && existsSync(DAEMON_SOCKET)
}

function acquire(sessionId: string, reason: string): void {
  if (!sessionId) return
  try {
    const truncated = reason.slice(0, 80)
    execSync(
      `${CLI_PATH} acquire ${sessionId} --tool claude --reason ${JSON.stringify(truncated)}`,
      { timeout: ACQUIRE_TIMEOUT, stdio: "ignore" }
    )
  } catch {
    // 6ix9ine failing must never break a Claude Code turn
  }
}

function release(sessionId: string): void {
  if (!sessionId) return
  try {
    execSync(`${CLI_PATH} release ${sessionId}`, {
      timeout: RELEASE_TIMEOUT,
      stdio: "ignore",
    })
  } catch {
    // 6ix9ine failing must never break a Claude Code turn
  }
}

function track(sessionId: string, pids: number[]): void {
  if (!sessionId || pids.length === 0) return
  try {
    execSync(
      `${CLI_PATH} track ${sessionId} --tool claude --pids ${pids.join(" ")}`,
      { timeout: TRACK_TIMEOUT, stdio: "ignore" }
    )
  } catch {
    // 6ix9ine failing must never break a Claude Code turn
  }
}

function wrapBashCommand(sessionId: string, command: string, runInBackground: boolean): string {
  const parts: string[] = []

  if (runInBackground) {
    parts.push(`${CLI_PATH} track ${sessionId} --tool claude --pids $$ >/dev/null 2>&1`)
  }

  parts.push(command)

  const releaseHook = [
    `__69_rc=$?`,
    `__69_pids=$(jobs -p)`,
    `[ -n "$__69_pids" ] && ${CLI_PATH} track ${sessionId} --tool claude --pids $__69_pids >/dev/null 2>&1`,
    `exit $__69_rc`,
  ].join("; ")

  parts.push(releaseHook)

  return parts.join("; ")
}

export const SixNinePlugin = async () => {
  const installed = isInstalled()
  if (!installed) {
    console.error("[6ix9ine] Claude Code plugin: 6ix9ine not detected — hooks will be no-ops")
  }

  return {
    "UserPromptSubmit": async (input: UserPromptSubmitPayload) => {
      if (!installed) return
      acquire(input.session_id, input.prompt || "")
    },

    "Stop": async (input: StopPayload) => {
      if (!installed) return
      release(input.session_id)
    },

    "PreToolUse": async (input: PreToolUsePayload) => {
      if (!installed) return
      const sessionId = input.session_id
      const command = input.tool_input?.command || ""
      const runInBackground = input.tool_input?.run_in_background || false
      if (!sessionId || !command) return

      input.tool_input.command = wrapBashCommand(sessionId, command, runInBackground)
    },

    "event": async (input: EventPayload) => {
      if (!installed) return
      if (input.event?.type === "session.idle") {
        const sessionId = input.event.properties?.sessionID as string | undefined
        if (sessionId) {
          release(sessionId)
        }
      }
    },
  }
}
