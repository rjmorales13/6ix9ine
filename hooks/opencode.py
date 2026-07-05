from __future__ import annotations

from pathlib import Path
from typing import Optional

AGENT_NAME = "opencode"
# Verified against the real, installed @opencode-ai/plugin docs and, more
# authoritatively, its actual shipped dist/index.d.ts on this machine (v1.4.10)
# -- not just the docs page, which omits payload shapes and lists a hook name
# ("session.idle" as a top-level Hooks key) that doesn't actually exist as
# such; it's really delivered through the generic `event` hook's Event union
# (see @opencode-ai/sdk's EventSessionIdle: {type: "session.idle", properties:
# {sessionID}}). Global plugins load from ~/.config/opencode/plugins/
# (plural) -- NOT ~/.opencode/plugin/, which is just where the `opencode`
# binary itself is installed, not a config/plugin-loading location at all.
PROJECT_CONFIG_DIR = Path.cwd() / ".opencode"
HOME_CONFIG_DIR = Path.home() / ".config" / "opencode"
PLUGIN_FILENAME = "6ix9ine-hook.ts"

# Absolute path to the installed CLI wrapper (see install.sh) -- deterministic
# per-$HOME, same approach used for the Claude Code hook fix.
_CLI_PATH = str(Path.home() / ".local" / "bin" / "6ix9ine")

PLUGIN_TEMPLATE = (
    'import { execSync } from "node:child_process"\n'
    "\n"
    f"const CLI = {_CLI_PATH!r}\n"
    "\n"
    "export const SixNinePlugin = async () => {\n"
    "  return {\n"
    '    "chat.message": async (input) => {\n'
    "      try {\n"
    '        execSync(`${CLI} acquire ${input.sessionID} --tool opencode --reason "opencode turn"`, { timeout: 3000 })\n'
    "      } catch (err) {\n"
    "        // 6ix9ine failing must never break an OpenCode turn\n"
    "      }\n"
    "    },\n"
    "    event: async (input) => {\n"
    '      if (input.event.type !== "session.idle") return\n'
    "      const sessionID = input.event.properties?.sessionID\n"
    "      if (!sessionID) return\n"
    "      try {\n"
    "        execSync(`${CLI} release ${sessionID}`, { timeout: 3000 })\n"
    "      } catch (err) {\n"
    "        // 6ix9ine failing must never break an OpenCode turn\n"
    "      }\n"
    "    },\n"
    "  }\n"
    "}\n"
)


def _candidate_dirs() -> list[Path]:
    return [PROJECT_CONFIG_DIR, HOME_CONFIG_DIR]


def _config_dir() -> Optional[Path]:
    for candidate in _candidate_dirs():
        if candidate.exists():
            return candidate
    return None


def detect() -> bool:
    return _config_dir() is not None


def _plugin_path() -> Path:
    config_dir = _config_dir()
    if config_dir is None:
        raise FileNotFoundError("no OpenCode configuration directory detected")
    return config_dir / "plugins" / PLUGIN_FILENAME


def install() -> dict:
    plugin_path = _plugin_path()
    plugin_path.parent.mkdir(parents=True, exist_ok=True)
    plugin_path.write_text(PLUGIN_TEMPLATE)
    return {"ok": True, "config_path": str(plugin_path)}


def uninstall() -> dict:
    try:
        plugin_path = _plugin_path()
    except FileNotFoundError:
        return {"ok": True}
    if plugin_path.exists():
        plugin_path.unlink()
        return {"ok": True, "removed": str(plugin_path)}
    return {"ok": True}


def verify() -> bool:
    try:
        return _plugin_path().exists()
    except FileNotFoundError:
        return False
