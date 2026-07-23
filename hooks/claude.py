from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

AGENT_NAME = "claude"
CONFIG_DIR = Path.home() / ".claude"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

# Fallback absolute path to the source-install CLI wrapper (see install.sh),
# used only when `6ix9ine` is not discoverable on PATH. A Homebrew install
# instead resolves via shutil.which("6ix9ine") -> <brew-prefix>/bin/6ix9ine.
_CLI_FALLBACK_PATH = str(Path.home() / ".local" / "bin" / "6ix9ine")

# Hooks are installed as `6ix9ine hook-acquire` / `6ix9ine hook-release`: the
# command is the resolved 6ix9ine binary and the sole arg is a subcommand that
# cli.py's own argparse handles. This works identically for the frozen
# PyInstaller binary (what Homebrew ships) and the source install.
#
# The PREVIOUS implementation instead installed `<python> -c "<embedded code>"`,
# reusing sys.executable as the interpreter. In the frozen binary sys.executable
# is the 6ix9ine binary itself, so `6ix9ine -c "<code>"` hit argparse, which
# rejects `-c` and exits 2. Claude Code treats exit 2 from UserPromptSubmit as a
# hard block, so every prompt submission was erased -- a real user lockout. The
# markers below let us still recognise and strip that stale/broken shape from an
# already-affected settings.json (migration / self-heal).
_ACQUIRE_SUBCOMMAND = "hook-acquire"
_RELEASE_SUBCOMMAND = "hook-release"

# Substrings that, taken together, reliably identify one of our OLD `-c`
# payloads without false-matching unrelated `python -c` hooks.
_ACQUIRE_MARKERS = ("json.load(sys.stdin)", "6ix9ine", "acquire")
_RELEASE_MARKERS = ("json.load(sys.stdin)", "6ix9ine", "release")
# The old Bash PreToolUse PID-tracking hook. It never worked even from source
# (a NameError on an undefined _CLI_PATH inside the executed snippet was
# swallowed by a bare except, printing the payload unmodified) and used the same
# exit-2-prone mechanism. It is no longer installed; these markers exist only so
# uninstall()/self-heal can strip it from an already-affected settings.json.
_BASH_MARKERS = ("json.load(sys.stdin)", "jobs -p", "track")

_BASH_TRACK_PERM = "Bash(6ix9ine track:*)"


def detect() -> bool:
    return CONFIG_DIR.exists()


def _cli_path() -> str:
    """Resolve the 6ix9ine binary to invoke from the hook.

    Prefer PATH resolution (a Homebrew install puts `6ix9ine` on PATH), then
    the frozen binary itself if we're running frozen but not yet on PATH, then
    the source-install fallback.
    """
    resolved = shutil.which("6ix9ine")
    if resolved:
        return resolved
    if getattr(sys, "frozen", False):
        return sys.executable
    return _CLI_FALLBACK_PATH


def _load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _make_group(subcommand: str) -> dict:
    return {
        "hooks": [
            {
                "type": "command",
                "command": _cli_path(),
                "args": [subcommand],
            }
        ]
    }


def _is_our_hook(hook: dict, subcommand: str | None, markers: tuple[str, ...]) -> bool:
    """True if `hook` is one of ours -- either the current subcommand shape or a
    stale old `-c "<embedded code>"` shape identified by all of `markers`."""
    if not isinstance(hook, dict) or hook.get("type") != "command":
        return False
    args = hook.get("args") or []
    if subcommand is not None and list(args[:1]) == [subcommand]:
        return True
    if len(args) >= 2 and args[0] == "-c":
        code = args[1] or ""
        return all(marker in code for marker in markers)
    return False


def _contains_our_group(groups: list, subcommand: str | None, markers: tuple[str, ...]) -> bool:
    for group in groups:
        for hook in group.get("hooks", []):
            if _is_our_hook(hook, subcommand, markers):
                return True
    return False


