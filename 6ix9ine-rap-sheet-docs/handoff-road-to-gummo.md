# Handoff: Road to Gummo

Status snapshot as of 2026-07-04, updated same day after a live smoke test of the full
privileged path on this machine (`/Users/rmorales/PycharmProjects/6ix9ine/`). This doc is the
source of truth for what's done vs. not — re-read this before re-explaining context in a new
session.

Bar used throughout: **"Completed" = actually run/tested against real behavior, not just code
that exists.** Unit tests against mocked I/O count as "logic confirmed," not "feature confirmed."

---

## Completed — real, verified live on this machine (2026-07-04)

This is the first time anything in the privileged/system-integration layer has actually been
exercised for real (previously all of this was "logic confirmed via mocks" — see below).

- [x] `plists/com.rjmorales.6ix9ine.daemon.plist` and `plists/com.rjmorales.6ix9ine.helper.plist`
      written, `plutil -lint` clean, installed and loaded for real
- [x] `6ix9ine-daemon` running as a real LaunchAgent (real PID, loaded via
      `launchctl bootstrap gui/<uid>`), serving a real Unix socket at
      `~/Library/Application Support/6ix9ine/cli.sock`
- [x] `6ix9ine-helper` running as a real root LaunchDaemon (PID owned by `root`), serving
      `/var/run/6ix9ine-helper.sock`
- [x] Real peer-PID + owner-UID authorization confirmed working (see `helper.py:authorize`)
- [x] Real `acquire` → daemon → helper → `pmset disablesleep 1` confirmed via `pmset -g`
- [x] Real process-death auto-release confirmed: a one-shot `acquire` CLI call's own PID died
      immediately after the process exited; the daemon's process watcher detected this and
      released the session within the same tick, `pmset disablesleep` dropped back to `0`
      automatically with no manual `release` needed
- [x] Real duration-based `hold --for 5s` confirmed: expired on its own, `pmset disablesleep`
      returned to `0` automatically
- [x] Real lid-state read via live `ioreg` polling confirmed (`status` correctly reported
      `"lid": "open"`, matching actual hardware state) — a close/open **transition** still hasn't
      been observed (see Pending)
- [x] `daemon-status`, `status`, `helper-status` all confirmed against the real running
      processes, not mocks

---

## Bugs found and fixed during this smoke test

1. **Root helper shebang couldn't handle a space in the interpreter path.**
   `cli.py:build_setup_helper_script` wrote `#!{sys.executable}` as the launcher's shebang line.
   Since the interpreter lives at `~/Library/Application Support/6ix9ine/venv/bin/python3` (a
   space in "Application Support"), the kernel's shebang parser split on the first space and
   tried to exec `/Users/.../Application` as the interpreter — silent exec failure, nothing in
   `ps`, nothing logged. **Fixed**: the launcher installed at `HELPER_INSTALL_PATH` is now a
   space-free `#!/bin/sh` wrapper that `exec`s the real interpreter with its path passed as a
   normal quoted argv element (no shebang parsing involved), invoking a separate `_launcher.py`
   inside the `.d` install directory. Covered by existing tests (no assertions on the literal
   shebang text, so nothing needed updating there).
2. **Nothing copies the daemon's LaunchAgent plist into `~/Library/LaunchAgents/`.** Unlike
   `setup-privileged-helper` (which explicitly `cp`s the helper plist into
   `/Library/LaunchDaemons/`), `cmd_daemon_start` only ever calls `launchctl load` and assumes the
   plist is already in place. **Not fixed in code** — I copied it manually for this smoke test.
   `daemon-start` will still fail for the next person/machine until this is added (to
   `install.sh` or to `cmd_daemon_start` itself).
