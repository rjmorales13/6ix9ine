# Agent Hook Integration Guide

6ix9ine integrates with AI coding agents by hooking into their lifecycle events. When an agent starts a task, it calls `6ix9ine acquire`. When it finishes, it calls `6ix9ine release`. This is **activity-scoped**, not session-scoped — an open-but-idle agent at the prompt does not keep your Mac awake.

## How Hooks Work

Each agent has a hook system that allows running commands before/after specific events. 6ix9ine provides installers that automatically configure these hooks.

### Generic Hook Pattern

```bash
# When agent starts a turn / task
6ix9ine acquire <session-uuid> --tool <agent-name> --reason "<task-description>"

# When agent stops / goes idle
6ix9ine release <session-uuid>
```

Sessions are reference-counted by UUID. Overlapping tasks stack cleanly; sleep unblocks only when the last one releases.

---

## ✅ Claude Code

**Status:** Fully supported. Hook system confirmed and verified live (real hook invocation
simulated with synthetic stdin JSON, real `settings.json` merge, real acquire/release cycle) —
see `docs/planning/handoff-road-to-gummo.md` bug #5 for how the earlier, broken
implementation was found and fixed.

### Hook System

Claude Code reads hook configuration from the `"hooks"` key inside `~/.claude/settings.json`
(**not** a separate `hooks.json` file). Each event maps to an array of matcher groups; a command
hook receives its payload as **JSON on stdin** (fields include `session_id`, `prompt`,
`hook_event_name`, etc.) — it does not receive `{session_id}`/`{prompt_summary}`-style
placeholders substituted into `args`. `UserPromptSubmit` and `Stop` don't support a `matcher`
field at all (it's silently ignored if present — they always fire on every occurrence).

**Exit code 2 is blocking** for both events: for `UserPromptSubmit` it erases the submitted
prompt; for `Stop` it prevents Claude from finishing its turn. `hooks/claude.py` wraps its actual
work in `try/except` and always exits 0, regardless of whether the underlying `6ix9ine
acquire`/`release` call succeeds — a failure of 6ix9ine itself must never block or erase the
user's actual Claude Code usage.

### Events

| Event | Action |
|-------|--------|
| `UserPromptSubmit` | reads `session_id`/`prompt` from stdin, runs `6ix9ine acquire <session_id> --tool claude --reason <prompt[:80]>` |
| `Stop` | reads `session_id` from stdin, runs `6ix9ine release <session_id>` |

### Installer Behavior

The `6ix9ine install-hooks --agent claude` command:
1. Detects `~/.claude/` directory
2. Backs up existing `settings.json` to `settings.json.bak`
3. Merges a `UserPromptSubmit` and a `Stop` matcher group into `settings.json`'s `"hooks"` key,
   preserving any unrelated existing keys/hooks
4. Is idempotent — re-running it won't duplicate the entry

### Manual Configuration

If you prefer to configure manually, add a matcher group like this to your Claude Code
`settings.json` (the `command` path is resolved per-machine — prefer `shutil.which("6ix9ine")`,
with a frozen-binary and a source-install fallback; this is the shape, not a literal value to
paste):

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/opt/homebrew/bin/6ix9ine",
            "args": ["hook-acquire"]
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/opt/homebrew/bin/6ix9ine",
            "args": ["hook-release"]
          }
        ]
      }
    ]
  }
}
```

**Do not use `"command": "<python interpreter>", "args": ["-c", "<inline code>"]`.** That was the
original implementation and it locked a real user out of Claude Code entirely once run against the
frozen, Homebrew-distributed binary — see
[TROUBLESHOOTING-HOOKS.md](TROUBLESHOOTING-HOOKS.md) Case study 3 before building any new hook
integration the same way. The invoked command must be `6ix9ine` itself (resolved to wherever it's
actually installed) with a real subcommand as `args` — never an inline code string handed to a
general-purpose interpreter that may not exist in the shipped binary.

---

## ✅ OpenCode

**Status:** Fully supported. Hook system confirmed and verified live — real `chat.message`
acquire and real `session.idle`-triggered release, caught live in `6ix9ine status` concurrently
alongside an unrelated agent session. See
[TROUBLESHOOTING-HOOKS.md](TROUBLESHOOTING-HOOKS.md) bug #7 for how the earlier, completely
non-functional implementation was found and fixed, and for the real API details (verified
against the actual installed `@opencode-ai/plugin` package, not just docs); see Case study 4
(same doc) for a later fix (v1.0.3) to a hardcoded CLI path that went stale across install
methods.

### Hook System

OpenCode plugins export an async function `(input) => Promise<Hooks>`. There is no
`beforeCommand`/`afterCommand` — those never existed in the real API. The closest real hooks:
`"chat.message"` (fires with `input.sessionID` when a new message arrives) and the generic
`event` hook, filtered for `event.type === "session.idle"` (delivers `event.properties.sessionID`).
Plugins auto-load from `~/.config/opencode/plugins/` (global) or `.opencode/plugins/`
(project-level) — the glob also matches a singular `plugin/` directory name, but `plugins/` is
the documented, primary convention.

### Events

| Event | Action |
|-------|--------|
| `chat.message` | reads `input.sessionID`, runs `6ix9ine acquire <sessionID> --tool opencode --reason "opencode turn" --pid <process.pid>` |
| `event` (filtered to `type === "session.idle"`) | reads `event.properties.sessionID`, runs `6ix9ine release <sessionID>` |

`--pid` is the plugin host's own `process.pid` (the long-lived OpenCode process, not a per-call
worker). It's a defense-in-depth cleanup path, not a change to session identity: sessions are
still refcounted purely by their UUID `session-key`, and a clean `session.idle` release is still
the primary path. If OpenCode ever fails to emit `session.idle` (crash, force-quit, connection
drop), the daemon can fall back to pid-based cleanup — guarded against OS PID reuse via
`create_time` (resolved server-side, never trusted from the client) and exempt from CPU-idle
pruning (the host process is often near-0% CPU while genuinely waiting on the model mid-turn). See
[TROUBLESHOOTING-HOOKS.md](TROUBLESHOOTING-HOOKS.md) for the full incident this closes.

### Installer Behavior

The `6ix9ine install-hooks --agent opencode` command:
1. Detects `~/.config/opencode/` (global) or project `.opencode/` directory
2. Creates a 6ix9ine plugin file at `plugins/6ix9ine-hook.ts` in whichever was detected
3. OpenCode auto-discovers it at its own next startup — no separate registration step

### Manual Plugin Example

```typescript
// ~/.config/opencode/plugins/6ix9ine-hook.ts
import { execFileSync } from "node:child_process"

