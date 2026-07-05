from __future__ import annotations

import pytest
from rich.text import Text

import tui_wordmark


# ------------------------------------------------------------------ glyphs
# Digits are chunky terminal-mono glyphs, 8 pixel-rows tall (4 terminal rows
# via half-blocks). Script letters are thin/slanted, 6 pixel-rows tall,
# bottom-aligned. Bitmaps use '#' for on and '.' for off.


def _assert_bitmap(rows, expected_height):
    assert len(rows) == expected_height
    widths = {len(r) for r in rows}
    assert len(widths) == 1, "glyph rows must be uniform width"
    assert widths.pop() >= 3
    joined = "".join(rows)
    assert set(joined) <= {"#", "."}
    assert "#" in joined


@pytest.mark.parametrize("ch", ["6", "9"])
def test_digit_glyphs_are_8px_tall(ch):
    _assert_bitmap(tui_wordmark.DIGIT_GLYPHS[ch], 8)


@pytest.mark.parametrize("ch", ["i", "x", "n", "e"])
def test_script_glyphs_are_6px_tall(ch):
    _assert_bitmap(tui_wordmark.SCRIPT_GLYPHS[ch], 6)


# ------------------------------------------------------------------ colors


def test_wordmark_colors_match_spec():
    assert tui_wordmark.DIGIT_COLOR_6 == "#1f1a18"
    assert tui_wordmark.DIGIT_COLOR_9 == "#18201b"
    assert tui_wordmark.SCRIPT_COLORS == {
        "i1": "#8a6c48",
        "x": "#88824c",
        "i2": "#4c688a",
        "n": "#6f5a88",
        "e": "#845270",
    }
    assert tui_wordmark.TAGLINE_COLOR == "#565e68"


# ------------------------------------------------------------------ banner


def test_banner_is_four_terminal_rows():
    banner = tui_wordmark.render_banner()
    assert isinstance(banner, Text)
    assert banner.plain.count("\n") == 3  # 8 pixel rows → 4 half-block lines


def test_banner_uses_half_block_characters():
    plain = tui_wordmark.render_banner().plain
    assert any(ch in plain for ch in "▀▄█")


def test_banner_fits_an_80_column_terminal():
    for line in tui_wordmark.render_banner().plain.split("\n"):
        assert len(line) <= 78


def test_banner_carries_every_letter_color():
    banner = tui_wordmark.render_banner()
    styles = " ".join(str(span.style) for span in banner.spans)
    for color in (
        tui_wordmark.DIGIT_COLOR_6,
        tui_wordmark.DIGIT_COLOR_9,
        *tui_wordmark.SCRIPT_COLORS.values(),
    ):
        assert color in styles


# ---------------------------------------------------------------- collapsed


def test_collapsed_is_single_line_with_wordmark_and_tagline():
    collapsed = tui_wordmark.render_collapsed()
    assert isinstance(collapsed, Text)
    assert "\n" not in collapsed.plain
    assert "6ix9ine" in collapsed.plain
    assert tui_wordmark.TAGLINE in collapsed.plain


def test_collapsed_keeps_the_ghost_palette():
    collapsed = tui_wordmark.render_collapsed()
    styles = " ".join(str(span.style) for span in collapsed.spans)
    assert tui_wordmark.SCRIPT_COLORS["i1"] in styles
    assert tui_wordmark.TAGLINE_COLOR in styles


# ----------------------------------------------------------- collapse rule


@pytest.mark.parametrize(
    "height,collapsed",
    [(24, True), (29, True), (30, False), (40, False)],
)
def test_collapse_threshold(height, collapsed):
    assert tui_wordmark.should_collapse(height) is collapsed