def _strip_our_hooks(groups: list, subcommand: str | None, markers: tuple[str, ...]) -> list:
    """Return a new group list with our hooks (old and new shape) removed;
    groups left empty by the removal are dropped, foreign groups are preserved."""
    cleaned = []
    for group in groups:
        original_hooks = group.get("hooks")
        if original_hooks is None:
            cleaned.append(group)
            continue
        kept = [h for h in original_hooks if not _is_our_hook(h, subcommand, markers)]
        if kept:
            new_group = dict(group)
            new_group["hooks"] = kept
            cleaned.append(new_group)
    return cleaned


def _remove_bash_track_permission(settings: dict) -> None:
    """Strip the stale Bash(6ix9ine track:*) permission the old installer added."""
    permissions = settings.get("permissions")
    if not isinstance(permissions, dict):
        return
    allow_list = permissions.get("allow")
    if not isinstance(allow_list, list) or _BASH_TRACK_PERM not in allow_list:
        return
    permissions["allow"] = [p for p in allow_list if p != _BASH_TRACK_PERM]
    if not permissions["allow"]:
        permissions.pop("allow", None)
    if not permissions:
        settings.pop("permissions", None)


def install() -> dict:
    if SETTINGS_FILE.exists():
        shutil.copy(SETTINGS_FILE, SETTINGS_FILE.with_suffix(SETTINGS_FILE.suffix + ".bak"))

    settings = _load_settings()
    hooks = settings.setdefault("hooks", {})

    # Self-heal + install: strip any stale/broken or duplicate 6ix9ine entries
    # first, then append exactly one current-shape group. Re-running install
    # after an upgrade therefore auto-repairs an already-affected user.
    for event, subcommand, markers in (
        ("UserPromptSubmit", _ACQUIRE_SUBCOMMAND, _ACQUIRE_MARKERS),
        ("Stop", _RELEASE_SUBCOMMAND, _RELEASE_MARKERS),
    ):
        groups = _strip_our_hooks(hooks.get(event, []), subcommand, markers)
        groups.append(_make_group(subcommand))
        hooks[event] = groups

    # The Bash PreToolUse PID-tracking hook is intentionally NOT installed
    # (never worked; used the exit-2-prone mechanism -- see _BASH_MARKERS).
    # Still strip any stale copy so an affected user is repaired on re-install.
    pretooluse = _strip_our_hooks(hooks.get("PreToolUse", []), None, _BASH_MARKERS)
    if pretooluse:
        hooks["PreToolUse"] = pretooluse
    else:
        hooks.pop("PreToolUse", None)

    _remove_bash_track_permission(settings)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
    return {"ok": True, "config_path": str(SETTINGS_FILE)}


def uninstall() -> dict:
    if not SETTINGS_FILE.exists():
        return {"ok": True}

    settings = _load_settings()
    hooks = settings.get("hooks", {})

    for event, subcommand, markers in (
        ("UserPromptSubmit", _ACQUIRE_SUBCOMMAND, _ACQUIRE_MARKERS),
        ("Stop", _RELEASE_SUBCOMMAND, _RELEASE_MARKERS),
        ("PreToolUse", None, _BASH_MARKERS),
    ):
        remaining = _strip_our_hooks(hooks.get(event, []), subcommand, markers)
        if remaining:
            hooks[event] = remaining
        else:
            hooks.pop(event, None)

    _remove_bash_track_permission(settings)

    if not hooks:
        settings.pop("hooks", None)

    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
    return {"ok": True}


def verify() -> bool:
    settings = _load_settings()
    hooks = settings.get("hooks", {})
    has_acquire = _contains_our_group(
        hooks.get("UserPromptSubmit", []), _ACQUIRE_SUBCOMMAND, _ACQUIRE_MARKERS
    )
    has_release = _contains_our_group(hooks.get("Stop", []), _RELEASE_SUBCOMMAND, _RELEASE_MARKERS)
    return has_acquire and has_release
