# How to Keep Your Mac Awake for Claude Code: caffeinate vs. LidRun vs. Macchiato vs. adrafinil vs. 6ix9ine

If you've ever kicked off a long Claude Code session, closed your MacBook lid, and come back to a dead agent and a half-finished refactor, you already know the problem: macOS is aggressive about sleep, and AI coding agents are exactly the kind of long-running, bursty workload that sleep kills.

This post compares every realistic way to keep a Mac awake during Claude Code sessions — the built-in free option, the paid app, the free alternatives, and the open-source session-aware approach — and ends with a straight answer about when each one makes sense.

One framing note up front: most comparisons of keep-awake tools rank convenience. This one also ranks **trust**, because several of these tools ask for privileged control over your machine's power management. What you can and can't audit matters.

## The Problem: Agents Work Longer Than Your Mac Stays Awake

An AI agent session doesn't look like normal usage to macOS. You type a prompt, then the machine works — compiling, running tests, calling APIs — while *you* do nothing. No keyboard, no mouse, no video playing. From the OS's point of view, the machine is idle, and idle machines get put to sleep.

It gets worse on a docked Mac. Close the lid and macOS wants to sleep immediately, which means the popular "run the agent overnight on the desk Mac" workflow dies at the lid hinge. Display-sleep tricks don't help here; you need *system* sleep blocked, which on modern macOS ultimately means `pmset disablesleep` — a command that requires root.

So the real question isn't "how do I keep my Mac awake" — it's "how do I keep my Mac awake **while Claude Code is actually working**, including with the lid closed, without leaving sleep disabled forever and without handing root to something I can't read?"

## The Free Built-In: `caffeinate`

macOS ships with an answer, and it's genuinely good at what it does. `caffeinate` creates a power assertion for as long as it runs:

```bash
# Keep the system awake until you Ctrl-C
caffeinate -dims

# Keep it awake exactly as long as one command runs
caffeinate -i npm run build
```

**Strengths:** It's free, it's already installed, it's Apple's own code, and the wrap-a-command form is elegant — the assertion dies exactly when the work does.

**Weaknesses:** It has no idea what an agent session is. You have to remember to start it, remember to stop it, and keep the terminal alive — close that window and the assertion evaporates mid-run. Run it in the background and you've built the opposite problem: a Mac that never sleeps because you forgot about a process. And critically for docked Macs, `caffeinate` doesn't survive the clamshell case — closing the lid still sleeps the machine.

**Verdict:** Perfect for wrapping a single known command. The wrong shape for agent sessions that start and stop on their own schedule.

## The Paid Option: LidRun

LidRun is the polished commercial entry: a proper app, multi-agent support, and compatibility across macOS versions.

**Strengths:** If you want a supported product with a nice interface and someone to email when it breaks, this is that. It handles the lid-closed case, which puts it ahead of `caffeinate` for docked setups.

**Weaknesses:** Two, and they compound. First, it's paid — you're buying something the OS half-provides for free. Second, it's closed-source. That's fine for a to-do app; it's a harder swallow for software that manipulates system sleep at a privileged level. You cannot read the code you're trusting. For a lot of developers, "trust us" is a fine answer right up until the software wants elevated control of the machine — and then it isn't.

**Verdict:** You're paying for convenience and accepting a black box. Reasonable trade for some; a non-starter for others.

## The Free Alternatives: Macchiato and adrafinil

Two free options sit between the built-in and the paid app.

**Macchiato** is open source, which immediately puts it in better trust territory than LidRun. Its multi-agent support is limited, though, and it's early — minimal community traction so far. At its core it's still a toggle: *you* decide when the Mac should stay awake, not your workload.

**adrafinil** is also free with partially visible source, but it only targets the latest macOS, and like Macchiato its multi-agent support is limited.

**Verdict:** Both are honest free tools, and if all you want is a nicer manual switch than `caffeinate`, either might do. But neither knows whether work is actually happening. The failure modes are the same as the built-in — forget to enable it and your session dies; forget to disable it and your Mac never sleeps — just with a friendlier switch.