const CLI = "6ix9ine" // bare command name -- resolved via PATH at call time, not
                       // baked in as an absolute path. See TROUBLESHOOTING-HOOKS.md
                       // Case study 4 for why an absolute, install-time-resolved
                       // path goes stale across install-method changes here.

export const SixNinePlugin = async () => {
  return {
    "chat.message": async (input) => {
      try {
        execFileSync(CLI, ["acquire", input.sessionID, "--tool", "opencode", "--reason", "opencode turn", "--pid", process.pid.toString()], { timeout: 3000, stdio: "ignore" })
      } catch (err) {
        // 6ix9ine failing must never break an OpenCode turn
      }
    },
    event: async (input) => {
      if (input.event.type !== "session.idle") return
      const sessionID = input.event.properties?.sessionID
      if (!sessionID) return
      try {
        execFileSync(CLI, ["release", sessionID], { timeout: 3000, stdio: "ignore" })
      } catch (err) {
        // 6ix9ine failing must never break an OpenCode turn
      }
    },
  }
}
```

---

## 🔄 Codex CLI

**Status:** Hook integration **pending research**. This section documents what we need to determine.

### What We Need to Know

Before implementing Codex CLI hooks, we need to answer:

1. **Does Codex CLI read a configuration directory?**
   - Check for `~/.codex/`, `~/.codexrc`, or `~/.config/codex/`
   - What files exist in these directories?

2. **Does Codex CLI support lifecycle hooks?**
   - Can we inject pre/post commands via config?
   - Does it support environment variables like `CODEX_PRE_COMMAND`?
   - Does it have a plugin system?

3. **Does Codex CLI support MCP (Model Context Protocol)?**
   - If yes, we can provide an MCP tool: `6ix9ine_mcp_acquire` / `6ix9ine_mcp_release`
   - This would be the preferred integration method

4. **What is the exact process name?**
   - Is it `codex`, `codex-cli`, or something else?
   - This affects process sniffing in `daemon.py`

### Research Tasks

```bash
# Run these commands and report findings:
ls -la ~/.codex/
ls -la ~/.config/codex/
codex --help
codex --version
cat ~/.codex/config.json 2>/dev/null || echo "No config found"
```

### Fallback: Process Sniffing

If Codex CLI does not support hooks, `daemon.py` can use **process sniffing** as a fallback:

```python
# In daemon.py process watcher
CODEX_BINARIES = ["codex", "codex-cli"]

