from __future__ import annotations

import pytest

import shared
import tui_theme


# ---------------------------------------------------------------- held tiers
# Spec (status-view-spec.md): <5m green, 5-<30m orange, 30-<45m red,
# >=45m hot red bold, >1h adds the fire suffix.

GREEN = tui_theme.HELD_GREEN
ORANGE = tui_theme.HELD_ORANGE
RED = tui_theme.HELD_RED
HOT = tui_theme.HELD_HOT


@pytest.mark.parametrize(
    "seconds,color,bold,fire",
    [
        (0, GREEN, False, False),
        (299, GREEN, False, False),          # 4:59 → green
        (300, ORANGE, False, False),         # 5:00 → orange
        (1799, ORANGE, False, False),        # 29:59 → orange
        (1800, RED, False, False),           # 30:00 → red
        (2699, RED, False, False),           # 44:59 → red
        (2700, HOT, True, False),            # 45:00 → hot red, bold
        (3599, HOT, True, False),            # 59:59 → hot, no fire yet
        (3600, HOT, True, False),            # exactly 1h → still no fire
        (3601, HOT, True, True),             # over 1h → fire
        (7200, HOT, True, True),
    ],
)
def test_held_tier_boundaries(seconds, color, bold, fire):
    tier = tui_theme.held_tier(seconds)
    assert (tier.color, tier.bold, tier.fire) == (color, bold, fire)


def test_held_tier_clamps_negative_to_green():
    tier = tui_theme.held_tier(-5)
    assert tier.color == GREEN and not tier.bold and not tier.fire


# ---------------------------------------------------------- session identity


def test_session_color_is_deterministic():
    key = "a3f8c2e1-77aa-4b0e-9c31-08d2f4e6b5aa"
    assert tui_theme.session_color(key) == tui_theme.session_color(key)


def test_session_color_comes_from_identity_palette():
    for key in ("k1", "k2", "hold-4fa2", "a3f8c2e1"):
        assert tui_theme.session_color(key) in tui_theme.SESSION_COLORS


def test_session_colors_spread_across_palette():
    keys = [f"session-{i}" for i in range(16)]
    used = {tui_theme.session_color(k) for k in keys}
    assert len(used) > 1


def test_identity_palette_never_collides_with_held_colors():
    # Spec: a session's name color and held-time color must differ in a row.
    # Guaranteed by construction: the two palettes are disjoint.
    held = {GREEN, ORANGE, RED, HOT}
    assert held.isdisjoint(set(tui_theme.SESSION_COLORS))


# ----------------------------------------------------------------- agents


@pytest.mark.parametrize(
    "agent,emoji",
    [
        ("claude", "🤖"),
        ("opencode", "🧰"),
        ("codex", "⌘"),
        ("antigravity", "🚀"),
        ("manual", "✋"),
    ],
)
def test_agent_label_has_spec_emoji(agent, emoji):
    label = tui_theme.agent_label(agent)
    assert label == f"{emoji} {agent}"


def test_every_valid_agent_has_an_identity():
    for agent in shared.VALID_AGENTS:
        assert "❓" not in tui_theme.agent_label(agent)


def test_unknown_agent_falls_back_gracefully():
    assert tui_theme.agent_label("mystery") == "❓ mystery"


# ----------------------------------------------------------------- chips


def test_chip_styles_match_spec():
    assert tui_theme.CHIP_ACTIVE == ("#6ee7a0", "#123524")
    assert tui_theme.CHIP_BLOCKED == ("#ff8fab", "#3a1220")
    assert tui_theme.CHIP_SLEEP_OK == ("#7cc4ff", "#12283a")
    assert tui_theme.CHIP_IDLE == ("#8b93a0", "#1a2026")
