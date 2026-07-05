"""Pure-logic theme module for Textual TUI dashboard.

Color palettes, agent emojis, and held-time tier classification.
No Textual or rich imports — standard library only.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass
from typing import Optional

import shared


# Color constants for held-time states.
HELD_GREEN = "#6ee7a0"
HELD_ORANGE = "#ffb454"
HELD_RED = "#ff6b5e"
HELD_HOT = "#ff3b30"

# General palette constants.
BACKGROUND = "#0b0d10"
BORDER = "#2c333c"
BORDER_QUIET = "#232930"
TEXT = "#c7cdd6"
TEXT_DIM = "#5c6570"
TEXT_FAINT = "#4a525c"
HOLD_TEXT = "#6a7380"

# Session identity colors — kept disjoint from HELD_* colors.
SESSION_COLORS = ("#7cc4ff", "#f5d76e", "#b3e07c", "#e8e6e1")

# Agent identity emojis.
AGENT_EMOJI = {
    "claude": "🤖",
    "opencode": "🧰",
    "codex": "⌘",
    "antigravity": "🚀",
    "manual": "✋",
}

# Chip styling constants: (foreground, background).
CHIP_ACTIVE = ("#6ee7a0", "#123524")
CHIP_BLOCKED = ("#ff8fab", "#3a1220")
CHIP_SLEEP_OK = ("#7cc4ff", "#12283a")
CHIP_IDLE = ("#8b93a0", "#1a2026")


@dataclass(frozen=True)
class HeldTier:
    """Classification of a held session by elapsed time."""

    color: str
    bold: bool
    fire: bool


def held_tier(seconds: float) -> HeldTier:
    """Classify a held session by elapsed time in seconds.

    Thresholds:
    - < 300s (< 5m): green
    - 300-1799s (5m to < 30m): orange
    - 1800-2699s (30m to < 45m): red
    - 2700-3600s (45m to 1h): hot, bold
    - > 3600s (> 1h): hot, bold, fire

    Negative durations clamp to 0 (green).
    """
    clamped = max(0.0, seconds)

    if clamped < 300:
        return HeldTier(color=HELD_GREEN, bold=False, fire=False)
    elif clamped < 1800:
        return HeldTier(color=HELD_ORANGE, bold=False, fire=False)
    elif clamped < 2700:
        return HeldTier(color=HELD_RED, bold=False, fire=False)
    elif clamped <= 3600:
        return HeldTier(color=HELD_HOT, bold=True, fire=False)
    else:
        return HeldTier(color=HELD_HOT, bold=True, fire=True)


def session_color(key: str) -> str:
    """Deterministic stable mapping from session key to identity color.

    Uses zlib.crc32 for reproducibility across processes.
    """
    hash_val = zlib.crc32(key.encode("utf-8")) & 0xFFFFFFFF
    index = hash_val % len(SESSION_COLORS)
    return SESSION_COLORS[index]


def agent_label(agent: str) -> str:
    """Return a human-readable label with agent emoji and name.

    Falls back to '❓ agent_name' for unknown agents.
    """
    emoji = AGENT_EMOJI.get(agent, "❓")
    return f"{emoji} {agent}"
