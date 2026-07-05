# 6ix9ine

> 6ix9ine is the snitch that rats on sleep: it keeps your Mac awake only while work is happening, then lets it go back to sleep like nothing ever happened.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![macOS](https://img.shields.io/badge/macOS-supported-000000?logo=apple&logoColor=white)](#requirements)

<p align="left"><sub><strong>Built for docked Macs, active agents, and the moments when you want one quick glance instead of a full terminal dive.</strong></sub></p>

## What It Does

6ix9ine keeps your Mac awake only while active work is underway. When sessions are active, it blocks sleep, including clamshell sleep for docked or lid-closed Macs. When nothing is running, your Mac goes back to normal sleep behavior.

It also gives you a lightweight dashboard so you can see active sessions and other processes, like Ollama, in one place.

## Why It Exists

Most sleep tools are either too broad or too invisible. 6ix9ine exists to keep the machine awake only when the work deserves it, then get out of the way the moment the job is done.

## Features

- Keeps your Mac awake only while active work is happening, then lets it sleep normally again
- Supports clamshell mode, so docked Macs stay awake when the lid closes
- Shows active sessions and other running processes like Ollama in a live dashboard
- Lightweight, with a small footprint and fast status checks
- Designed to work on Macs as long as Python 3.13+ is installed

### Supported Agents

- ✅ Claude Code
- ✅ OpenCode
- 🔄 Codex CLI *(hook integration pending — see [HOOKS.md](6ix9ine-rap-sheet-docs/HOOKS.md))*
- 🔄 Antigravity CLI (`agy`) *(hook integration pending — see [HOOKS.md](6ix9ine-rap-sheet-docs/HOOKS.md))*

## Requirements

- macOS 14+
- Python 3.13+

## Getting Started

### Install

**Homebrew** *(recommended — tap is being finalized, not published yet)*:

```bash
brew tap rjmorales13/6ix9ine
brew install 6ix9ine
```

**From source** *(works today — see [INSTALL.md](6ix9ine-rap-sheet-docs/INSTALL.md) for details)*:

```bash
git clone https://github.com/rjmorales13/6ix9ine.git
cd 6ix9ine
./install.sh
```

This sets up a private Python 3.13 venv, installs dependencies, and puts `6ix9ine` and `t69` on your `PATH` (via `~/.local/bin`). It does **not** touch root or `launchd` — that's the next, explicit step.

### One-time privileged helper setup

Installs the small root LaunchDaemon that's the only part of 6ix9ine allowed to touch sleep-blocking APIs:

```bash
6ix9ine setup-privileged-helper
```

### Install hooks into your agents

```bash
6ix9ine install-hooks --all
```

### Start the daemon

```bash
6ix9ine daemon-start
```

### Start the dashboard

```bash
t69
```

## Dashboard

The dashboard is the main place to monitor what is happening right now.

- Active sessions are shown first
- Other processes, such as Ollama, are shown alongside them
- The view is intentionally minimal so status is easy to read at a glance
- Final TUI direction: full-page terminal `status view` with row-specific color, distinct session identities, and held-time thresholds

Think of it as the live control surface: one place to confirm what is awake, what is holding sleep open, and what is just running in the background.

## Want Something Added?

Leave a comment or open an issue with the next thing you want 6ix9ine to watch, show, or automate.

## Contributors

<table>
<tr>
<td align="center">
  <a href="https://github.com/rjmorales13">
    <img src="https://github.com/rjmorales13.png?size=160" width="96" height="96" alt="rjmorales13" />
    <br /><strong>rjmorales13</strong>
  </a>
  <br /><sub>Creator</sub>
  <br /><sub><a href="https://www.linkedin.com/in/robert-morales-8a2b806a/">LinkedIn</a></sub>
</td>
</tr>
</table>

> I innovate where others iterate. I build tools that break molds, learn relentlessly, and leave every system better than I found it. I don't just write software - I play the game, and I play to win. Veni, vidi, vici.

## Documentation

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](6ix9ine-rap-sheet-docs/ARCHITECTURE.md) | System design, privilege tiers, and IPC protocol |
| [INSTALL.md](6ix9ine-rap-sheet-docs/INSTALL.md) | Installation options and setup steps |
| [HOOKS.md](6ix9ine-rap-sheet-docs/HOOKS.md) | Agent hook integration guide |
| [API.md](6ix9ine-rap-sheet-docs/API.md) | CLI reference and status output |
| [CONTRIBUTING.md](6ix9ine-rap-sheet-docs/CONTRIBUTING.md) | How to add support for new agents |
| [TROUBLESHOOTING-HOOKS.md](6ix9ine-rap-sheet-docs/TROUBLESHOOTING-HOOKS.md) | Hook integration bugs found/fixed, and a verification checklist for adding new agents |
| [dashboard-status-view/status-view-spec.md](6ix9ine-rap-sheet-docs/dashboard-status-view/status-view-spec.md) | Final TUI dashboard mock and visual rules |

## Support This Project

- [Buy Me a Coffee](https://buymeacoffee.com/rjmorales13)
- [Cash App](https://cash.app/$awe50me)

## License

MIT
