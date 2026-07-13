import { connect, Socket } from "node:net"
import { existsSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"

const DAEMON_SOCKET_PATH = join(
  homedir(),
  "Library", "Application Support", "6ix9ine", "cli.sock"
)

export interface DaemonResponse {
  ok: boolean
  status?: string
  count?: number
  error?: string
  [key: string]: unknown
}

export function daemonSocketPath(): string {
  return process.env.SIXNINE_DAEMON_SOCKET || DAEMON_SOCKET_PATH
}

export function isDaemonReachable(): boolean {
  return existsSync(daemonSocketPath())
}

export function sendCommand(payload: Record<string, unknown>, timeoutMs = 5000): Promise<DaemonResponse> {
  return new Promise((resolve, reject) => {
    const sockPath = daemonSocketPath()
    const sock: Socket = connect(sockPath, () => {
      const body = JSON.stringify(payload) + "\n"
      sock.write(body, "utf-8")
    })

    const timer = setTimeout(() => {
      sock.destroy()
      reject(new Error("daemon socket timeout"))
    }, timeoutMs)

    let buf = ""
    sock.on("data", (chunk: Buffer) => {
      buf += chunk.toString("utf-8")
      const nl = buf.indexOf("\n")
      if (nl !== -1) {
        clearTimeout(timer)
        sock.end()
        const line = buf.slice(0, nl)
        try {
          resolve(JSON.parse(line) as DaemonResponse)
        } catch {
          reject(new Error(`invalid JSON response: ${line}`))
        }
      }
    })

    sock.on("error", (err: Error) => {
      clearTimeout(timer)
      reject(new Error(`daemon socket error: ${err.message}`))
    })

    sock.on("end", () => {
      clearTimeout(timer)
      if (!buf) {
        reject(new Error("daemon socket closed without response"))
      }
    })
  })
}

export function acquire(sessionId: string, reason: string, timeoutMs = 5000): Promise<DaemonResponse> {
  return sendCommand(
    { cmd: "ACQUIRE", session: sessionId, tool: "claude", reason: reason.slice(0, 80) },
    timeoutMs
  )
}

export function release(sessionId: string, timeoutMs = 5000): Promise<DaemonResponse> {
  return sendCommand({ cmd: "RELEASE", session: sessionId }, timeoutMs)
}

export function status(timeoutMs = 5000): Promise<DaemonResponse> {
  return sendCommand({ cmd: "STATUS" }, timeoutMs)
}

export function hold(duration: string, reason: string, timeoutMs = 5000): Promise<DaemonResponse> {
  return sendCommand({ cmd: "HOLD", for: duration, reason }, timeoutMs)
}

export function killAll(timeoutMs = 5000): Promise<DaemonResponse> {
  return sendCommand({ cmd: "KILL_ALL" }, timeoutMs)
}
