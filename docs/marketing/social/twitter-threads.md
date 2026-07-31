# 6ix9ine — Social Media Content Pack

Launch-ready copy for Hacker News, Twitter/X, Reddit, Product Hunt, and Indie Hackers.
Positioning: **free + open source + session-aware + auditable root helper.** Lead with the problem and the transparency story, not the name.

> **The #1 asset before you post anything:** the demo GIF (see `RECORD-DEMO-GIF.md`).
> A short clip of the `t69` dashboard flipping `IDLE → 🚫 SLEEP BLOCKED → 💤 SLEEP AVAILABLE`
> outperforms any code screenshot on every channel. One recording, reused everywhere.

---

## Launch sequence (channel priority)

| Order | Channel | Why | When |
|---|---|---|---|
| 1 | **Hacker News — Show HN** | Best cold-start for auditable OSS dev tools; the architecture story lands here | Launch day, ~9am ET weekday |
| 2 | **Reddit** (staggered) | Targeted communities, problem-first titles | Days 1–3, one sub/day |
| 3 | **Twitter/X** | Broad reach + tag agent maintainers; GIF-led | Launch day, then ~1 week |
| 4 | **Product Hunt** | Long-tail visibility — but needs social proof first | Day 7+, after 10–20 stars |
| 5 | *(optional)* Lobsters, r/macapps, short video | Depth / spillover | As bandwidth allows |

**Golden rule for link-sensitive platforms (X especially):** keep GitHub links out of the
main post. Put them in the **first reply** or your bio. Outbound links in the top tweet get
the whole thread throttled.

---

## 1. Hacker News — Show HN (launch here first)

**Title:**

> Show HN: 6ix9ine – keep your Mac awake only while AI agents are working

**URL field:** `https://github.com/rjmorales13/6ix9ine`

**Text (first comment / body):**

> I kept losing long Claude Code runs the same way: dock the MacBook, close the lid, and macOS sleeps the whole machine mid-session. `caffeinate` doesn't survive a closed lid, and "never sleep" apps just leave the Mac awake around the clock.
>
> 6ix9ine ties wakefulness to actual work instead of a toggle. Agent lifecycle hooks call `acquire` on session start and `release` on end; a user-space daemon keeps a reference count; sleep is blocked only while the count is > 0 — clamshell included. If a process dies without releasing, a process-death watcher cleans it up, so a leaked wake lock is structurally impossible rather than merely unlikely.
>
> The part I actually want feedback on is the trust boundary. Truly blocking sleep on a lid-closed Mac needs root (`pmset disablesleep`), so I pushed all policy into user space and kept the root component to a single LaunchDaemon with one mutating endpoint — `set_sleep_blocked(bool)`, a fixed `pmset` argv (no shell, no caller input), peer-UID socket auth, and a reset-to-unblocked fail-safe on start/shutdown. It's ~140 lines in `bin/helper.py`; you can audit the entire privileged surface in a few minutes.
>
> macOS 14+, Python 3.13+, MIT. `brew install rjmorales13/6ix9ine/6ix9ine`. Claude Code and OpenCode hooks are confirmed end-to-end; Codex CLI and Antigravity are in progress. Critique of the privilege model especially welcome.

*HN doesn't penalize links in the body — this is the one place to be fully transparent up front. Reply to every comment for the first few hours; that's what keeps a Show HN on the front page.*

---

## 2. Twitter/X

### Hero tweet (post the GIF here, NO link)

> Your Mac has no idea Claude Code is working.
>
> You kick off a long agent run, close the lid, and macOS sleeps the whole machine. You come back to a dead session and half-finished work.
>
> So I built the thing that fixes it properly. 🧵
>
> [attach demo.gif — dashboard flipping ACTIVE → SLEEP BLOCKED → SLEEP AVAILABLE]

### Reply 1 — solution

> 6ix9ine blocks sleep *only* while agent sessions are running.
>
> Session starts → sleep blocked.
> Last session ends → Mac sleeps normally again.
>
> A reference counter, not a switch. No toggles, no "oops, it's been awake 3 days."

### Reply 2 — features

> ⚡ Auto-detects Claude Code + OpenCode via lifecycle hooks
> 🔒 Full clamshell support — docked, lid closed, running overnight
> 💀 Crash-safe: process-death watchers release leaked sessions
> 👁️ Live terminal dashboard (t69): every session, who holds it, for how long

