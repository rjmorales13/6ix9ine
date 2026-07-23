# Outline: How to Keep Your Mac Awake During Claude Code Sessions — Every Option Compared

**Target keyword:** `keep mac awake claude code`
**Secondary keywords:** `caffeinate alternative`, `mac sleep ai agent`, `keep macbook awake lid closed`
**Format:** Comparison post (~1,200–1,500 words) · **Audience:** Developers running AI coding agents on macOS
**Angle:** Trust and transparency — "what each tool costs you in trust vs. convenience"

---

## 1. The Problem (~150 words)

- Long-running AI agent sessions (Claude Code, OpenCode, Aider) die when your Mac sleeps.
- Docked MacBooks with the lid closed are the worst case: macOS sleeps and your overnight agent run is gone by morning.
- Existing fixes are blunt instruments: they keep the Mac awake *forever*, not *while work is happening*.
- Frame the reader's real question: "How do I keep my Mac awake only while Claude Code is running?"

## 2. The Free Built-In: `caffeinate` (~200 words)

- Ships with macOS; zero install. `caffeinate -dims`, or wrap a command.
- Strengths: free, scriptable, no third-party trust required.
- Weaknesses: manual start/stop, assertion dies with the terminal, no session awareness, no clamshell (lid-closed) protection, nothing to look at.
- Verdict: fine for a one-off build; wrong shape for agent workflows.

## 3. The Paid Option: LidRun (~150 words)

- Polished, paid, closed-source.
- Strengths: nice UX, multi-agent support, works across macOS versions.
- Weaknesses: costs money for something the OS half-does, and — the trust point — you can't read the code that's being handed privileged control of your machine's sleep behavior.
- Verdict: pay for convenience, accept a black box.

## 4. Free Alternatives: Macchiato & adrafinil (~150 words)

- Both free; both partially open.
- Macchiato: open-source but limited multi-agent support; minimal traction so far.
- adrafinil: free, latest-macOS-only, limited multi-agent support, partial transparency.
- Verdict: closer in spirit, but still manual toggles at heart — none track whether *work is actually happening*.

## 5. 6ix9ine: Session-Aware Sleep Control (~250 words)

- Free, MIT-licensed, fully open source.
- The core difference: **reference counting, not toggles**. Agent hooks fire acquire/release; the daemon counts active sessions; sleep is blocked only while count > 0.
- Confirmed hook integrations: Claude Code, OpenCode; manual `acquire`/`release` for anything else.
- Clamshell support via a minimal root helper (`pmset disablesleep`) — the only privileged component, ~140 lines, auditable in one sitting.
- Process-death watchers: crashed agents can't leak a sleep block.
- `t69` live dashboard: see every session, who holds what, and for how long.
- Trust angle: the only keep-awake daemon where you can read the entire privilege-escalation path before trusting it with root.

## 6. Comparison Table (~100 words)

Rows: Cost · Open source · Auditable privileged code · Session-aware (auto release) · Clamshell/lid-closed support · Multi-agent · Crash-safe (no leaked blocks) · Dashboard
Columns: `caffeinate` · LidRun · Macchiato · adrafinil · 6ix9ine

## 7. When to Use Each (~150 words)

- `caffeinate`: one-off commands, scripts, CI-ish local tasks.
- LidRun: you want a paid, supported GUI product and don't mind closed source.
- Macchiato / adrafinil: free manual toggles, simple needs.
- 6ix9ine: you run AI coding agents, you want sleep tied to actual work, and you want to audit what runs as root.

## 8. CTA (~50 words)

- GitHub repo link + `./install.sh` one-liner.
- Invitation to read `helper.py` before installing — transparency as the pitch.

---

**Internal notes:**
- Every competitor claim must stay within the verified comparison dimensions (cost, openness, multi-agent, OS support). No invented feature claims.
- Keyword placement: title, H1, first paragraph, section 5 heading vicinity, conclusion.
- Publish targets: Dev.to (primary), Medium (canonical link back), GitHub Pages.