3. **Homebrew's bottled `python@3.13` (and `python@3.14`) could not `pip install` anything on
   this Mac** (macOS 26.1 "Tahoe" / Darwin 25.1.0). Both throw
   `ImportError: ... Symbol not found: _XML_SetAllocTrackerActivationThreshold ... Expected in:
   /usr/lib/libexpat.1.dylib` — a Homebrew-bottle/OS version mismatch, not a 6ix9ine bug. Fixed
   locally with `brew reinstall --build-from-source python@3.13`, which compiles `pyexpat`
   against this machine's actual libraries. If Homebrew ships a formula update, this may need
   redoing.
4. **`thermal_monitor.py`'s `powermetrics --samplers smc` doesn't exist on Apple Silicon.**
   Confirmed live: `powermetrics --samplers smc -i1 -n1` returns
   `powermetrics: unrecognized sampler: smc` on this hardware. `smc` was an Intel-only sampler
   name; Apple Silicon's equivalent is the `thermal` sampler (or `cpu_power`), with a different
   output format that `parse_cpu_temperature()` doesn't handle. Confirmed through the real
   running helper: a live `get_thermal` call returns
   `{"ok": false, "error": "CPU die temperature not found in powermetrics output"}`.
   **This is a real, previously-unknown bug** — thermal cutout protection does not currently work
   on Apple Silicon at all. **Not fixed this session** — needs its own investigation (dump real
   `--samplers thermal` output on this Mac, rewrite the regex/parser, add a fixture for it).

---

## Current live state on this machine (end of this session)

- `~/Library/Application Support/6ix9ine/venv` — Python 3.13 venv with `psutil`+`textual`
  installed; used as the interpreter for both the daemon and the helper
- `~/Library/Application Support/6ix9ine/{daemon.py,daemon_commands.py,ipc.py,lid_monitor.py,
  shared.py,thermal_monitor.py,idle_tracker.py,session_registry.py}` — a **runtime copy**, not
  the repo checkout. This will go stale if `bin/*.py` changes without being re-copied (another
  reason `install.sh` needs to exist).
- `~/Library/LaunchAgents/com.rjmorales.6ix9ine.daemon.plist` installed and loaded; daemon running
- `/Library/LaunchDaemons/com.rjmorales.6ix9ine.helper.plist`,
  `/Library/PrivilegedHelperTools/com.rjmorales.6ix9ine.helper(.d)`, and the `.owner` file
  installed and loaded; helper running as root
- Both processes were left running intentionally (matches the documented "always-on" design).
  Use `6ix9ine daemon-stop` / `6ix9ine uninstall-helper` (via the venv python above) to tear down.
- The repo's own `.venv` (3.9.6, used by `pytest`) was **not** touched or replaced.

---

## Completed (logic confirmed via passing unit tests)

All 182 tests pass (`pytest tests/ -q`). Each item below is tested against mocks/fixtures/tmp_path,
not real hardware or real filesystem state, *except* where superseded by the live section above.

- [x] `bin/session_registry.py` — acquire/release/hold refcounting, expiry logic
- [x] `bin/shared.py` — duration parsing (`30m`, `2h`, `1h30m`), path/bundle-id constants
- [x] `bin/ipc.py` — newline-delimited JSON wire protocol framing
- [x] `bin/cli.py` — all subcommand handlers (`acquire`, `release`, `hold`, `status`,
      `install-hooks`, `uninstall-hooks`, `daemon-*`, `setup-privileged-helper`,
      `uninstall-helper`, `helper-status`) — tested via dependency-injected fakes (`Deps` param)
