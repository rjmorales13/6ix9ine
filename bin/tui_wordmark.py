"""Render the Stay Woke dashboard header with terminal half blocks."""
from __future__ import annotations

from rich.console import Console, ConsoleOptions, RenderResult
from rich.style import Style
from rich.text import Text

from shared import DISPLAY_NAME

STAY_COLOR = "#8a6c48"
WOKE_COLOR = "#6f5a88"
TAGLINE_COLOR = "#565e68"
TAGLINE = "— keeps your Mac awake while agents work"
COLLAPSE_HEIGHT = 30
MOUNTAIN_PIXELS = (
    "DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD",
    "DBBBDBBBBBDDDBBBDDDBDDBSMBDDBBBBBDDD",
    "DDDDDDDDDDBDDBCCCCCBCCSSMBBDDBDDDDBB",
    "DDDDDDDBBCCCCCCCRRRRSMSSBBBBSSBDDDDD",
    "DBMMSMBDDDDBCMMCCRACMSSMMBMBMMMSSMBD",
    "BBBBBBMMMMSMMBMSMMBMSMMSMBMMMBBBMBMB",
    "BMMBBBMMBMMSSMSSMMMMBMMBBBBBBMMMSSMB",
    "MSSSSSSSSSSSSSSSRRSSSSSSSSSSSSSSSSSM",
    "MSSSSISSSSSSSSSSSMPSSSSSSSSSSSSISSSM",
    "MSSSSSSSSSSSRSSSSPPPSSSSSSSSSSSSSSSM",
    "MSSSSSSSSSSSSSSSSPPSMBSSSSSSSSSSSSSM",
    "BMMMMMMMMMMMMMMBMMMMMBBMMMMMMMMMMMMB",
)
MOUNTAIN_SCENE_HEIGHT = len(MOUNTAIN_PIXELS) // 2
MOUNTAIN_COLORS = {
    "D": "#141922",
    "B": "#2a3548",
    "M": "#465469",
    "S": "#5c6f8a",
    "I": "#8c9db2",
    "C": "#695256",
    "R": "#b5775d",
    "A": "#ffad4a",
    "P": "#0a0d13",
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


class MountainScene:
    """Fit the artwork within the pane while preserving its proportions."""

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        source_width = len(MOUNTAIN_PIXELS[0])
        columns_per_row = source_width // MOUNTAIN_SCENE_HEIGHT
        height = min(MOUNTAIN_SCENE_HEIGHT, options.max_width // columns_per_row)
        width = height * columns_per_row
        scene = Text(no_wrap=True)
        padding = " " * ((options.max_width - width) // 2)
        for row in range(height):
            if row:
                scene.append("\n")
            scene.append(padding)
            top = MOUNTAIN_PIXELS[(4 * row + 1) * MOUNTAIN_SCENE_HEIGHT // (2 * height)]
            bottom = MOUNTAIN_PIXELS[(4 * row + 3) * MOUNTAIN_SCENE_HEIGHT // (2 * height)]
            for column in range(width):
                pixel = (2 * column + 1) * source_width // (2 * width)
                scene.append("▀", style=Style(color=MOUNTAIN_COLORS[top[pixel]],
                                              bgcolor=MOUNTAIN_COLORS[bottom[pixel]]))
        yield scene


def render_collapsed() -> Text:
    text = Text()
    stay, woke = DISPLAY_NAME.split()
    text.append(stay, style=STAY_COLOR)
    text.append(" ")
    text.append(woke, style=WOKE_COLOR)
    text.append(" ")
    text.append(TAGLINE, style=TAGLINE_COLOR)
    return text
