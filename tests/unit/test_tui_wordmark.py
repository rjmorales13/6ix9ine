from __future__ import annotations

import pytest
from rich.text import Text

import tui_wordmark


@pytest.mark.parametrize("letter", list("STAYWOKE"))
def test_glyphs_have_six_even_pixel_rows(letter):
    glyph = tui_wordmark.GLYPHS[letter]
    assert len(glyph) == 6
    assert all(len(row) == 5 and set(row) <= {"#", "."} for row in glyph)


def test_banner_renders_three_half_block_rows_in_both_colors():
    banner = tui_wordmark.render_banner()
    assert isinstance(banner, Text)
    lines = banner.plain.splitlines()
    assert len(lines) == 3
    assert all(len(line) <= 78 for line in lines)
    assert any(char in banner.plain for char in "▀▄█")
    styles = {str(span.style) for span in banner.spans}
    assert {tui_wordmark.STAY_COLOR, tui_wordmark.WOKE_COLOR} <= styles


def test_collapsed_includes_display_name_and_tagline_on_one_line():
    collapsed = tui_wordmark.render_collapsed()
    assert collapsed.plain == f"Stay Woke {tui_wordmark.TAGLINE}"
    styles = {str(span.style) for span in collapsed.spans}
    assert tui_wordmark.TAGLINE_COLOR in styles


# ----------------------------------------------------------- collapse rule


@pytest.mark.parametrize(
    "height,collapsed",
    [(24, True), (29, True), (30, False), (40, False)],
)
def test_collapse_threshold(height, collapsed):
    assert tui_wordmark.should_collapse(height) is collapsed
