# Contributing to 6ix9ine

Thank you for considering contributing! This guide covers how to add support for new agents, improve the core system, and submit changes.

## Adding Support for a New Agent

**Read [TROUBLESHOOTING-HOOKS.md](TROUBLESHOOTING-HOOKS.md) before starting.** Both existing hook
integrations (Claude Code, OpenCode) were shipped as `✅ Fully supported` while being complete
no-ops — each was built against a guessed API that was never checked against what's actually
installed. That doc has the concrete verification checklist and the exact mistakes to avoid; the
steps below are the general shape, not a substitute for it.

### Step 1: Research the Agent's Hook System

Before writing code, determine:

1. **Process name(s):** What does `psutil` see? (e.g., `claude`, `opencode`, `codex`)
2. **Config directory:** Where does the agent store settings? (e.g., `~/.claude/`, `~/.opencode/`)
3. **Hook mechanism:**
   - JSON config file with pre/post commands?
   - Plugin directory (Python/TypeScript/JS)?
   - MCP (Model Context Protocol) server?
   - Environment variables?
   - None (use process sniffing fallback)?
4. **Lifecycle events:** What events can we hook into?
   - `beforeTurn` / `afterTurn`
   - `beforeCommand` / `afterCommand`
   - `UserPromptSubmit` / `Stop`
   - `taskStart` / `taskEnd`

### Step 2: Document Your Research

Add a section to [HOOKS.md](HOOKS.md) with:
- Status emoji: ✅ (confirmed), 🔄 (pending), ❌ (not supported)
- What you found
- Research tasks for others to verify
- Fallback process sniffing config if hooks unavailable

### Step 3: Implement the Hook Installer

**The template below illustrates the general `detect`/`install`/`uninstall`/`verify` shape
only.** The config file location, the `"hooks"` key structure, and the `{session_id}`-style
placeholder substitution are all *illustrative*, not a real, verified API for any actual tool —
copying them as-is is exactly how bugs #5 and #7 happened (see
[TROUBLESHOOTING-HOOKS.md](TROUBLESHOOTING-HOOKS.md)). Replace every concrete detail with what you
independently verified in Step 1 against the real, installed tool.

Create a new file in `hooks/<agent_name>.py`:

```python
# hooks/newagent.py
import os
import json
import shutil
from pathlib import Path

AGENT_NAME = "newagent"
CONFIG_DIR = "~/.newagent"
CONFIG_FILE = "hooks.json"


def detect() -> bool:
    """Check if this agent is installed on the system."""
    return os.path.exists(os.path.expanduser(CONFIG_DIR))


def install() -> dict:
    """Install hooks into the agent's config."""
    config_path = os.path.expanduser(f"{CONFIG_DIR}/{CONFIG_FILE}")
    
    # Backup existing config
    if os.path.exists(config_path):
        shutil.copy(config_path, f"{config_path}.bak")
    
    # Read existing config or create new
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        config = {}
    
    # Add hooks
    config["hooks"] = config.get("hooks", {})
    config["hooks"]["beforeTask"] = {
        "command": "6ix9ine acquire",
        "args": ["{session_id}", "--tool", AGENT_NAME, "--reason", "{task_description}"]
    }
    config["hooks"]["afterTask"] = {
        "command": "6ix9ine release",
        "args": ["{session_id}"]
    }
    
    # Write back
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    return {"ok": True, "config_path": config_path}


def uninstall() -> dict:
    """Remove hooks and restore from backup."""
    config_path = os.path.expanduser(f"{CONFIG_DIR}/{CONFIG_FILE}")
    backup_path = f"{config_path}.bak"
    
    if os.path.exists(backup_path):
        shutil.copy(backup_path, config_path)
        return {"ok": True, "restored_from": backup_path}
    
    # If no backup, try to clean manually
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        if "hooks" in config:
            config["hooks"].pop("beforeTask", None)
            config["hooks"].pop("afterTask", None)
            if not config["hooks"]:
                del config["hooks"]
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    return {"ok": True}


def verify() -> bool:
    """Verify hooks are working."""
    return True
```

### Step 4: Register in the CLI

Update `cli.py` to include the new agent:

```python
from hooks import claude, opencode, newagent

AGENT_MODULES = {
    "claude": claude,
    "opencode": opencode,
    "newagent": newagent,
}
```

### Step 5: Add Process Sniffing Fallback

Update `daemon.py`:

```python
AGENT_PROCESS_MAP = {
    "claude": ["claude"],
    "opencode": ["opencode"],
    "newagent": ["newagent", "newagent-cli"],
}
```

### Step 6: Test

```bash
# Install hooks for your new agent
6ix9ine install-hooks --agent newagent

# Verify
6ix9ine status

# Run the agent and confirm sessions appear
# Confirm sleep blocks when agent is working
# Confirm sleep resumes when agent is idle

# Uninstall hooks
6ix9ine uninstall-hooks --agent newagent
```

### Step 7: Update Documentation

- Add to [HOOKS.md](HOOKS.md) with full instructions
- Add to [README.md](../README.md) supported agents list
- Update [API.md](API.md) if new CLI flags are needed

---

## Development Setup

```bash
git clone https://github.com/rjmorales13/6ix9ine.git
cd 6ix9ine

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
# Requirements: psutil, textual, asyncio

# Run tests
python -m pytest tests/

# Run daemon in foreground (for debugging)
python bin/daemon.py --foreground

# Run CLI against local daemon
python bin/cli.py status
```

---

## Code Style

- **Python 3.13+** syntax only
- Type hints on all public functions
- Docstrings in Google style
- Max line length: 100 characters
- Use `asyncio` for async code, `threading` for blocking I/O

---

## Testing

### Unit Tests

```bash
python -m pytest tests/unit/
```

### Integration Tests

```bash
# Requires helper to be installed
python -m pytest tests/integration/ --helper-installed
```

### Manual Test Checklist

Before submitting a PR for a new agent:

- [ ] Hook installer detects the agent correctly
- [ ] Hook installer backs up existing config
- [ ] Hook installer writes valid config
- [ ] Agent acquires session on task start
- [ ] Agent releases session on task end
- [ ] Overlapping sessions refcount correctly
- [ ] `6ix9ine status` shows the session
- [ ] Sleep is blocked while session is active
- [ ] Sleep resumes when last session releases
- [ ] `t69 --kill` restores normal sleep
- [ ] Hook uninstaller restores original config
- [ ] Process sniffing fallback works (if applicable)

---

## Submitting Changes

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/new-agent-support`
3. Make changes with tests
4. Update documentation
5. Submit a PR with:
   - Description of the agent's hook system
   - Screenshots of `6ix9ine status` showing it working
   - Confirmation of manual test checklist

---

## Questions?

Open an issue with the `question` label or reach out in discussions.