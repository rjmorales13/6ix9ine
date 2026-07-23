# Troubleshooting Hooks

Read this before adding hook support for a new agent CLI (Codex, Antigravity, or anything else),
and before trusting any existing hook integration in this repo at face value.

## Why this doc exists

Two of the three implemented agent hook integrations — Claude Code and OpenCode — were **complete
no-ops** despite both being marked `✅ Fully supported. Hook system confirmed` in
[HOOKS.md](HOOKS.md). Both were built against a guessed API that was never checked against a real
installation, and both guesses were wrong in a way that made the integration silently do nothing —
not a partial failure, a complete no-op that looked like working code and passed its own unit
tests. This doc records exactly what was wrong, how each was found and fixed, and — the important
part — the methodology to use so the next integration doesn't repeat the same mistake.

## The core lesson

**A hook integration that "looks right" and passes unit tests against its own assumptions is not
verified.** Every hook implementation in this project so far was written against a guess about a
third-party API, and every guess was wrong. The only way to actually know a hook fires is to:

1. Verify the real API against the **actually installed** package/binary on the target machine
   (source code or shipped type definitions), not just published docs — docs can be outdated,
   incomplete, or describe a different version than what's installed. This project hit real cases
   of both.
2. Prove data flows in with a **live invocation**, not just a unit test against mocked I/O.
3. Prove the effect you actually care about happens on shared, mutable system state (in
   6ix9ine's case: `6ix9ine status`, real `pmset -g` output) — not just "the hook's own code ran
   without throwing."

---

## Case study 1: Claude Code (bug #5)

### What was wrong

`hooks/claude.py` wrote its config to a standalone `~/.claude/hooks.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": {
      "command": "6ix9ine acquire",
      "args": ["{session_id}", "--tool", "claude", "--reason", "{prompt_summary}"]
    }
  }
}
```

Real Claude Code reads hook configuration from the `"hooks"` key **inside**
`~/.claude/settings.json` — a completely different file, which it never wrote to. The
`{session_id}`/`{prompt_summary}` placeholder-substitution pattern doesn't exist either: real
hook commands receive their payload as **JSON on stdin**.

### How it was found

Verified the real schema against the current official docs (`code.claude.com/docs/en/hooks`)
instead of trusting the existing implementation, because the change touches a **global** config
file (`~/.claude/settings.json` affects every Claude Code session on the machine, not just one
project) — getting it wrong has real blast radius. Confirmed live against this machine's actual
`settings.json`, which had a `"hooks": {}` that had stayed empty despite the old `install-hooks`
reporting success.

### The real schema

- Hook config lives in `settings.json`'s `"hooks"` key: an object keyed by event name, each value
  an array of matcher groups — `{matcher?: string, hooks: [{type: "command", command: string,
  args?: string[]}]}`.
- `UserPromptSubmit` and `Stop` do **not** support a `matcher` at all — silently ignored if
  present.
- Command hooks receive their payload as **JSON on stdin**:
  `{session_id, prompt_id, transcript_path, cwd, permission_mode, hook_event_name, prompt
  (UserPromptSubmit only), ...}` — never via `args` substitution.
- **Exit code 2 is blocking, and this is the single most important safety fact**: for
  `UserPromptSubmit` it erases the submitted prompt; for `Stop` it prevents Claude from ever
  finishing its turn. Any other nonzero exit code is a non-blocking warning (shown, but execution
  continues).

### The fix

- Merge into `settings.json`'s `"hooks"` key (backed up to `.bak` first), preserving every
  unrelated existing key
- Generate a command that reads stdin JSON and calls `6ix9ine acquire`/`release`, wrapped in
  `try/except` that **always exits 0** regardless of whether the underlying call succeeds
- Idempotent (checks before appending) and precise on uninstall (removes exactly the matched
  entry, not a blind whole-file restore from backup)

### How it was verified

1. Unit tests rewritten against the corrected schema (`tests/unit/test_hooks_claude.py`)
2. Installed for real into this machine's actual `settings.json`; confirmed valid JSON and every
   pre-existing key (`permissions`, `env`, `statusLine`, `enabledPlugins`, ...) untouched
3. Extracted the literal installed command from the real file and executed it with a synthetic
   JSON payload piped to stdin, exactly as Claude Code would invoke it — confirmed real
   `6ix9ine acquire`, real `status` showing `ACTIVE`, real `pmset disablesleep 1`
4. Confirmed exit code 0 even with malformed JSON, empty stdin, and a missing `session_id` field
   — the failure modes that must never turn into a blocking exit 2
5. Confirmed unprompted, later in the same session: a real `UserPromptSubmit` fired for an actual
   user message in an actual live conversation

---

## Case study 2: OpenCode (bug #7)

### What was wrong

`hooks/opencode.py` wrote a plugin file to `~/.opencode/plugin/6ix9ine-hook.ts`, exporting:

```ts
export default {
  beforeCommand: (command) => { /* ... */ },
  afterCommand: () => { /* ... */ },
}
```

`beforeCommand`/`afterCommand` do not exist anywhere in the real `@opencode-ai/plugin` API.

### How it was found

The user reported "OpenCode is running with an agent and the dashboard isn't picking it up."
Checked the *actually installed* package on the machine —
`~/.config/opencode/node_modules/@opencode-ai/plugin/dist/index.d.ts` — which is more
authoritative than any docs page since it's the exact version actually running. Its `Hooks`
interface has no `beforeCommand`/`afterCommand` at all.

### The real schema

- A plugin file exports an async function: `(input: PluginInput) => Promise<Hooks>`.
- Closest real hooks for "acquire on start of work / release on stop":
  - `"chat.message"` — fires with `input.sessionID` when a new message is received (→ acquire)
  - the generic `event` hook, filtered for `event.type === "session.idle"` (→ release). This
    event type is defined in `@opencode-ai/sdk`'s `EventSessionIdle`, delivered through the
    generic `event` hook's `Event` union — **not** its own top-level `Hooks` key, despite the
    docs page implying otherwise.
- Global plugins auto-load from `~/.config/opencode/plugins/`. The real glob pattern is
  `{plugin,plugins}/*.{ts,js}` scanned against a resolved list of directories that also includes
  `~/.opencode/` (confirmed by reading the actual `opencode` source and cross-checking with
  `opencode debug config`'s `plugin_origins` output) — so the directory-naming part of the
  original bug diagnosis was actually a partial red herring. **The wrong export shape was the
  real, sole cause of the complete no-op**, not the directory.

### The fix

- Rewrote the plugin template to the real `chat.message`/`event` hooks, `try/catch`-wrapped so a
  6ix9ine failure can never break an OpenCode turn
- Standardized on `~/.config/opencode/plugins/` (plural) going forward as the primary, documented
  global location

### How it was verified — including a false negative worth learning from

1. Unit tests rewritten against the corrected schema (`tests/unit/test_hooks_opencode.py`)
2. `bun build` on the generated `.ts` file — confirms it actually compiles, not just that Python
   wrote *a* file
3. **First live attempt gave a false negative.** Ran `opencode run "..."` with a shell `&` *and*
   the tool's own background-execution flag (double-backgrounding), then polled `6ix9ine status`
   — saw nothing, which looked like proof the fix didn't work. It wasn't: the whole ~9-second
   turn (including its own release) had almost certainly already finished before the polling loop
   even started running.
4. Used `opencode debug config` to directly confirm the plugin was correctly discovered in
   `plugin_origins` — this ruled out a location/registration problem before looking further.
5. Added a **temporary diagnostic build** of the plugin that wrote unambiguous markers (module
   load, factory call, each hook firing, with the real payload) to a plain file — independent of
   `execSync`/6ix9ine/log-parsing ambiguity. This proved `chat.message` and
   `event: session.idle` both fire with real data and no caught errors.
6. Ran a **correctly-timed** live test: single background process (no shell `&`), polling every 1
   second, checking `kill -0 $PID` to confirm actual liveness before treating any result as
   meaningful. Caught the real OpenCode session appear in `6ix9ine status` at t+2s — concurrently
   alongside an unrelated real session from a different agent, i.e. real multi-agent
   refcounting — held for the process's full lifetime, released the instant it exited.
7. Reverted the diagnostic build to the clean version and reinstalled it for real.

---

## Case study 3: Claude Code hook lockout (PR #13) — a *verified, working* integration that later became actively dangerous

### What was wrong

Case study 1's fix was real and correctly verified against source execution. It broke anyway, in
production, for a reason source-level verification could never have caught. `hooks/claude.py`
installed each hook as:

```json
{"type": "command", "command": "<sys.executable>", "args": ["-c", "<embedded python source>"]}
```

`sys.executable` is a real, general-purpose Python interpreter when running from source — `-c
"<code>"` works fine. But 6ix9ine ships to real users as a **PyInstaller-frozen binary** via
Homebrew, and in a frozen binary, `sys.executable` resolves to **the binary itself**, not an
interpreter. The frozen binary's `main()` is a fixed `argparse` dispatcher, not a Python REPL — it
rejected `-c` as an invalid subcommand and exited **2**. Claude Code treats exit 2 from
`UserPromptSubmit` as blocking. **This locked the maintainer out of every single Claude Code
prompt during real, live testing on their own machine**, requiring manual `~/.claude/settings.json`
surgery to recover — not a hypothetical, not a test-environment artifact.

### How it was found

Not by code review. A separate, unrelated PR (#12, bundling the `hooks/` package into the frozen
binary) was independently reviewed and approved with zero findings — because reviewing that diff
alone could never reveal that a completely different, untouched code path (the hook installer)
carried an assumption that's only false in a build mode the diff never exercised. It was found
because the maintainer insisted on running `install-hooks --all` against the **real,
Homebrew-distributed frozen binary**, rather than trusting that fixing one known bug (PR #12) made
the feature safe to consider done.

### The real problem

- `sys.executable` is not a stable "something that can run arbitrary code" signal. It means two
  different things depending on execution mode, and only one of those meanings actually supports
  `-c <code>`.
- No test in this project, before PR #13, ever built and executed the actual frozen binary's
  installed hook. Every prior test exercised source-mode execution or mocked subprocess calls —
  however thorough that suite looked, it structurally could not have caught this.

### The fix

- Stopped generating hooks as `<interpreter> -c <code>` entirely. Added real `hook-acquire`/
  `hook-release` subcommands to the CLI's own `argparse` dispatch — this works identically frozen
  or from source, because both modes go through the same dispatcher; neither depends on an
  external general-purpose interpreter being reachable.
- Hard-required the new subcommands to **always exit 0** (swallow every exception) and **print
  nothing to stdout** for `UserPromptSubmit`/`Stop` — Claude Code injects a `UserPromptSubmit`
  hook's stdout directly into the prompt context, so even a normal, successful JSON response would
  have silently corrupted every prompt if printed.
- Real users could already have the OLD broken hook baked into their `settings.json` (exactly what
  happened to the maintainer) — so the fix also had to make the uninstall/self-heal matching logic
  recognize **both** the old broken shape and the new one. A fix that only recognizes its own new
  shape leaves anyone already affected permanently stuck, because a "successful" uninstall would
  silently do nothing for them.
- Removed the `PreToolUse`/Bash hook entirely rather than patching it in place — it turned out to
  have never worked, even from source (a silently swallowed `NameError`), and its actual expected
  Claude Code output contract was never verified against real docs. Shipping an unverified
  reimplementation of something capable of blocking tool execution was judged worse than
  temporarily losing the feature.

### How it was verified

1. Reproduced the exact crash first, against a freshly rebuilt frozen binary — confirmed
   `<binary> -c "print(1)"` exits 2 with `argparse`'s "invalid choice" error, matching the real
   incident precisely.
2. Built the fixed binary fresh and, in an **isolated temp `HOME`** (never the real
   `~/.claude/settings.json`), ran `install-hooks`, then actually executed the resulting installed
   commands with a realistic JSON payload on stdin — confirmed exit 0, empty stdout, for both
   `UserPromptSubmit` and `Stop`.
3. Seeded an isolated settings file with the **exact old broken hook shape**, reproducing the
   maintainer's real incident, confirmed it still reproduces exit 2 — then ran the **fixed**
   binary's `install-hooks` against it and confirmed it replaced the broken hook with the safe
   one, while leaving an unrelated, pre-existing setting in the same file untouched. This is the
   test that proves the fix can *repair* an already-affected user, not just prevent new breakage.
4. An independent reviewer, in a separate context with no access to the implementer's own
   reasoning, re-verified the fix from the diff and separately re-confirmed the mechanism against
   its own fresh build before approving.

---

## Universal checklist for adding hook support for a new CLI

Do **not** start from the `hooks/newagent.py` template in [CONTRIBUTING.md](CONTRIBUTING.md) as
if the hook names/shapes shown there are real for any specific tool — that template illustrates
the general pattern (`detect`/`install`/`uninstall`/`verify`), not a verified API. Every concrete
hook name, config file location, and payload shape must be independently verified per tool, using
the steps below.

### 1. Find the actual source of truth, in priority order

1. **The tool's own installed package/binary on this machine** — `node_modules/<pkg>/dist/*.d.ts`
   or equivalent shipped source/type definitions. Most authoritative: it's the exact version
   actually running, not whatever a docs page describes.
2. **The tool's own debug/introspection commands**, if it has them (e.g. `opencode debug config`,
   `opencode debug paths`) — shows what the running process actually resolved, not what you assume
   it resolved.
3. **Current official docs** — useful for orientation, but verify against #1 before trusting it.
   This project hit two separate cases of docs being incomplete or outright wrong for the
   installed version.

### 2. Determine the real answers to

- Where does hook/plugin config actually live? (the exact file, not a guessed convention)
- What's the real schema for registering a hook/plugin?
- What's the real payload shape delivered to a hook — args? stdin? a context object? — and which
  field carries the session/task identifier?
- **Can a hook block or break the host tool's normal operation if it errors or returns something
  unexpected?** (Claude Code: yes, exit code 2 blocks/erases.) Establish this before writing
  anything — it determines how defensively the generated code must be written.
- **Does 6ix9ine ship as a compiled/frozen binary in production, even though it also runs from
  source during development?** (Yes — PyInstaller, distributed via Homebrew.) If the hook's
  invocation mechanism depends on `sys.executable` (or any equivalent "find me an interpreter"
  signal) being a general-purpose interpreter, verify that holds in **both** modes before shipping
  — it does not for a frozen binary, which is a fixed program, not an interpreter. See Case study 3.
- **Does the host tool consume or inject the hook's stdout into its own context** (e.g. Claude
  Code's `UserPromptSubmit`)? If so, the hook must produce **exactly** what's expected on
  stdout — usually nothing — not whatever a normal, successful CLI response would print.

### 3. Write the installer so that

- It's idempotent — re-running `install-hooks` must not duplicate entries
- It preserves everything unrelated in the target config file (merge, never overwrite wholesale)
- It backs up the existing file before the first write
- The generated hook command **always succeeds from the host tool's point of view**, regardless
  of whether the underlying `6ix9ine acquire`/`release` call actually succeeds — wrap in
  try/except (or the target language's equivalent) and never let a 6ix9ine failure propagate as a
  blocking error to the host tool
- Uninstall removes exactly what was added (match on content), not "restore the whole file from a
  backup that might now be stale from unrelated later edits"
- Never hardcode one specific install method's binary path (e.g. a from-source install script's
  target directory) as the only way to find the CLI. Resolve it dynamically — PATH lookup first,
  with sensible fallbacks — so it keeps working under every install method, including ones that
  didn't exist yet when the hook was first written
- If a hook's installed shape ever changes between versions, the matching logic in `uninstall()`/
  `install()` must recognize **both** the old and new shapes. A fix that only cleans up its own new
  shape leaves anyone already on the old, broken shape permanently stuck — a "successful" uninstall
  would silently do nothing for them. See Case study 3

### 4. Verify, in this order — do not skip to the end

1. Unit tests against the corrected schema, using fake config directories
2. Confirm the generated file/config is valid in its own right — parse the JSON; for
   compiled/typed languages, actually compile it (`bun build`, `tsc`, etc.)
3. Install for real against this machine's real config; confirm the diff is exactly what you
   expect (existing keys untouched, new entry present and well-formed)
4. Drive a **real, live invocation** of the target tool and prove the hook fires — not "should
   fire because the code looks right." If the tool has no headless/one-shot mode, add temporary
   diagnostic side effects (write to a marker file on module load / each hook firing) rather than
   trusting silence as success.
5. Confirm the actual effect you care about happens: check `6ix9ine status`, real `pmset -g`
   output — not just that the hook's own code ran without an exception.
6. Test against the **actual distributed artifact real users run** — the frozen binary, not just
   source execution. Some failure modes exist *only* in that mode (Case study 3); no amount of
   source-level testing will surface them.
7. **Never test hook installation against your own real, in-use config file**
   (`~/.claude/settings.json` or equivalent) — always use an isolated temp `HOME`/config directory.
   This is not a hypothetical precaution: a broken hook has already locked a real person out of
   their own tool in this project's history (Case study 3).

### 5. Common test-methodology traps (both hit in this session)

- **Checking status only after a background process may have already finished its whole
  lifecycle.** Always confirm liveness (`kill -0 $PID`, or poll fast enough) before treating an
  empty result as meaningful.
- **Double-backgrounding** — `cmd &` inside a call that's *also* run with the harness's own
  background-execution flag. The outer wrapper returns almost immediately, decoupling your "wait"
  from the thing you're actually waiting on, and any subsequent polling starts too late.
- **An already-running session of the target tool will never pick up a hook installed after it
  started.** Hooks/plugins load at startup. Always test with a freshly started process, and note
  this caveat clearly when reporting a fix — the user's existing session(s) won't reflect it.