### Reply 3 — transparency (the moat)

> It needs root to block clamshell sleep (`pmset disablesleep`).
>
> So the privileged helper is ~140 lines, ONE endpoint, peer-UID auth, resets to a safe state on crash.
>
> Audit the entire root surface in 5 minutes before installing. That's the whole pitch.

### Reply 4 — CTA + link (link goes HERE, not the top)

> Free. MIT. One command:
>
> brew install rjmorales13/6ix9ine/6ix9ine
>
> ⭐ if your Mac has ever fallen asleep mid-agent-run 👇
> https://github.com/rjmorales13/6ix9ine

**Amplification:** quote-tweet or reply-tag maintainers/communities of the tools it hooks
(Claude Code, OpenCode) — they're the most likely to reshare. Keep it factual, not spammy.

---

## 3. Reddit Post Templates

*Post natively (no crossposts), stagger across different days, and stay in the comments for
the first ~2 hours. Include the GIF wherever the sub allows it — visual proof converts 10x
better than text.*

### r/macOS — angle: the docked-Mac clamshell problem

**Title:** I made a free, open-source tool that keeps your Mac awake only while work is actually happening (full clamshell support)

**Body:**

> Like a lot of people here, I run long tasks on a docked MacBook with the lid closed — in my case AI coding agents that work for hours. macOS sleeps the moment the lid shuts, and the usual fixes are blunt: `caffeinate` dies with your terminal and doesn't handle clamshell, and the "never sleep" apps leave your Mac awake 24/7 whether it's working or not.
>
> So I built **6ix9ine** (yes, meme name — it's "the snitch that rats on sleep"). Instead of a toggle, it's a reference counter: tools call `acquire` when work starts and `release` when it ends, and sleep is blocked only while the count is above zero. Claude Code and OpenCode are auto-detected via hooks; anything else can use the manual CLI. If a process crashes without releasing, a watcher cleans it up — no leaked wake locks.
>
> Clamshell sleep needs root (`pmset disablesleep`), so the privileged part is deliberately tiny: a ~140-line helper with a single endpoint and peer-UID authentication. The whole thing is MIT-licensed specifically so you can read the root code before trusting it.
>
> macOS 14+, Python 3.13+. `brew install rjmorales13/6ix9ine/6ix9ine`. Free: https://github.com/rjmorales13/6ix9ine
>
> Happy to answer anything about the architecture — the privilege-separation design was the interesting part.

### r/ClaudeAI — angle: overnight Claude Code runs dying

**Title:** Tired of your Mac sleeping mid-Claude-Code-run? I made a free tool that keeps it awake only while the agent is working

**Body:**

> If you run Claude Code for long sessions on a laptop, you've probably hit this: the agent works, *you* don't touch the keyboard, macOS decides the machine is idle and sleeps — and your overnight run is dead by morning. Docked with the lid closed, it's worse: macOS sleeps almost immediately.
>
> **6ix9ine** hooks into Claude Code's session start/end events and blocks sleep only while a session is live, releasing it automatically when the last one ends. Multiple concurrent agents just work (reference-counted). There's a live terminal dashboard (`t69`) showing every active session and how long it's been held.
>
> Free, MIT, `brew install rjmorales13/6ix9ine/6ix9ine`. OpenCode is supported too; Codex CLI and Antigravity are in progress. https://github.com/rjmorales13/6ix9ine

### r/LocalLLaMA — angle: keeping long local jobs alive

**Title:** Keep your Mac awake only while a job is running (agents, training, batch) — free + open source, survives a closed lid

**Body:**

> Running local models or long batch jobs on a Mac and having it sleep out from under you? `caffeinate` is all-or-nothing and doesn't handle a docked/closed lid. I built **6ix9ine**: it blocks sleep only while work is actually in progress (reference-counted `acquire`/`release`), then lets the Mac sleep the moment the last job ends.
>
> AI coding agents (Claude Code, OpenCode) are auto-detected via hooks; anything else — a training run, an Ollama pipeline, a batch script — wraps in `6ix9ine acquire` / `release`. Clamshell support via a minimal ~140-line root helper you can audit before installing.
>
> MIT, `brew install rjmorales13/6ix9ine/6ix9ine`. https://github.com/rjmorales13/6ix9ine

### r/devtools — angle: agent-workflow tooling

**Title:** 6ix9ine — open-source sleep management for AI agent workflows (Claude Code, OpenCode)

**Body:**

> If you run Claude Code, OpenCode, or Aider for long sessions, you've hit this: the agent works, *you* don't touch the keyboard, macOS decides the machine is idle and sleeps. Your overnight run is dead by morning.
>
> 6ix9ine hooks into agent lifecycle events (session start/end) and keeps a reference-counted registry of active sessions. Sleep is blocked while count > 0, released automatically when the last session ends. Multiple concurrent agents just work. There's a live TUI dashboard (`t69`) showing every session, its agent, and hold duration.
>
> Design notes for this crowd: three-tier privilege separation (hooks → user-space daemon → minimal root helper), the root surface is one endpoint in ~140 auditable lines, process-death watchers prevent leaked sleep blocks, and there are 350+ tests including the live privileged path.
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

## 4. Product Hunt

**Tagline (73 chars, under the 100-char limit):**

> Keeps your Mac awake while AI agents work — free, open source, auditable.

**Timing & prep:**
- **Don't launch cold.** Wait until you have ~10–20 GitHub stars from the HN/Reddit waves — PH ranking is driven by early votes and social proof.
- Schedule for **12:01 AM Pacific** so you capture a full day on the leaderboard.
- Lead the **first maker comment** with the transparency story (the ~140-line auditable root helper) and embed the demo GIF in the gallery.

---

## 5. Indie Hackers Pitch

**Title:** 6ix9ine — I open-sourced the "boring" infrastructure my AI agent workflow needed

**Body:**

> Every long Claude Code run I did died the same way: I'd dock my MacBook, close the lid, and macOS would sleep-kill the session. The existing options were a paid closed-source app or "never sleep" toggles that left the machine awake around the clock.
>
> So I built the tool I wanted: **6ix9ine**, a free, MIT-licensed daemon that ties sleep to actual work. Agent hooks increment a reference counter on session start and decrement on end; sleep is blocked only while the count is above zero. Clamshell support, crash-safe cleanup, live terminal dashboard.
>
> The bet I'm making on distribution: for software that needs root, **transparency is the moat**. The paid competitor can't show you its privileged code — mine is ~140 lines and I tell people to read it before installing. Free + auditable is a quadrant the paid apps structurally can't enter.
>
> It's early — Claude Code and OpenCode integrations are live, Homebrew tap is up. I'd love feedback from anyone building for the AI-agent workflow space: what other tools in your stack should auto-detect sessions like this?
>
> https://github.com/rjmorales13/6ix9ine

---

## Pre-launch checklist

- [x] **Record the demo GIF** (`RECORD-DEMO-GIF.md`) and wire it into the README hero slot
- [x] **Set GitHub repo description + topics** — was blank, so every search result, topic page, and link preview rendered an empty repo. 20 topics set (`claude-code`, `ai-agents`, `keep-awake`, `caffeinate`, `pmset`, `clamshell`, …). Homepage still blank pending the GitHub Pages landing page.
- [x] **Confirm `brew install rjmorales13/6ix9ine/6ix9ine` works on a clean machine** — verified by the maintainer.
- [x] **Skim the top of the README as a first-time visitor** — problem lands well inside 15 seconds (line 4 + the GIF caption carry it). Two badges were working against it and got fixed: `Python 3.13+` was false friction (Homebrew ships frozen binaries needing **no** Python — the full 389-test suite passes on 3.12), and `macOS-supported` understated the constraint. Requirements now split by install method, plus a macOS-only disclaimer routing Linux/Windows interest to a feature request.
- [x] **Post the X/Twitter thread** — posted 2026-07-31 from the app account. 5 posts chained, GIF on the hero, link held to the final post.
- [ ] Draft the HN Show HN and have the tab open for launch-day morning
- [ ] Pre-write Reddit replies to the obvious objections ("why not caffeinate?", "why trust root?")

## Cadence notes

- **Thread cadence (X):** post the hero tweet standalone first; add replies within ~10 minutes. Link only in the final reply.
- **Reddit:** native posts only, one subreddit per day, stay in comments for the first 2 hours.
- **Product Hunt:** hold until you have stars; transparency story in the first maker comment.
- **All channels:** lead with the problem; let the name be a punchline, never the hook.
