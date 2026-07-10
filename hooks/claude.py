from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

AGENT_NAME = "claude"
CONFIG_DIR = Path.home() / ".claude"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

# Absolute path to the installed CLI wrapper (see install.sh) -- deterministic
# per-$HOME, independent of whichever interpreter happens to run this module.
_CLI_PATH = str(Path.home() / ".local" / "bin" / "6ix9ine")

# Real Claude Code hooks receive their payload as JSON on stdin (not via
# {placeholder} substitution in args -- see 6ix9ine-rap-sheet-docs/HOOKS.md).
# Both snippets swallow every exception and always exit 0: UserPromptSubmit
# and Stop both treat exit code 2 as a *blocking* error (erasing the prompt,
# or refusing to let Claude stop, respectively), so a hook that fails loudly
# here would break the user's actual Claude Code session, not just 6ix9ine.
_ACQUIRE_CODE = (
    "import json, subprocess, sys\n"
    "try:\n"
    "    data = json.load(sys.stdin)\n"
    "    session_id = data.get('session_id') or ''\n"
    "    reason = (data.get('prompt') or '')[:80]\n"
    "    if session_id:\n"
    "        subprocess.run(\n"
    f"            [{_CLI_PATH!r}, 'acquire', session_id, '--tool', 'claude', '--reason', reason],\n"
    "            timeout=3,\n"
    "        )\n"
    "except Exception:\n"
    "    pass\n"
)

_RELEASE_CODE = (
    "import json, subprocess, sys\n"
    "try:\n"
    "    data = json.load(sys.stdin)\n"
    "    session_id = data.get('session_id') or ''\n"
    "    if session_id:\n"
    f"        subprocess.run([{_CLI_PATH!r}, 'release', session_id], timeout=3)\n"
    "except Exception:\n"
    "    pass\n"
)

# PreToolUse hook that wraps Bash commands to track background command PIDs.
# The epilogue captures `jobs -p` after the original command exits and reports
# them to the daemon via `6ix9ine track`. Prologue reports the tool shell PID
# itself if run_in_background: true.
_BASH_HOOK_CODE = (
    "import json, subprocess, sys\n"
    "try:\n"
    "    data = json.load(sys.stdin)\n"
    "    session_id = data.get('session_id') or ''\n"
    "    command = data.get('tool_input', {}).get('command') or ''\n"
    "    run_in_background = data.get('tool_input', {}).get('run_in_background', False)\n"
    "    if not session_id or not command:\n"
    "        print(json.dumps(data))\n"
    "        sys.exit(0)\n"
    "    prologue = ''\n"
    "    if run_in_background:\n"
    "        prologue = f'{_CLI_PATH!r} track {session_id!r} --tool claude --pids $$ >/dev/null 2>&1; '\n"
    "    epilogue = (f'; __69_rc=$?; __69_pids=$(jobs -p); '\n"
    "                f'[ -n \"$__69_pids\" ] && {_CLI_PATH!r} track {session_id!r} --tool claude --pids $__69_pids >/dev/null 2>&1; '\n"
    "                f'exit $__69_rc')\n"
    "    wrapped_command = prologue + command + epilogue\n"
    "    data['tool_input']['command'] = wrapped_command\n"
    "    print(json.dumps(data))\n"
    "except Exception:\n"
    "    print(json.dumps(data) if 'data' in dir() else '{}')\n"
)


def detect() -> bool:
    return CONFIG_DIR.exists()


def _load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _make_group(code: str) -> dict:
    return {
        "hooks": [
            {
                "type": "command",
                "command": sys.executable,
                "args": ["-c", code],
            }
        ]
    }


def _contains_our_group(groups: list, code: str) -> bool:
    # Matched on args only (not "command"), so this stays correct even if
    # install() and verify()/uninstall() run under different interpreters
    # (e.g. in tests) -- the code payload is what identifies our entry.
    for group in groups:
        for hook in group.get("hooks", []):
            if hook.get("type") == "command" and hook.get("args") == ["-c", code]:
                return True
    return False


