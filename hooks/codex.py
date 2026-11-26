from __future__ import annotations

import json
import os
import shlex
import shutil
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from hooks import command_name

AGENT_NAME = "codex"
CONFIG_DIR = Path.home() / ".codex"
_EVENTS = {
    "PreModelRequest": ("hook-acquire", 10),
    "PostModelRequest": ("hook-release", 10),
    "Stop": ("hook-release", 10),
    "Interrupt": ("hook-release", 3),
    "SessionEnd": ("hook-release", 3),
}


def _config_dir() -> Path:
    override = os.environ.get("CODEX_HOME")
    return Path(override).expanduser() if override else CONFIG_DIR


def detect() -> bool:
    return _config_dir().is_dir() or shutil.which("codex") is not None


def _command(subcommand: str) -> str:
    name = command_name()
    if getattr(sys, "frozen", False):
        # PyInstaller resolves sys.executable to the versioned binary, while
        # argv[0] can retain Homebrew's stable symlink.
        cli = sys.executable
        launcher = shutil.which(sys.argv[0])
        if launcher and Path(launcher).name in {"staywoke", "6ix9ine"}:
            try:
                if os.path.samefile(launcher, cli):
                    cli = launcher
            except OSError:
                pass
    else:
        cli = shutil.which(name) or str(Path.home() / ".local/bin" / name)
    return shlex.join([os.path.abspath(cli), subcommand, "--tool", AGENT_NAME])


def _load(path: Path) -> dict:
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(settings, dict) or not isinstance(settings.get("hooks", {}), dict):
        raise ValueError("expected a JSON object containing a hooks object")
    return settings


def _is_ours(hook: dict, subcommand: str) -> bool:
    if hook.get("type") != "command" or not isinstance(hook.get("command"), str):
        return False
    try:
        argv = shlex.split(hook["command"])
    except ValueError:
        return False
    return (
        len(argv) == 4
        and Path(argv[0]).name in {"staywoke", "6ix9ine"}
        and argv[1:] == [subcommand, "--tool", AGENT_NAME]
    )


def _groups(hooks: dict, event: str) -> list:
    groups = hooks.get(event, [])
    if not isinstance(groups, list) or any(
        not isinstance(group, dict)
        or not isinstance(group.get("hooks"), list)
        or any(not isinstance(hook, dict) for hook in group["hooks"])
        for group in groups
    ):
        raise ValueError(f"invalid {event} hook groups")
    return groups


def _write(path: Path, settings: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as temp:
        try:
            json.dump(settings, temp, indent=2)
            temp.write("\n")
            temp.close()
            os.replace(temp.name, path)
        finally:
            Path(temp.name).unlink(missing_ok=True)


def _configure(installing: bool) -> dict:
    path = _config_dir() / "hooks.json"
    try:
        path = path.resolve()
        settings = _load(path)
        original = settings.get("hooks", {})
        hooks = dict(original)
        # Remove the acquire hook registered by earlier Stay Woke installs.
        managed = {**_EVENTS, "UserPromptSubmit": ("hook-acquire", None)}
        for event, (subcommand, timeout) in managed.items():
            updated = []
            for group in _groups(original, event):
                handlers = [hook for hook in group["hooks"] if not _is_ours(hook, subcommand)]
                if handlers == group["hooks"]:
                    updated.append(group)
                elif handlers:
                    updated.append({**group, "hooks": handlers})

            if installing and timeout is not None:
                updated.append({"hooks": [
                    {"type": "command", "command": _command(subcommand), "timeout": timeout}
                ]})
            if updated:
                hooks[event] = updated
            elif event in original and original[event]:
                hooks.pop(event)

        if hooks != original:
            if hooks:
                settings["hooks"] = hooks
            else:
                settings.pop("hooks", None)
            _write(path, settings)
    except (OSError, ValueError, RuntimeError) as exc:
        return {"ok": False, "error": f"Cannot update Codex hooks at {path}: {exc}"}
    return {"ok": True, "config_path": str(path)}


def install() -> dict:
    return _configure(installing=True)


def uninstall() -> dict:
    return _configure(installing=False)


def verify() -> bool:
    try:
        hooks = _load(_config_dir() / "hooks.json").get("hooks", {})
        return all(
            any(_is_ours(hook, subcommand) for group in _groups(hooks, event) for hook in group["hooks"])
            for event, (subcommand, _) in _EVENTS.items()
        )
    except (OSError, ValueError):
        return False
