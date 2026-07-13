import { readFileSync, writeFileSync, existsSync, copyFileSync } from "node:fs"
import { execSync } from "node:child_process"
import { homedir } from "node:os"
import { join } from "node:path"
import { daemonSocketPath, isDaemonReachable } from "../shared/daemon-client"

const CLAUDE_CONFIG_DIR = join(homedir(), ".claude")
const DEFAULT_CLAUDE_SETTINGS = join(CLAUDE_CONFIG_DIR, "settings.json")

// Common install locations for python3, tried in order after the
// SIXNINE_PYTHON override and `command -v python3`.
const PYTHON_FALLBACK_PATHS = [
  "/opt/homebrew/bin/python3",
  "/usr/local/bin/python3",
  "/usr/bin/python3",
]

const ACQUIRE_CODE = [
  `import json, subprocess, sys`,
  `try:`,
  `    data = json.load(sys.stdin)`,
  `    sid = data.get('session_id') or ''`,
  `    rsn = (data.get('prompt') or '')[:80]`,
  `    if sid:`,
  `        subprocess.run(['6ix9ine', 'acquire', sid, '--tool', 'claude', '--reason', rsn], timeout=3)`,
  `except Exception:`,
  `    pass`,
].join("\n")

const RELEASE_CODE = [
  `import json, subprocess, sys`,
  `try:`,
  `    data = json.load(sys.stdin)`,
  `    sid = data.get('session_id') or ''`,
  `    if sid:`,
  `        subprocess.run(['6ix9ine', 'release', sid], timeout=3)`,
  `except Exception:`,
  `    pass`,
].join("\n")

/**
 * Resolve an absolute path to a python3 interpreter.
 *
 * Order of resolution:
 *   1. SIXNINE_PYTHON environment override (must point at an existing file)
 *   2. `command -v python3` on PATH
 *   3. Well-known install locations
 *
 * Throws a clear error if none is found — callers must not silently fall back
 * to the Node.js binary (`process.execPath`), which cannot execute Python.
 */
export function resolvePythonPath(): string {
  const override = process.env.SIXNINE_PYTHON
  if (override) {
    if (existsSync(override)) return override
    throw new Error(
      `[6ix9ine] SIXNINE_PYTHON is set to "${override}" but that path does not exist`
    )
  }

  try {
    const found = execSync("command -v python3", {
      encoding: "utf-8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim()
    if (found && existsSync(found)) return found
  } catch {
    // command -v failed or python3 not on PATH — fall through to known paths
  }

  for (const candidate of PYTHON_FALLBACK_PATHS) {
    if (existsSync(candidate)) return candidate
  }

  throw new Error(
    "[6ix9ine] could not locate python3. Set SIXNINE_PYTHON to your python3 binary."
  )
}

type HookEntry = { type: string; command: string; args: string[] }
type HookGroup = { hooks: HookEntry[] }

function hasOurHook(settings: Record<string, unknown>, event: string, code: string): boolean {
  const hooks = settings.hooks as Record<string, unknown[]> | undefined
  if (!hooks) return false
  const groups = hooks[event]
  if (!groups) return false
  for (const group of groups) {
    const hookList = (group as Record<string, unknown>).hooks as Record<string, unknown>[] | undefined
    if (!hookList) continue
    for (const h of hookList) {
      if (h.type === "command" && JSON.stringify(h.args) === JSON.stringify(["-c", code])) {
        return true
      }
    }
  }
  return false
}

function makeGroup(code: string, python: string): HookGroup {
  return {
    hooks: [{ type: "command", command: python, args: ["-c", code] }],
  }
}

export function install(settingsPath: string = DEFAULT_CLAUDE_SETTINGS): boolean {
  if (!existsSync(settingsPath)) {
    console.error("[6ix9ine] Claude Code settings.json not found at", settingsPath)
    return false
  }

  const python = resolvePythonPath()

  const backupPath = settingsPath + ".bak"
  if (!existsSync(backupPath)) {
    copyFileSync(settingsPath, backupPath)
  }

  const raw = readFileSync(settingsPath, "utf-8")
  const settings = JSON.parse(raw) as Record<string, unknown>
  const hooks = (settings.hooks as Record<string, HookGroup[]>) || {}
  settings.hooks = hooks

  if (!hasOurHook(settings, "UserPromptSubmit", ACQUIRE_CODE)) {
    hooks.UserPromptSubmit = hooks.UserPromptSubmit || []
    hooks.UserPromptSubmit.push(makeGroup(ACQUIRE_CODE, python))
  }

  if (!hasOurHook(settings, "Stop", RELEASE_CODE)) {
    hooks.Stop = hooks.Stop || []
    hooks.Stop.push(makeGroup(RELEASE_CODE, python))
  }

  writeFileSync(settingsPath, JSON.stringify(settings, null, 2))
  console.error("[6ix9ine] hooks installed in", settingsPath)
  return true
}

export function uninstall(settingsPath: string = DEFAULT_CLAUDE_SETTINGS): boolean {
  if (!existsSync(settingsPath)) return true

  const raw = readFileSync(settingsPath, "utf-8")
  const settings = JSON.parse(raw) as Record<string, unknown>
  const hooks = settings.hooks as Record<string, HookGroup[]> | undefined
  if (!hooks) return true

  for (const event of ["UserPromptSubmit", "Stop"] as const) {
    const code = event === "UserPromptSubmit" ? ACQUIRE_CODE : RELEASE_CODE
    if (hooks[event]) {
      hooks[event] = hooks[event].filter((group) => {
        const hookList = group.hooks
        if (!hookList) return true
        return !hookList.some(
          (h) => h.type === "command" && JSON.stringify(h.args) === JSON.stringify(["-c", code])
        )
      })
      if (hooks[event].length === 0) delete hooks[event]
    }
  }

  writeFileSync(settingsPath, JSON.stringify(settings, null, 2))
  console.error("[6ix9ine] hooks removed from", settingsPath)
  return true
}

export function main(settingsPath?: string): void {
  const isUninstall = process.argv.includes("--uninstall")

  if (!isUninstall) {
    if (!isDaemonReachable()) {
      console.error("[6ix9ine] daemon socket not found at", daemonSocketPath())
      console.error("[6ix9ine] is 6ix9ine running? hooks will install but will be no-ops until daemon starts")
    }
    install(settingsPath)
  } else {
    uninstall(settingsPath)
  }
}

// Only auto-run when executed as a script (tsx install.ts), never when imported
// under Jest — tests call install()/uninstall()/main() against a temp file.
if (!process.env.JEST_WORKER_ID) {
  main()
}

export { ACQUIRE_CODE, RELEASE_CODE }
