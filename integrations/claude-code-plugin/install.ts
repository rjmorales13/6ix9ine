import { readFileSync, writeFileSync, existsSync, copyFileSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"
import { daemonSocketPath, isDaemonReachable } from "../shared/daemon-client"

const CLAUDE_CONFIG_DIR = join(homedir(), ".claude")
const CLAUDE_SETTINGS = join(CLAUDE_CONFIG_DIR, "settings.json")

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

function makeGroup(code: string): Record<string, unknown> {
  const python = process.execPath || "/usr/bin/python3"
  return {
    hooks: [
      { type: "command", command: python, args: ["-c", code] },
    ],
  }
}

export function install(): boolean {
  if (!existsSync(CLAUDE_SETTINGS)) {
    console.error("[6ix9ine] Claude Code settings.json not found at", CLAUDE_SETTINGS)
    return false
  }

  const backupPath = CLAUDE_SETTINGS + ".bak"
  if (!existsSync(backupPath)) {
    copyFileSync(CLAUDE_SETTINGS, backupPath)
  }

  const raw = readFileSync(CLAUDE_SETTINGS, "utf-8")
  const settings = JSON.parse(raw) as Record<string, unknown>
  const hooks = (settings.hooks as Record<string, unknown[]>) || {}
  settings.hooks = hooks

  if (!hasOurHook(settings, "UserPromptSubmit", ACQUIRE_CODE)) {
    hooks.UserPromptSubmit = hooks.UserPromptSubmit || []
    hooks.UserPromptSubmit.push(makeGroup(ACQUIRE_CODE))
  }

  if (!hasOurHook(settings, "Stop", RELEASE_CODE)) {
    hooks.Stop = hooks.Stop || []
    hooks.Stop.push(makeGroup(RELEASE_CODE))
  }

  writeFileSync(CLAUDE_SETTINGS, JSON.stringify(settings, null, 2))
  console.error("[6ix9ine] hooks installed in", CLAUDE_SETTINGS)
  return true
}

export function uninstall(): boolean {
  if (!existsSync(CLAUDE_SETTINGS)) return true

  const raw = readFileSync(CLAUDE_SETTINGS, "utf-8")
  const settings = JSON.parse(raw) as Record<string, unknown>
  const hooks = settings.hooks as Record<string, unknown[]> | undefined
  if (!hooks) return true

  for (const event of ["UserPromptSubmit", "Stop"] as const) {
    const code = event === "UserPromptSubmit" ? ACQUIRE_CODE : RELEASE_CODE
    if (hooks[event]) {
      hooks[event] = hooks[event].filter((group) => {
        const hookList = (group as Record<string, unknown>).hooks as Record<string, unknown[]>
        if (!hookList) return true
        return !hookList.some(
          (h) => h.type === "command" && JSON.stringify(h.args) === JSON.stringify(["-c", code])
        )
      })
      if (hooks[event].length === 0) delete hooks[event]
    }
  }

  writeFileSync(CLAUDE_SETTINGS, JSON.stringify(settings, null, 2))
  console.error("[6ix9ine] hooks removed from", CLAUDE_SETTINGS)
  return true
}

function main(): void {
  const isUninstall = process.argv.includes("--uninstall")

  if (!isUninstall) {
    if (!isDaemonReachable()) {
      console.error("[6ix9ine] daemon socket not found at", daemonSocketPath())
      console.error("[6ix9ine] is 6ix9ine running? hooks will install but will be no-ops until daemon starts")
    }
    install()
  } else {
    uninstall()
  }
}

main()
