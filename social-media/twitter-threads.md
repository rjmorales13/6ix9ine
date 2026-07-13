# 6ix9ine — Social Media Content Pack

Launch-ready copy for Twitter/X, Reddit, Product Hunt, and Indie Hackers.
Positioning: **free + open source + session-aware + auditable root helper.** Lead with the problem and the transparency story, not the name.

---

## Twitter/X: 5-Tweet Launch Thread

**Tweet 1 — Problem**

> Your Mac has no idea Claude Code is working.
>
> You kick off a long agent run, close the lid, and macOS puts everything to sleep. Come back to a dead session and a half-finished refactor.
>
> Keep-awake apps "fix" this by never letting your Mac sleep. That's not a fix. 🧵

**Tweet 2 — Solution**

> I built 6ix9ine: a free, open-source daemon that blocks sleep only while agent sessions are running.
>
> Session starts → sleep blocked.
> Last session ends → Mac sleeps normally again.
>
> No toggles. No "oops, it's been awake for 3 days." A reference counter, not a switch.

**Tweet 3 — Features**

> ⚡ Auto-detects Claude Code + OpenCode sessions via lifecycle hooks
> 🔒 Full clamshell support — docked Mac, lid closed, agents running overnight
> 💀 Crash-safe: process-death watchers release leaked sessions
> 👁️ Live terminal dashboard (t69): every session, who holds it, for how long

**Tweet 4 — Transparency**

> The part I care about most: it needs root to block clamshell sleep (pmset disablesleep).
>
> So the privileged helper is ~140 lines with ONE endpoint. Peer-UID auth. Resets to a safe state on crash.
>
> Audit the entire root surface in 5 minutes before installing. That's the point.

**Tweet 5 — CTA**

> Free. MIT-licensed. One-command install.
>
> git clone https://github.com/rjmorales13/6ix9ine.git && cd 6ix9ine && ./install.sh
>
> Read helper.py before you run it — seriously, it's the whole pitch.
>
> ⭐ if your Mac has ever fallen asleep mid-agent-run: https://github.com/rjmorales13/6ix9ine

---

## Reddit Post Templates

### r/macOS — angle: the docked-Mac clamshell problem

**Title:** I made a free, open-source tool that keeps your Mac awake only while work is actually happening (full clamshell support)

**Body:**

> Like a lot of people here, I run long tasks on a docked MacBook with the lid closed — in my case AI coding agents that work for hours. macOS sleeps the moment the lid shuts, and the usual fixes are blunt: `caffeinate` dies with your terminal and doesn't handle clamshell, and the "never sleep" apps leave your Mac awake 24/7 whether it's working or not.
>
> So I built **6ix9ine** (yes, meme name — it's "the snitch that rats on sleep"). Instead of a toggle, it's a reference counter: tools call `acquire` when work starts and `release` when it ends, and sleep is blocked only while the count is above zero. Claude Code and OpenCode are auto-detected via hooks; anything else can use the manual CLI. If a process crashes without releasing, a watcher cleans it up — no leaked wake locks.
>
> Clamshell sleep needs root (`pmset disablesleep`), so the privileged part is deliberately tiny: a ~140-line helper with a single endpoint and peer-UID authentication. The whole thing is MIT-licensed specifically so you can read the root code before trusting it.
>
> macOS 14+, Python 3.13+. Free: https://github.com/rjmorales13/6ix9ine
>
> Happy to answer anything about the architecture — the privilege-separation design was the interesting part.

### r/devtools — angle: agent-workflow tooling

**Title:** 6ix9ine — open-source sleep management for AI agent workflows (Claude Code, OpenCode)

**Body:**

> If you run Claude Code, OpenCode, or Aider for long sessions, you've hit this: the agent works, *you* don't touch the keyboard, macOS decides the machine is idle and sleeps. Your overnight run is dead by morning.
>
> 6ix9ine hooks into agent lifecycle events (session start/end) and keeps a reference-counted registry of active sessions. Sleep is blocked while count > 0, released automatically when the last session ends. Multiple concurrent agents just work. There's a live TUI dashboard (`t69`) showing every session, its agent, and hold duration.
>
> Design notes for this crowd: three-tier privilege separation (hooks → user-space daemon → minimal root helper), the root surface is one endpoint in ~140 auditable lines, process-death watchers prevent leaked sleep blocks, and there are 223+ tests including the live privileged path.
>
> Free, MIT: https://github.com/rjmorales13/6ix9ine
>
> Claude Code and OpenCode hooks are confirmed end-to-end; Codex CLI and Antigravity are in progress — contributions welcome if you use either.

### r/programming — angle: the architecture story

**Title:** Designing a macOS daemon so the root-privileged surface is 140 auditable lines

**Body:**

> I built a keep-awake daemon for AI agent sessions and wrote up the part I think is actually interesting: how to need root (truly blocking sleep on a lid-closed Mac requires `pmset disablesleep`) without becoming a root daemon.
>
> The design is classic privilege separation: ephemeral hooks fire session events; a user-space LaunchAgent owns *all* policy logic as a pure, unit-testable reference-counted registry; and the only root component is a LaunchDaemon with exactly one mutating endpoint — `set_sleep_blocked(bool)` — a fixed `pmset` argv (no shell, no caller input), peer-UID socket authentication, and a reset-to-unblocked fail-safe on start and shutdown so a crash loop can't leave sleep permanently disabled.
>
> The registry also anchors tracked PIDs by process creation time so PID reuse can't fake a live session, and prunes sessions whose owning process died — a leaked wake lock is structurally impossible rather than merely unlikely.
>
> Source (MIT): https://github.com/rjmorales13/6ix9ine — the privileged component is `bin/helper.py` if you want to audit the claims. Critique of the trust boundary welcome; peer-PID auth over `LOCAL_PEERPID` was the pragmatic choice given no pure-Python XPC bindings, and the code says so honestly.

---

## Product Hunt Tagline

> Keeps your Mac awake while AI agents work — free, open source, auditable.

*(73 characters — under the 100-char Product Hunt limit)*

---

## Indie Hackers Pitch

**Title:** 6ix9ine — I open-sourced the "boring" infrastructure my AI agent workflow needed

**Body:**

> Every long Claude Code run I did died the same way: I'd dock my MacBook, close the lid, and macOS would sleep-kill the session. The existing options were a paid closed-source app or "never sleep" toggles that left the machine awake around the clock.
>
> So I built the tool I wanted: **6ix9ine**, a free, MIT-licensed daemon that ties sleep to actual work. Agent hooks increment a reference counter on session start and decrement on end; sleep is blocked only while the count is above zero. Clamshell support, crash-safe cleanup, live terminal dashboard.
>
> The bet I'm making on distribution: for software that needs root, **transparency is the moat**. The paid competitor can't show you its privileged code — mine is ~140 lines and I tell people to read it before installing. Free + auditable is a quadrant the paid apps structurally can't enter.
>
> It's early — Claude Code and OpenCode integrations are live, Homebrew formula is next. I'd love feedback from anyone building for the AI-agent workflow space: what other tools in your stack should auto-detect sessions like this?
>
> https://github.com/rjmorales13/6ix9ine

---

## Usage Notes

- **Thread cadence:** post Tweet 1 standalone first; add 2–5 as replies within 10 minutes.
- **Reddit:** post natively (no crossposts), stagger subreddits across different days, and stay in the comments for the first 2 hours.
- **Product Hunt:** pair the tagline with the transparency story in the first maker comment.
- **All channels:** lead with the problem; let the name be a punchline, never the hook.