def _make_bash_hook_group() -> dict:
    """PreToolUse hook with Bash matcher for tracking background command PIDs."""
    return {
        "matcher": "Bash",
        "hooks": [
            {
                "type": "command",
                "command": sys.executable,
                "args": ["-c", _BASH_HOOK_CODE],
            }
        ],
    }


def install() -> dict:
    if SETTINGS_FILE.exists():
        shutil.copy(SETTINGS_FILE, SETTINGS_FILE.with_suffix(SETTINGS_FILE.suffix + ".bak"))

    settings = _load_settings()
    hooks = settings.setdefault("hooks", {})

    prompt_group = hooks.setdefault("UserPromptSubmit", [])
    if not _contains_our_group(prompt_group, _ACQUIRE_CODE):
        prompt_group.append(_make_group(_ACQUIRE_CODE))

    stop_group = hooks.setdefault("Stop", [])
    if not _contains_our_group(stop_group, _RELEASE_CODE):
        stop_group.append(_make_group(_RELEASE_CODE))

    pretooluse_groups = hooks.setdefault("PreToolUse", [])
    bash_group_exists = any(
        g.get("matcher") == "Bash" and _contains_our_group([g], _BASH_HOOK_CODE)
        for g in pretooluse_groups
    )
    if not bash_group_exists:
        pretooluse_groups.append(_make_bash_hook_group())

    # Add Bash(6ix9ine track:*) to permissions.allow (idempotent)
    permissions = settings.setdefault("permissions", {})
    allow_list = permissions.setdefault("allow", [])
    bash_track_perm = "Bash(6ix9ine track:*)"
    if bash_track_perm not in allow_list:
        allow_list.append(bash_track_perm)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
    return {"ok": True, "config_path": str(SETTINGS_FILE)}


def uninstall() -> dict:
    if not SETTINGS_FILE.exists():
        return {"ok": True}

    settings = _load_settings()
    hooks = settings.get("hooks", {})

    for event, code in (("UserPromptSubmit", _ACQUIRE_CODE), ("Stop", _RELEASE_CODE)):
        remaining = [group for group in hooks.get(event, []) if not _contains_our_group([group], code)]
        if remaining:
            hooks[event] = remaining
        else:
            hooks.pop(event, None)

    # Remove our Bash PreToolUse hook
    pretooluse = hooks.get("PreToolUse", [])
    remaining_pretooluse = [
        g for g in pretooluse
        if not (g.get("matcher") == "Bash" and _contains_our_group([g], _BASH_HOOK_CODE))
    ]
    if remaining_pretooluse:
        hooks["PreToolUse"] = remaining_pretooluse
    else:
        hooks.pop("PreToolUse", None)

    # Remove Bash track permission
    permissions = settings.get("permissions", {})
    allow_list = permissions.get("allow", [])
    permissions["allow"] = [p for p in allow_list if p != "Bash(6ix9ine track:*)"]
    if not permissions["allow"]:
        permissions.pop("allow", None)
    if not permissions:
        settings.pop("permissions", None)

    if not hooks:
        settings.pop("hooks", None)

    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
    return {"ok": True}


def verify() -> bool:
    settings = _load_settings()
    hooks = settings.get("hooks", {})
    # Check UserPromptSubmit, Stop, and PreToolUse Bash hook
    has_acquire = _contains_our_group(hooks.get("UserPromptSubmit", []), _ACQUIRE_CODE)
    has_release = _contains_our_group(hooks.get("Stop", []), _RELEASE_CODE)
    pretooluse = hooks.get("PreToolUse", [])
    has_bash_hook = any(
        g.get("matcher") == "Bash" and _contains_our_group([g], _BASH_HOOK_CODE)
        for g in pretooluse
    )
    return has_acquire and has_release and has_bash_hook
