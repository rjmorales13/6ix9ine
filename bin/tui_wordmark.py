"""Render the Stay Woke dashboard header with terminal half blocks."""
from __future__ import annotations

from rich.style import Style
from rich.text import Text

from shared import DISPLAY_NAME

STAY_COLOR = "#8a6c48"
WOKE_COLOR = "#6f5a88"
TAGLINE_COLOR = "#565e68"
TAGLINE = "— keeps your Mac awake while agents work"
COLLAPSE_HEIGHT = 30
PENGUIN = (
    "...DDDDDD...",
    "..DFFFFFFD..",
    ".DFFHFFHFFD.",
    ".DFFKFFKFFD.",
    ".DFFFOOFFFD.",
    "..DFFOOFFD..",
    "..DTTTTTTD..",
    ".DDFFFFTtDD.",
    "ODFFFFFTtFDO",
    ".DFFFFFTtFD.",
    "..DDFFFFDD..",
    "..OOO..OOO..",
)
PENGUIN_HEIGHT = len(PENGUIN) // 2
PENGUIN_COLORS = {
    "D": "#404650",
    "F": "#fff3d9",
    "H": "#8394a5",
    "K": "#10141a",
    "O": "#ffa62b",
    "T": "#40cbcb",
    "t": "#18898e",
}

# Six pixel rows render as three terminal rows.
GLYPHS = {
    "S": (".####", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", ".#.#."),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", ".###."),
    "K": ("#...#", "#..#.", "###..", "#..#.", "#...#", "#...#"),
    "E": ("#####", "#....", "####.", "#....", "#....", "#####"),
}
HALF_BLOCKS = {"..": " ", "#.": "▀", ".#": "▄", "##": "█"}


def should_collapse(terminal_height: int) -> bool:
    return terminal_height < COLLAPSE_HEIGHT


def render_banner() -> Text:
    banner = Text()
    for row in range(0, 6, 2):
        if row:
            banner.append("\n")
        for word, color in zip(DISPLAY_NAME.upper().split(), (STAY_COLOR, WOKE_COLOR)):
            if word == "WOKE":
                banner.append("   ")
            glyphs = []
            for letter in word:
                top, bottom = GLYPHS[letter][row:row + 2]
                glyphs.append("".join(HALF_BLOCKS[a + b] for a, b in zip(top, bottom)))
            banner.append(" ".join(glyphs), style=color)
    return banner


def render_penguin() -> Text:
    penguin = Text()
    for row, (top, bottom) in enumerate(zip(PENGUIN[::2], PENGUIN[1::2])):
        if row:
            penguin.append("\n")
        for upper, lower in zip(top, bottom):
            foreground = PENGUIN_COLORS.get(upper)
            background = PENGUIN_COLORS.get(lower)
            if foreground:
                penguin.append("▀", style=Style(color=foreground, bgcolor=background))
            elif background:
                penguin.append("▄", style=Style(color=background))
            else:
                penguin.append(" ")
    return penguin


def render_collapsed() -> Text:
    text = Text()
    stay, woke = DISPLAY_NAME.split()
    text.append(stay, style=STAY_COLOR)
    text.append(" ")
    text.append(woke, style=WOKE_COLOR)
    text.append(" ")
    text.append(TAGLINE, style=TAGLINE_COLOR)
    return text
