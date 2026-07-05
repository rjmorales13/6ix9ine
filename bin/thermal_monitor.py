from __future__ import annotations

import re
import subprocess
from typing import Callable, Optional

_CPU_TEMP_PATTERN = re.compile(r"CPU die temperature:\s*([\d.]+)\s*C", re.IGNORECASE)
_THERMAL_PRESSURE_PATTERN = re.compile(r"Current pressure level:\s*(\w+)")

PRESSURE_TO_TEMP = {
    "Nominal": 40.0,
    "Moderate": 70.0,
    "Heavy": 85.0,
    "Critical": 95.0,
}


def parse_cpu_temperature(powermetrics_output: str) -> float:
    """Parse CPU die temperature or thermal pressure from powermetrics output.

    Tries Intel-style ``CPU die temperature`` first, then falls back to
    Apple Silicon-style ``Current pressure level``, mapping pressure
    levels to synthetic temperatures so the caller's threshold logic
    works unchanged.
    """
    match = _CPU_TEMP_PATTERN.search(powermetrics_output)
    if match:
        return float(match.group(1))

    pressure = _THERMAL_PRESSURE_PATTERN.search(powermetrics_output)
    if pressure:
        level = pressure.group(1)
        return PRESSURE_TO_TEMP.get(level, 40.0)

    raise LookupError("CPU die temperature not found in powermetrics output")


def read_cpu_temperature(run: Callable = subprocess.run) -> float:
    """Sample CPU temperature. Must run as root (only the privileged helper can call this).

    Tries ``--samplers smc`` first (Intel), then ``--samplers thermal``
    (Apple Silicon) when ``smc`` is not recognised.
    """
    for samplers in ("smc", "thermal"):
        result = run(
            ["powermetrics", "--samplers", samplers, "-i1", "-n1"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            continue
        try:
            return parse_cpu_temperature(result.stdout)
        except LookupError:
            continue
    raise LookupError("CPU die temperature not found in powermetrics output")


class ThermalMonitor:
    """Tracks current/peak temperature and fires the cutout exactly once per crossing."""

    def __init__(self, threshold: float) -> None:
        self.threshold = threshold
        self.current: Optional[float] = None
        self.peak: float = 0.0
        self.cutout_fired: bool = False

    def observe(self, temperature: float) -> bool:
        """Record a reading; return True exactly once when the threshold is first crossed."""
        self.current = temperature
        self.peak = max(self.peak, temperature)
        if temperature >= self.threshold and not self.cutout_fired:
            self.cutout_fired = True
            return True
        return False

    def reset_cutout(self) -> None:
        self.cutout_fired = False

    def to_state_dict(self) -> dict:
        return {
            "current_temp": self.current,
            "peak_temp": self.peak,
            "cutout_threshold": self.threshold,
            "cutout_fired": self.cutout_fired,
        }
