from __future__ import annotations

from pathlib import Path

# Status: pending research (see 6ix9ine-rap-sheet-docs/HOOKS.md). Antigravity
# CLI (`agy`)'s plugin directory and hook events are unconfirmed, so this
# module only detects a plausible config directory and refuses to silently
# no-op an install.
AGENT_NAME = "antigravity"
CONFIG_DIR = Path.home() / ".antigravity"

_PENDING_MESSAGE = (
    "antigravity hook integration is pending research; see 6ix9ine-rap-sheet-docs/HOOKS.md "
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
