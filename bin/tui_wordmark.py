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
MIN_PENGUIN_HEIGHT = 34
MIN_PENGUIN_WIDTH = 70
HEADER_PADDING = 2

PENGUIN = (
    ".....DDDDDD.....",
    "...DDDDDDDDDD...",
    "..DDFFDDDDFFDD..",
    "..DFFHFFFFHFFD..",
    "..DFFKFFFFKFFD..",
    "..DFFFFOFFFFFD..",
    "...DFFFOFFFD....",
    "...DTTTTTTTD....",
    "..DTTtttTTtDD...",
    ".DDDFFFFFTtDDD..",
    ".DDFFFFFFFtDDD..",
    ".DOFFFFFFFttOD..",
    "..DDFFFFFFDD....",
    "...DDFFFFDD.....",
    "...OODDDDOO.....",
    "..OOOO..OOOO....",
)
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


def render_header(terminal_height: int, terminal_width: int) -> Text:
    header = render_banner()
    header.append("\n")
    header.append(TAGLINE, style=TAGLINE_COLOR)
    if terminal_height < MIN_PENGUIN_HEIGHT or terminal_width < MIN_PENGUIN_WIDTH:
        return header

    title = header.split()
    header = Text()
    penguin_column = terminal_width - HEADER_PADDING - len(PENGUIN[0])

    for row, (top, bottom) in enumerate(zip(PENGUIN[::2], PENGUIN[1::2])):
        if row:
            header.append("\n")
        title_line = title[row] if row < len(title) else Text()
        header.append_text(title_line)
        header.append(" " * (penguin_column - title_line.cell_len))

        for upper, lower in zip(top, bottom):
            foreground = PENGUIN_COLORS.get(upper)
            background = PENGUIN_COLORS.get(lower)
            if foreground:
                header.append("▀", style=Style(color=foreground, bgcolor=background))
            elif background:
                header.append("▄", style=Style(color=background))
            else:
                header.append(" ")

    return header


def render_collapsed() -> Text:
    text = Text()
    stay, woke = DISPLAY_NAME.split()
    text.append(stay, style=STAY_COLOR)
    text.append(" ")
    text.append(woke, style=WOKE_COLOR)
    text.append(" ")
    text.append(TAGLINE, style=TAGLINE_COLOR)
    return text
