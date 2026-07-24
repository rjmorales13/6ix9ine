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

# Bare command name, NOT an absolute install-time path. Unlike Claude Code's
# hooks.json (whose "command" field is invoked directly, so hooks/claude.py's
# _cli_path() must precompute an absolute path via shutil.which/frozen-binary
# fallback), this template is executed by opencode's own execFileSync, which
# spawns through the child process's inherited PATH. Baking in an absolute
# path here (as an earlier version of this file did, hardcoded to the
# source-install location ~/.local/bin/6ix9ine) goes stale the moment the user
# switches install methods (e.g. source install -> Homebrew) without rerunning
# install() -- exactly the bug this fixes. A bare name self-heals across
# install-method changes since it re-resolves against PATH on every opencode
# turn instead of once at install time.
_CLI_PATH = "6ix9ine"

# The frozen, Homebrew-distributed binary has a PyInstaller onefile cold-start
# of ~3.2-3.7s (verified: even `6ix9ine --version`, which does zero daemon
# I/O, takes that long -- it's bootstrap overhead, not slow work). A timeout
# below that window means every real acquire/release call gets SIGTERM'd by
# execFileSync before the subprocess even finishes starting, and the
# resulting ETIMEDOUT is invisible -- swallowed by the try/catch below per
# the "6ix9ine failing must never break an OpenCode turn" contract, so
# sessions silently never register with the daemon at all. 10s comfortably
# clears the observed cold-start with real margin; confirmed live via an A/B
# test (3000ms: ETIMEDOUT every time; 10000ms: succeeds in ~3.3s and the
# session appears in `6ix9ine status`). See docs/TROUBLESHOOTING-HOOKS.md,
# Case study 6.
_ACQUIRE_RELEASE_TIMEOUT_MS = 10000

# PID sourcing: process.pid inside the plugin factory is the long-lived
# OpenCode host process's own pid, NOT a per-call worker/child. Verified
# against the actually-installed @opencode-ai/plugin's PluginInput type
# (dist/index.d.ts, v1.4.10 on this machine): it exposes `client`, `project`,
# `directory`, `worktree`, `serverUrl`, `$` -- nothing suggesting the plugin
# module runs in a separate worker/child process per call, and there's no
# child_process/worker_threads usage anywhere in the installed package's
# compiled output. The daemon resolves this pid's create_time server-side
# (see daemon_commands.handle_acquire) to guard against OS PID reuse before
# ever treating it as "still alive" -- see session_registry.py's
# Session.create_time docstring.
PLUGIN_TEMPLATE = (
    'import { execFileSync } from "node:child_process"\n'
    "\n"
    f"const CLI = {_CLI_PATH!r}\n"
    f"const TIMEOUT_MS = {_ACQUIRE_RELEASE_TIMEOUT_MS}\n"
    "\n"
    "export const SixNinePlugin = async () => {\n"
    "  return {\n"
    '    "chat.message": async (input) => {\n'
    "      try {\n"
    '        execFileSync(CLI, ["acquire", input.sessionID, "--tool", "opencode", "--reason", "opencode turn", "--pid", process.pid.toString()], { timeout: TIMEOUT_MS, stdio: "ignore" })\n'
    "      } catch (err) {\n"
    "        // 6ix9ine failing must never break an OpenCode turn\n"
    "      }\n"
    "    },\n"
    "    event: async (input) => {\n"
    '      if (input.event.type !== "session.idle") return\n'
    "      const sessionID = input.event.properties?.sessionID\n"
    "      if (!sessionID) return\n"
    "      try {\n"
    '        execFileSync(CLI, ["release", sessionID], { timeout: TIMEOUT_MS, stdio: "ignore" })\n'
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
