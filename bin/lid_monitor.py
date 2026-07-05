from __future__ import annotations

import re
import subprocess
from typing import Callable

_CLAMSHELL_PATTERN = re.compile(r'"AppleClamshellState"\s*=\s*(Yes|No)')


def parse_clamshell_state(ioreg_output: str) -> str:
    """Parse `ioreg -r -k AppleClamshellState -d 4` output into 'open'/'closed'."""
    match = _CLAMSHELL_PATTERN.search(ioreg_output)
    if not match:
        raise LookupError("AppleClamshellState not found in ioreg output")
    return "closed" if match.group(1) == "Yes" else "open"


def read_lid_state(run: Callable = subprocess.run) -> str:
    result = run(
        ["ioreg", "-r", "-k", "AppleClamshellState", "-d", "4"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    return parse_clamshell_state(result.stdout)


class LidMonitor:
    """Tracks lid open/closed transitions so callers can react only on change."""

    def __init__(self) -> None:
        self.state: str = "unknown"

    def observe(self, state: str) -> bool:
        """Record a reading; return True only when it differs from a known prior state."""
        previous = self.state
        self.state = state
        return previous != "unknown" and state != previous
