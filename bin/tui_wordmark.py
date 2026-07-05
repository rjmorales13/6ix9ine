"""
Terminal banner rendering for "6ix9ine" using half-block pixel art.

The banner uses a clever half-block technique: 8 pixel rows become 4 terminal
rows by pairing pixels vertically and mapping them to Unicode half-block
characters:
  (top, bottom): █=both, ▀=top only, ▄=bottom only, space=neither

Digits (6, 9) are chunky and 8 pixels tall. Script glyphs (i, x, n, e) are
thin, slanted, 6 pixels tall, and bottom-aligned within the 8-pixel space.
"""
from __future__ import annotations

from rich.text import Text

# Colors
DIGIT_COLOR_6 = "#1f1a18"
DIGIT_COLOR_9 = "#18201b"
SCRIPT_COLORS = {
    "i1": "#8a6c48",
    "x": "#88824c",
    "i2": "#4c688a",
    "n": "#6f5a88",
    "e": "#845270",
}
TAGLINE_COLOR = "#565e68"
TAGLINE = "— the snitch that rats on sleep"
COLLAPSE_HEIGHT = 30

# Glyph bitmaps (8 rows for digits, 6 rows for scripts)
DIGIT_GLYPHS = {
    "6": (
        ".####.",
        "#.....",
        "#.....",
        "#####.",
        "#....#",
        "#....#",
        "#....#",
        ".####.",
    ),
    "9": (
        ".####.",
        "#....#",
        "#....#",
        "#....#",
        ".#####",
        ".....#",
        ".....#",
        ".####.",
    ),
}

SCRIPT_GLYPHS = {
    "i": (
        ".#..",
        "....",
        ".#..",
        ".#..",
        "#...",
        "###.",
    ),
    "x": (
        "#...#",
        ".#.#.",
        ".###.",
        ".###.",
        ".#.#.",
        "#...#",
    ),
    "n": (
        ".....",
        ".....",
        "#.##.",
        "##..#",
        "#...#",
        "#...#",
    ),
    "e": (
        ".###.",
        "#....",
        "####.",
        "#....",
        "#....",
        ".###.",
    ),
}


def should_collapse(terminal_height: int) -> bool:
    """Return True if terminal_height < COLLAPSE_HEIGHT, False otherwise."""
    return terminal_height < COLLAPSE_HEIGHT


def render_banner() -> Text:
    """Render the full 6ix9ine banner with half-block pixel art.

    Returns a Text object with 4 terminal rows (3 newlines), colored letters,
    and exactly 8 half-block rows of pixel art. Total width <= 78 columns.
    """
    letters = [
        ("6", DIGIT_GLYPHS["6"], DIGIT_COLOR_6),
        ("i", SCRIPT_GLYPHS["i"], SCRIPT_COLORS["i1"]),
        ("x", SCRIPT_GLYPHS["x"], SCRIPT_COLORS["x"]),
        ("9", DIGIT_GLYPHS["9"], DIGIT_COLOR_9),
        ("i", SCRIPT_GLYPHS["i"], SCRIPT_COLORS["i2"]),
        ("n", SCRIPT_GLYPHS["n"], SCRIPT_COLORS["n"]),
        ("e", SCRIPT_GLYPHS["e"], SCRIPT_COLORS["e"]),
    ]

    # Prepare glyph rows (pad scripts to 8 rows with 2 blank rows on top)
    prepared_glyphs = []
    for letter_name, glyph, color in letters:
        if letter_name in ("6", "9"):
            glyph_rows = list(glyph)
        else:
            # Script glyphs: 6 rows, pad 2 blank rows on top for bottom alignment
            blank_row = "." * len(glyph[0])
            glyph_rows = [blank_row, blank_row] + list(glyph)
        prepared_glyphs.append((glyph_rows, color))

    text = Text()

    # Render 4 terminal rows (each maps to 2 pixel rows)
    for terminal_row_idx in range(4):
        top_row_idx = terminal_row_idx * 2
        bottom_row_idx = top_row_idx + 1

        for letter_idx, (glyph_rows, color) in enumerate(prepared_glyphs):
            top_pixels = glyph_rows[top_row_idx]
            bottom_pixels = glyph_rows[bottom_row_idx]

            # Convert pixel pairs to half-block characters
            for col in range(len(top_pixels)):
                top_pixel = top_pixels[col] == "#"
                bottom_pixel = bottom_pixels[col] == "#"

                if top_pixel and bottom_pixel:
                    char = "█"
                elif top_pixel:
                    char = "▀"
                elif bottom_pixel:
                    char = "▄"
                else:
                    char = " "

                text.append(char, style=color)

            # Add gap between letters (1 column), except after last letter
            if letter_idx < len(prepared_glyphs) - 1:
                text.append(" ")

        # Add newlines between terminal rows (3 total: after rows 0, 1, 2)
        if terminal_row_idx < 3:
            text.append("\n")

    return text


def render_collapsed() -> Text:
    """Render the collapsed single-line version: 6ix9ine + tagline.

    Returns a Text object with the 7-character wordmark colored individually,
    followed by a space and the TAGLINE in TAGLINE_COLOR. No newlines.
    """
    text = Text()

    letters = [
        ("6", DIGIT_COLOR_6),
        ("i", SCRIPT_COLORS["i1"]),
        ("x", SCRIPT_COLORS["x"]),
        ("9", DIGIT_COLOR_9),
        ("i", SCRIPT_COLORS["i2"]),
        ("n", SCRIPT_COLORS["n"]),
        ("e", SCRIPT_COLORS["e"]),
    ]

    for char, color in letters:
        text.append(char, style=color)

    text.append(" ")
    text.append(TAGLINE, style=TAGLINE_COLOR)

    return text