for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    if proc.info['name'] in CODEX_BINARIES:
        # Auto-acquire if not already tracked
        auto_acquire(proc.info['pid'], "codex")
```

This is less precise than hooks (can't distinguish idle vs. active) but works without agent cooperation.

---

## 🔄 Antigravity CLI (`agy`)

**Status:** Hook integration **pending research**. This section documents what we need to determine.

### What We Know

From Antigravity documentation:
- The CLI is invoked as `agy`
- It supports "hooks, plugins, and MCP"
- It has a plugin system, but the exact filesystem path is not confirmed

### What We Need to Know

1. **Configuration directory:**
   - Check for `~/.antigravity/`, `~/.agy/`, `~/.config/antigravity/`
   - What files exist in these directories?

2. **Hook/plugin system details:**
   - What is the plugin directory path?
   - What hook events are available? (e.g., `before_task`, `after_task`)
   - What is the plugin file format? (Python? JavaScript? JSON config?)

3. **MCP support:**
   - Does `agy` expose an MCP server?
   - Can we register `6ix9ine` as an MCP tool?

4. **Process name:**
   - Is the binary `agy`, `antigravity`, or `antigravity-cli`?

### Research Tasks

```bash
# Run these commands and report findings:
ls -la ~/.antigravity/
ls -la ~/.agy/
ls -la ~/.config/antigravity/
agy --help
agy --version
cat ~/.antigravity/config.yaml 2>/dev/null || echo "No config found"
```

### Fallback: Process Sniffing

```python
# In daemon.py process watcher
ANTIGRAVITY_BINARIES = ["agy", "antigravity", "antigravity-cli"]

for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    if proc.info['name'] in ANTIGRAVITY_BINARIES:
        auto_acquire(proc.info['pid'], "antigravity")
```

---

## Process Sniffing (Fallback for All Agents)

If an agent does not support hooks, `daemon.py` can auto-detect running agent processes and acquire/release based on process presence.

### Configuration

In `daemon.py`:

```python
AGENT_PROCESS_MAP = {
    "claude": ["claude"],
    "opencode": ["opencode"],
    "codex": ["codex", "codex-cli"],      # placeholder
    "antigravity": ["agy", "antigravity"], # placeholder
}

SNIFFING_ENABLED = True  # User-configurable
```

### Limitations

- Cannot distinguish between **idle** and **active** agent sessions
- May keep Mac awake while agent is open but not working
- Higher latency (polls every 5-10 seconds)
- Recommended only when hooks are unavailable

---

## Hook Installer Implementation

The `6ix9ine install-hooks` command should:

1. **Detect agent installation:**
   ```python
   def detect_claude():
       return os.path.exists(os.path.expanduser("~/.claude"))

   def detect_opencode():
       return os.path.exists(os.path.expanduser("~/.opencode")) or               os.path.exists(os.path.expanduser("~/.config/opencode"))

   def detect_codex():
       # TODO: Implement after research
       return os.path.exists(os.path.expanduser("~/.codex"))  # placeholder

   def detect_antigravity():
       # TODO: Implement after research
       return os.path.exists(os.path.expanduser("~/.antigravity"))  # placeholder
   ```

2. **Backup existing configs:**
   ```python
   import shutil
   shutil.copy(config_path, f"{config_path}.bak")
   ```

3. **Install hooks:**
   - Write hook config / plugin file
   - Register with agent's plugin system

4. **Verify:**
   - Run a test command through the agent
   - Check `6ix9ine status` shows the session

5. **Uninstall:**
   - Restore from `.bak` file
   - Remove plugin files
   - Clean up agent config references

---

## Adding a New Agent

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide on adding support for new agents, and
read [TROUBLESHOOTING-HOOKS.md](TROUBLESHOOTING-HOOKS.md) **first** — it now documents three
separate real incidents, two different classes of mistake. Claude Code and OpenCode were both
complete no-ops the first time around, built against guessed APIs never checked against a real
installation (Case studies 1–2). Claude Code's hooks were *later* fixed correctly, fully verified
against source execution, and still ended up locking a real user out of the tool entirely — because
the fix was never tested against the actual frozen binary real users run, only source (Case study
3). Verifying an API guess and verifying a working feature keeps working in production are two
different problems; that doc's checklist covers both.