## 6ix9ine: Sleep That Follows the Work

[6ix9ine](https://github.com/rjmorales13/6ix9ine) (yes, the name is a meme — the tagline is "the snitch that rats on sleep") takes a different approach: instead of a toggle, it's a **reference counter**.

Here's the model. Claude Code and OpenCode expose lifecycle hooks that fire when a session starts and ends. 6ix9ine installs small hooks into those events:

- Session starts → hook calls `6ix9ine acquire` → counter goes up → sleep blocked
- Session ends → hook calls `6ix9ine release` → counter goes down
- Counter hits zero → sleep unblocked, automatically

You never flip a switch. Start three concurrent agent sessions, and your Mac stays awake until the *last* one finishes — then it goes back to sleeping normally like nothing happened. If an agent crashes without calling release, a process-death watcher notices the dead PID and releases the session for it, so a crashed tool can't leave your Mac permanently insomniac.

The clamshell case is handled properly: a minimal root helper calls `pmset disablesleep`, so a docked Mac keeps working overnight with the lid shut — full system wakefulness, not just display tricks.

And this is where the trust argument becomes concrete rather than rhetorical. That root helper — the only privileged component in the system — is about 140 lines of Python. One endpoint (`set_sleep_blocked(true|false)`), Unix-socket transport, peer-UID authentication so only the user-level daemon can talk to it, and a startup safety net that resets sleep to unblocked so a crash can never leave `disablesleep` stuck on. You can read the entire privilege-escalation path in one sitting before you install it. It's MIT-licensed and free.

There's also a live terminal dashboard (`t69`) showing every active session, which agent holds it, and for how long — so "why is my Mac awake right now" always has a visible answer.

Confirmed hook integrations today are Claude Code and OpenCode, with manual `acquire`/`release` commands for any other tool or script (Codex CLI and Antigravity integrations are in progress). It requires macOS 14+ and Python 3.13+.

## Comparison Table

| | `caffeinate` | LidRun | Macchiato | adrafinil | 6ix9ine |
|---|---|---|---|---|---|
| **Cost** | Free (built-in) | Paid | Free | Free | Free |
| **Open source** | Apple internal | ✗ | ✓ | Partial | ✓ (MIT) |
| **Auditable privileged code** | N/A | ✗ | Partial | Partial | ✓ — ~140-line helper |
| **Session-aware (auto acquire/release)** | Only via command-wrap | ✗ | ✗ | ✗ | ✓ |
| **Lid-closed (clamshell) support** | ✗ | ✓ | ✓ | ✓ | ✓ |
| **Multi-agent (Claude Code, OpenCode, …)** | ✗ | ✓ | Limited | Limited | ✓ |
| **Crash-safe (no leaked sleep blocks)** | ✗ | Unknown | ✗ | ✗ | ✓ — process-death watchers |
| **Live dashboard** | ✗ | ✗ | ✗ | ✗ | ✓ (`t69`) |

## When to Use Each

**Use `caffeinate`** when you're wrapping one known command — a build, a test suite, a download. `caffeinate -i <cmd>` is the right tool and nothing beats zero install.

**Use LidRun** if you want a commercial product with support behind it, you need the lid-closed case handled, and closed-source privileged software doesn't bother you.

**Use Macchiato or adrafinil** if you want a free manual toggle with a nicer interface than the terminal, and your workflow is simple enough that you'll remember to flip it both ways.

**Use 6ix9ine** if you run Claude Code or other AI agents seriously: overnight sessions, docked Macs, multiple concurrent agents. It's the only option where sleep is tied to whether work is *actually happening*, and the only one where you can audit every line that runs as root before trusting it.

## Try It

```bash
git clone https://github.com/rjmorales13/6ix9ine.git && cd 6ix9ine && ./install.sh
```

One command installs the daemon, the hooks, and the dashboard. And before you run it — seriously — go read [`bin/helper.py`](https://github.com/rjmorales13/6ix9ine/blob/main/bin/helper.py). It'll take you five minutes, and it's the whole point: keeping your Mac awake for Claude Code shouldn't require trusting a black box with root.
