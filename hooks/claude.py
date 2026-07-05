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

    if not hooks:
        settings.pop("hooks", None)

    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
    return {"ok": True}


def verify() -> bool:
    settings = _load_settings()
    hooks = settings.get("hooks", {})
    return _contains_our_group(hooks.get("UserPromptSubmit", []), _ACQUIRE_CODE) and _contains_our_group(
        hooks.get("Stop", []), _RELEASE_CODE
    )
