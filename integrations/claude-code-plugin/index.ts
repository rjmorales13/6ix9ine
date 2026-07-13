import { acquire, release, isDaemonReachable } from "../shared/daemon-client"

interface UserPromptSubmitPayload {
  session_id: string
  prompt: string
}

interface StopPayload {
  session_id: string
}

interface PreToolUsePayload {
  session_id: string
  tool_input: {
    command: string
    run_in_background?: boolean
  }
}

let reachable = false

async function acquireSession(sessionId: string, prompt: string): Promise<void> {
  if (!sessionId) return
  try {
    await acquire(sessionId, prompt.slice(0, 80))
  } catch {
    // 6ix9ine failing must never break a Claude Code turn
  }
}

async function releaseSession(sessionId: string): Promise<void> {
  if (!sessionId) return
  try {
    await release(sessionId)
  } catch {
    // 6ix9ine failing must never break a Claude Code turn
  }
}

export const SixNinePlugin = async () => {
  reachable = isDaemonReachable()
  if (!reachable) {
    console.error("[6ix9ine] daemon not reachable — hooks will be no-ops")
  }

  return {
    async UserPromptSubmit(input: UserPromptSubmitPayload): Promise<void> {
      if (!reachable) return
      await acquireSession(input.session_id, input.prompt || "")
    },

    async Stop(input: StopPayload): Promise<void> {
      if (!reachable) return
      await releaseSession(input.session_id)
    },

    async PreToolUse(input: PreToolUsePayload): Promise<void> {
      if (!reachable) return
      const sessionId = input.session_id
      const command = input.tool_input?.command || ""
      if (!sessionId || !command) return
    },
  }
}