- [x] `bin/daemon_commands.py` — ACQUIRE/RELEASE/HOLD/STATUS/KILL_ALL handlers
- [x] `bin/thermal_monitor.py` — `parse_cpu_temperature()` parsing logic tested against a
      hardcoded Intel-style sample string only — **now known not to match real Apple Silicon
      output** (see bug #4)
- [x] `bin/lid_monitor.py` — `parse_clamshell_state()` parsing logic, tested against hardcoded
      sample `ioreg` output — **now also confirmed against real live `ioreg` output** (steady
      state only, no transition yet)
- [x] `bin/idle_tracker.py` — idle-timeout logic
- [x] `bin/tui.py` — state/rendering logic, never actually launched on screen
- [x] `hooks/claude.py` — install/uninstall logic, tested against a fake `tmp_path/.claude`, never
      against the real `~/.claude/`
- [x] `hooks/opencode.py` — same pattern, fake `.opencode` dir only
- [x] `hooks/codex.py`, `hooks/antigravity.py` — confirmed to correctly no-op with a clear
      "pending research" error (this is the intended behavior, not a bug)
- [x] `LICENSE` (MIT), `README.md`, and full doc set in `6ix9ine-rap-sheet-docs/`
      (`ARCHITECTURE.md`, `INSTALL.md`, `API.md`, `HOOKS.md`, `CONTRIBUTING.md`)

---

## Pending — still not exercised for real

- [ ] No real lid-close/lid-open **transition** observed yet (only a steady-state "open" read so
      far)
- [ ] Thermal reading is real-attempted but currently broken on Apple Silicon (bug #4) — the
      cutout logic itself remains unit-tested only, and cannot fire correctly until the parser is
      fixed
- [x] ~~Hooks have never been installed into the real `~/.claude/` or `~/.opencode/`~~ — now
      exercised for real via `install.sh` → `6ix9ine install-hooks --all`. OpenCode installed for
      real (`~/.opencode/plugin/6ix9ine-hook.ts` written; its correctness against OpenCode's
      actual plugin-loading behavior is still unverified). **Claude Code did not** — see bug #5.
- [ ] `t69` (the Textual TUI) has never been visually launched — layout/keybindings unverified in
      a real terminal

---

## Bug #5 (new, higher priority than it looks): Claude Code hook integration was a no-op — FIXED

Discovered while wiring `install-hooks --all` into the now-fully-automated `install.sh`.
`hooks/claude.py` wrote its config to a standalone `~/.claude/hooks.json` file. Real Claude Code
reads hook configuration from the `"hooks"` key **inside `~/.claude/settings.json`** — confirmed
live on this machine: `~/.claude/settings.json` had a top-level `"hooks": {}` that stayed `{}`
after running the old `install-hooks --all`, while a brand-new, functionally-inert
`~/.claude/hooks.json` appeared instead. Claude Code never reads that file, so **the Claude Code
hook integration — the primary supported agent — had never actually worked**, and the existing
unit tests couldn't catch it because they only ever asserted against a fake
`tmp_path/.claude/hooks.json` that mirrored the same (wrong) assumption.

**Fixed this session.** Verified the real hook schema against the current official docs
(`code.claude.com/docs/en/hooks`) rather than relying on memory, since this touches the user's
**global** `~/.claude/settings.json` (affects every Claude Code session on the machine, not just
this project). Key facts that shaped the fix:
- Hook commands receive their payload as **JSON on stdin** (`session_id`, `prompt`,
  `hook_event_name`, ...), not via `{placeholder}` substitution in `args` (the old, wrong
  assumption)
- `UserPromptSubmit` and `Stop` don't support a `matcher` field at all
- **Exit code 2 is blocking**: for `UserPromptSubmit` it erases the submitted prompt; for `Stop`
  it prevents Claude from ever finishing its turn. This is the real danger of getting this wrong
  on a global config file — a hook that fails loudly could break prompt submission or turn
  completion across every project.

`hooks/claude.py` was rewritten to merge a `UserPromptSubmit`/`Stop` matcher group into
`settings.json` (preserving all unrelated existing keys — verified against the real file, which
also has `permissions`, `env`, `statusLine`, `enabledPlugins`, etc.), idempotently, with a
`.bak` backup before first write. The generated hook command reads stdin JSON and calls
`6ix9ine acquire`/`release`, wrapped in `try/except` so it **always exits 0** no matter what —
verified live with synthetic stdin payloads including malformed JSON, empty stdin, and a missing
`session_id` field, all correctly exiting 0.

**Verified live end-to-end** (not just unit tests): installed for real into this machine's actual
`~/.claude/settings.json`, then simulated a real `UserPromptSubmit` invocation with a synthetic
JSON payload piped to the exact installed command — it correctly called `6ix9ine acquire`,
`status` showed the session as `ACTIVE` with `agent: "claude"` and the real `pmset
disablesleep 1`. Simulated `Stop` similarly. Test suite: 185 passing (was 182 — added/rewrote
`tests/unit/test_hooks_claude.py` against the real schema). `HOOKS.md` updated to match.

The old, stale `~/.claude/hooks.json` artifact from the broken implementation was deleted as part
of applying the fix.

---

## Bug #6 (the big one, now FIXED): every session was auto-released within ~5 seconds regardless of real agent activity

Discovered running a real two-agent test (one short task, one long task, both explicitly driving
the CLI's `acquire`/`sleep`/`release` themselves via Haiku subagents, since subagent spawns don't
trigger the Claude Code hook lifecycle directly — see below). **Neither agent's own `release` call
succeeded** — both got `{"ok": false, "error": "session not found"}` — because the daemon had
already destroyed both sessions within about 5-10 seconds of them being acquired, regardless of
the fact real work (a 45-second sleep, standing in for a real long turn) was still in progress.

**Root cause**: `SessionRegistry.acquire()` was recording `pid=peer_pid`, where `peer_pid` is
whoever connects to the daemon's Unix socket (via `LOCAL_PEERPID`, `bin/ipc.py:get_peer_pid`) —
i.e. the one-shot `6ix9ine acquire` CLI process itself. That process sends one request and exits
immediately by design (`API.md`'s own latency budget: "acquire/release must round-trip in
< 50ms"). The daemon's `tick()` (every 5s, `bin/daemon.py:145`) prunes any session whose recorded
PID is no longer alive. Since the acquiring process is *always* dead within milliseconds of
acquiring, **every session was auto-pruned on the very next tick, no matter how long the actual
agent turn ran** — completely defeating the tool's core purpose for any turn longer than ~5
seconds (i.e. virtually all real usage). This also retroactively reframes my own earlier
"process-death auto-release confirmed working" note from the first live smoke test in this doc —
that was the same bug, observed without recognizing what it implied for real hook-driven turns.

There is no good substitute PID available from a hook context either: Claude Code's hook stdin
payload doesn't expose its own top-level process PID (checked the real schema — `session_id`,
`prompt_id`, `cwd`, `permission_mode`, etc., but nothing PID-like for "the Claude process still
running"). So PID-based liveness tracking cannot work correctly for hook-triggered sessions at
all, regardless of which PID you pick.

**Fixed**: `handle_acquire` (`bin/daemon_commands.py`) no longer accepts or records a `peer_pid`.
Sessions are now identified and reference-counted purely by their UUID `session_key` — which was
already the correct mechanism — with no PID-liveness tracking layered on top. `daemon.py`'s
`handle_request` still accepts `peer_pid` (required by the shared IPC `Handler` signature that
`helper.py` also uses, for a legitimate and unrelated purpose: per-request caller-UID
authorization) but no longer forwards it into acquire. `SessionRegistry.prune_dead`/`prune_idle`
and `idle_tracker.py` are untouched and still correctly tested at the unit level (they accept an
explicit `pid` and behave correctly if given one) — but with this fix, **no current code path
ever supplies a real pid**, so that machinery is now permanently dormant in practice.
**Follow-up decision needed**: leave this dormant (harmless, could be reactivated by some future
feature that has a real PID to offer) or remove it entirely as dead code and update
`ARCHITECTURE.md`'s "Process watcher" / "Idle release" claims accordingly. Not decided this
session.

**Tradeoff of the fix**: without PID-liveness, if Claude Code (or whatever agent) crashes hard
mid-turn without ever firing `Stop`, the session now stays held (and sleep blocked) indefinitely,
until someone runs `6ix9ine release`/`release --all`, or the daemon restarts (which clears all
in-memory session state). No safety-net expiry was added for this in this session.

**Verified live end-to-end** with two real Haiku subagents explicitly driving the CLI
(`acquire` → `sleep N` → `release`, staggered 10s vs 45s, since subagent spawns via the `Agent`
tool do not themselves trigger Claude Code's `UserPromptSubmit`/`Stop` hook lifecycle — that only
fires for the top-level interactive session):

| t | count | sleep_blocked | `pmset SleepDisabled` | sessions |
|---|---|---|---|---|
| +8s | 2 | True | 1 | both active |
| +16s | 1 | True (unchanged) | 1 | short one released, long one still holding |
| +24s | 0 | False | 0 | long one released |

Both agents' own `release` calls succeeded this time. Rewrote the two `test_daemon.py` tests that
had been asserting the *buggy* behavior as if it were a feature
(`test_tick_prunes_dead_sessions_and_unblocks`, `test_tick_prunes_idle_sessions`) into regression
tests proving sessions now survive `tick()` regardless of `pid_exists_fn`/`cpu_percent_fn`.
Updated `test_daemon_commands.py` similarly. Test suite: 185 passing throughout (same count as
before — replaced tests, not added).

Separately, `cmd_install_hooks`/`cmd_uninstall_hooks` in `cli.py` had their own bug: they never
checked the `ok` field a hook module's `install()`/`uninstall()` returns, so `hooks/codex.py` and
`hooks/antigravity.py` — which correctly decline with a "pending research" error when their config
dir is detected — were being silently reported as `"installed"` anyway. **Fixed**: both now sort
results into `installed`/`skipped`/`failed` based on the actual return value. Verified live: with
both `~/.codex` and `~/.antigravity` present on this machine, `install-hooks --all` now correctly
reports `codex` and `antigravity` under `"failed"` with their real error message, and only
`claude`/`opencode` under `"installed"`.

---

## New: `human-simulation-tests/` — real, non-mocked end-to-end suite

Added a separate suite at repo root (deliberately outside `tests/`, so it's never picked up by
the fast `pytest tests/ -q` sweep or run in a sandboxed/CI environment) that drives the actual
installed `6ix9ine` CLI against the actual running daemon and root helper — see its `README.md`
for preconditions and how to run it (`pytest human-simulation-tests/ -v`).

Covers: acquire/release round-trip, multi-session refcounting (regression test for bug #6),
hold-duration expiry, Claude Code hook schema installed correctly in the real
`~/.claude/settings.json` (regression test for bug #5), OpenCode plugin file installed, real
`ioreg` lid-state read, and — deliberately — a test that **currently fails** for bug #4 (thermal
`current_temp` never gets populated on Apple Silicon). That failure is intentional: it proves the
suite has teeth rather than trivially passing, and documents exactly what "fixed" will look like
when someone gets to bug #4.

One important lesson learned writing these: the first draft asserted the *global* `pmset
SleepDisabled` state after releasing a test's own session, which produced false failures — a real,
live session for **this very conversation** (the real Claude Code hook, from bug #5's fix, firing
for real on the actual message being answered while these tests ran) was still legitimately held,
since 6ix9ine is deliberately concurrent/refcounted. Fixed by scoping assertions to each test's own
session/hold key (checking presence/absence in `active_sessions`/`holds`) instead of the shared
global state — a good example of the fix itself creating a realistic test-interference scenario
that needed to be designed around, not suppressed.

Run directly (6 passed, 1 failed as expected) and independently by a background subagent given
only the README and the exact command, with no other context — both agreed.

---

## Bug #7 (same category as #5, now FIXED): OpenCode hook integration was also a no-op

Found when the user reported "OpenCode is running with an agent and the dashboard isn't picking
it up." Same root shape as bug #5: the implementation was built against a guessed API that never
matched reality, and was previously marked "✅ Fully supported. Hook system confirmed" in
`HOOKS.md` without ever being checked against a real OpenCode install.

**What was wrong**, verified against the actual `@opencode-ai/plugin` package installed on this
machine (`~/.config/opencode/node_modules/@opencode-ai/plugin/dist/index.d.ts`) — more
authoritative than the docs page, which itself omits payload shapes and lists a hook name that
turns out not to really exist as such:
- Wrote the plugin file to `~/.opencode/plugin/6ix9ine-hook.ts`. That directory
  (`~/.opencode/`) is just where the `opencode` CLI binary itself is installed on this machine
  (it has its own `bin/`, `node_modules/`, `package.json`) — it is **not** a real
  plugin-loading location. Real global plugins load from `~/.config/opencode/plugins/`
  (**plural** — the old code even used "plugin" singular for both candidate directories).
  `~/.config/opencode/` (which has `opencode.json`, `skills/`, actual project config) is the
  machine's real, actively-used OpenCode config directory.
- Exported a default object with `beforeCommand`/`afterCommand` methods. **Neither hook name
  exists** in the real `Hooks` interface. The real, closest analogs: `"chat.message"` (fires with
  `input.sessionID` when a new message arrives — used for acquire) and the generic `event` hook,
  filtered for `event.type === "session.idle"` with `event.properties.sessionID` (per
  `@opencode-ai/sdk`'s `EventSessionIdle` type — used for release). The docs page's mention of a
  top-level `"session.idle"` hook name is misleading for this installed SDK version (1.4.10); it's
  actually delivered through the generic `event` hook's `Event` discriminated union, not its own
  `Hooks` key.

Because the file was in the wrong directory, OpenCode never loaded it at all — not a partial
failure, a complete no-op, identical in spirit to bug #5.

**Fixed**: `hooks/opencode.py` rewritten — `HOME_CONFIG_DIR` now points at
`~/.config/opencode` (the old `~/.opencode` candidate was removed entirely, since it isn't a
real config location), plugin subdirectory changed to `plugins` (matching both the project-level
`.opencode/plugins/` and global `~/.config/opencode/plugins/` conventions), and the generated
plugin now uses the real `chat.message`/`event` hooks with real `input.sessionID`/
`event.properties.sessionID` fields, wrapped in `try/catch` so a 6ix9ine failure can never break
an OpenCode turn (same defensive posture as the Claude Code hook fix). Verified the generated
`.ts` file actually compiles with `bun build` (exit 0) — not just that Python wrote a file.
Rewrote `tests/unit/test_hooks_opencode.py` to match (186 tests passing total now, was 185).
Updated `human-simulation-tests/test_hooks_installed.py`'s OpenCode check similarly, and reran
the whole suite live (6 passed, 1 failed — thermal, as expected, unaffected by this fix).

Cleaned up the stale, never-loaded `~/.opencode/plugin/6ix9ine-hook.ts` from the old bug and
reinstalled for real at the correct `~/.config/opencode/plugins/6ix9ine-hook.ts`.

**Caveat confirmed**: this machine had 3 real OpenCode processes already running when the bug was
reported, all started well before the fix (checked via `ps` + `~/.local/share/opencode/log/opencode.log`
timestamps) — none of them can pick up the fix without a restart, same as the Claude Code hook
caveat from bug #5. This is exactly why the user still didn't see it in `t69` right after the fix
landed.

**Verified live, definitively, with a fresh `opencode run` invocation** (not just unit tests +
`bun build`): confirmed via `opencode debug config` that the plugin is correctly discovered
(`plugin_origins` includes `file:///Users/rmorales/.config/opencode/plugins/6ix9ine-hook.ts`).
A first live attempt to catch it in `6ix9ine status` showed nothing — traced to a **test
methodology bug on my part**, not a product bug: I ran `opencode run` with both a shell `&` and
the tool's own background flag (double-backgrounding), so the polling loop started only after the
whole ~9-second turn (including its own release) had likely already finished. A temporary
diagnostic build of the plugin (writing explicit markers to a file on module load, factory call,
and each hook firing) proved conclusively that `chat.message` fires with a real `sessionID` and
`event` fires with `type: "session.idle"`, with no caught errors from either `execSync` call. A
final, correctly-timed test (foreground `sleep` polling loop, single background process, checked
`kill -0` to confirm liveness) caught it directly: a real OpenCode session appeared in
`6ix9ine status` at t+2s (concurrently alongside this very Claude Code conversation's own
session — real multi-agent refcounting, live), stayed active for the ~6 seconds the OpenCode
process ran, and disappeared the instant it exited. The diagnostic build was reverted to the
clean version and reinstalled afterward.

**Lesson worth keeping**: when a "should be fixed" claim only rests on unit tests + a syntax
check, that's not verification — it's a hypothesis. The user pushing back ("I still don't see it")
was the right call here; the fix was actually correct, but that could only be established by
actually driving a real invocation and watching it happen, the same standard applied to every
other bug this session.

**Unrelated observation, not fixed**: `~/.config/opencode/opencode.json` on this machine has a
plaintext Ollama `apiKey` value. Not a 6ix9ine issue, just flagging it since it was visible while
investigating this bug — worth rotating/moving to an env var.

---

## Not built at all

- [x] ~~`install.sh`~~ — now exists at repo root, run and verified live on this machine
      (idempotent: no-ops cleanly on re-run against the already-installed state). Fixes bug #2 by
      generating the daemon LaunchAgent plist on the fly instead of assuming it's already in
      `~/Library/LaunchAgents/`. Installs `6ix9ine`/`t69` wrappers into `~/.local/bin` (no `sudo`,
      no root/launchd touched — that's still the separate `setup-privileged-helper` step).
      `plists/com.rjmorales.6ix9ine.daemon.plist` was **removed** from the repo since it hardcoded
      this machine's home directory and is now generated fresh by `install.sh` each time; only
      `plists/com.rjmorales.6ix9ine.helper.plist` remains as a static file (it has no per-user
      path, so it's genuinely portable as-is).
- [ ] `packaging/homebrew/` — empty, no `.rb` formula
- [ ] `packaging/npm/bin/`, `packaging/npm/scripts/` — still empty, and intentionally not being
      pursued right now (no concrete plan, unlike the Homebrew tap)

---

## Deferred (intentional, by design — not blockers)

- Codex CLI hook integration — `hooks/codex.py` is a documented placeholder pending research into
  Codex's hook/plugin/MCP surface. See `HOOKS.md` "Adding a New Agent" workflow before touching
  this.
- Antigravity CLI (`agy`) hook integration — same status, `hooks/antigravity.py`.
- Process-sniffing fallback (`SIXNINE_SNIFFING` env var, `AGENT_PROCESS_MAP` in `HOOKS.md`) — the
  fallback mechanism for agents without hook support is documented but not implemented in
  `daemon.py` yet. Only relevant once Codex/Antigravity work starts.
- Menu bar (`rumps`-based) option mentioned in `ARCHITECTURE.md` — optional, no code started.

---

## Open questions — updated after this session

1. **Plist content** — resolved. Static files in `plists/`, matching what `cli.py` already
   assumed. Both written and verified working, with the shebang caveat in bug #1.
2. **Root helper trust boundary** — resolved by reading the code. `bin/helper.py:authorize()`
   does **peer-PID + registered-owner-UID cross-checking**, not code-signing verification.
   `ARCHITECTURE.md` overstates this as "verifies caller code-signing requirement" — the doc
   should be corrected (or the implementation upgraded to match the doc). The current check did
   correctly authorize the real owner UID in the live test; a rejection path (different UID) was
   not separately tested this session.
3. **Have we ever run `sudo` for real?** Yes, now. `setup-privileged-helper` ran for real this
   session; the root LaunchDaemon is installed and confirmed working end to end.
4. **Homebrew tap / npm package ownership** — still unconfirmed; still aspirational placeholders
   as far as this session could tell. Not investigated further.
5. **macOS version / hardware** — this machine is macOS 26.1 (Darwin 25.1.0), Apple Silicon.
   Python 3.13.14 now works (after the Homebrew rebuild in bug #3). The project's own `.venv` is
   still 3.9.6 and was **not** touched — it's what `pytest` runs against, and could be recreated
   against 3.13 later for consistency with the documented requirement, but wasn't necessary for
   this smoke test.

---

## Suggested next step (for next session)

`install.sh` is now a single, fully-automated, idempotent command (venv, deps, runtime copy,
`6ix9ine`/`t69` wrappers, root helper setup, hook install, daemon start) — verified with a real
end-to-end run on this machine, and now also installs *working* Claude Code (bug #5) and OpenCode
(bug #7) hooks, plus sessions that actually hold for their real duration instead of dying within
~5 seconds (bug #6). These three were the biggest correctness bugs found this session — the
project's core promise (hold sleep prevention while an agent works, and know when one is)
mostly did not actually work end-to-end until they were fixed. Recommended priorities for next
session, roughly in order:

1. Verify a real OpenCode turn (not just unit tests + `bun build` syntax check) actually fires
   the new `chat.message`/`session.idle` hooks end-to-end and shows up in `t69`/`6ix9ine status`
   — start a **new** OpenCode session (the one already running when bug #7 was found won't pick
   up the fix retroactively, same caveat as Claude Code's hooks).
2. Decide the bug #6 follow-up: leave `prune_dead`/`prune_idle`/`idle_tracker.py` dormant (now
   unreachable in practice, but harmless and still unit-tested) or remove them and correct
   `ARCHITECTURE.md`'s "Process watcher" / "Idle release" claims to match. Also consider whether
   a non-PID safety net (e.g. max-age auto-expiry) is worth adding for the crash-without-Stop case
   the fix leaves open.
3. Investigate and fix bug #4 — thermal reading on Apple Silicon. This is a safety feature
   (thermal cutout while lid is closed) that currently cannot fire on this hardware at all.
4. Correct `ARCHITECTURE.md`'s code-signing claim (open question #2) so the doc matches the
   actual (weaker but functional) trust model, or upgrade the implementation to match the doc.
5. Observe a real lid-close/lid-open cycle and a real `t69` launch in a terminal.
6. Consider recreating `.venv` against Python 3.13 to match the documented requirement, now that
   the Homebrew pyexpat issue has a known fix (`brew reinstall --build-from-source python@3.13`).
7. `README.md` and `INSTALL.md` were rewritten this session (new tone/structure, real
   `install.sh`-based quick start, no more `/opt/6ix9ine` or `pip3 install psutil textual`
   leftovers). `README-WIP.md` is a draft kept locally by request — gitignored, not committed,
   not deleted.

---

## Status view rebuild (2026-07-04, branch `feat/status-view`)

The `t69` dashboard was rebuilt to the final spec
(`dashboard-status-view/status-view-spec.md`) per the implementation plan
(`dashboard-status-view/implementation-plan.md`):

- New pure-logic modules: `bin/tui_theme.py` (palette, held-time tiers,
  stable session colors, agent emoji) and `bin/tui_wordmark.py` (half-block
  pixel wordmark, collapse rule) — no Textual imports, fully unit-tested.
- `bin/tui.py` rebuilt: wordmark header + status lines, chip topline,
  dense monitor (sessions + timed holds, dim `—` pid), split inspector,
  quiet module dash, dark scrollbars, command palette disabled. All prior
  behavior kept (`--kill`, ignore filter, 2s refresh, k/x/a/r/q keys).
- Built via Haiku worker agents against orchestrator-written failing tests;
  Opus review pass. Test suite grew 186 → 246 (all green). Human-simulation
  suite unchanged: 6 pass + the known thermal failure (bug #4).
- First-ever visual renders captured via `App.export_screenshot()` (pilot
  harness) — full, collapsed (<30 rows), and daemon-down states verified.
- **Still pending**: the live manual checklist in the implementation plan
  (real terminal, real agent sessions, Terminal.app + iTerm2), and re-running
  `install.sh` so the runtime copy picks up the new TUI.
