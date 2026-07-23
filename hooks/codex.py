from __future__ import annotations

from pathlib import Path

# Status: pending research (see docs/HOOKS.md). Codex CLI's
# hook/plugin/MCP surface is unconfirmed, so this module only detects a
# plausible config directory and refuses to silently no-op an install.
AGENT_NAME = "codex"
CONFIG_DIR = Path.home() / ".codex"

_PENDING_MESSAGE = (
    "codex hook integration is pending research; see docs/HOOKS.md "
    "(process-sniffing fallback can be enabled via SIXNINE_SNIFFING instead)"
)


def detect() -> bool:
    return CONFIG_DIR.exists()


def install() -> dict:
    return {"ok": False, "error": _PENDING_MESSAGE}


def uninstall() -> dict:
    return {"ok": False, "error": _PENDING_MESSAGE}


def verify() -> bool:
    return False
