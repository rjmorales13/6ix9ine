from __future__ import annotations

import re
import subprocess
from typing import Callable, Optional

_CPU_TEMP_PATTERN = re.compile(r"CPU die temperature:\s*([\d.]+)\s*C", re.IGNORECASE)


def parse_cpu_temperature(powermetrics_output: str) -> float:
    """Parse the CPU die temperature line out of `powermetrics --samplers smc` output."""
    match = _CPU_TEMP_PATTERN.search(powermetrics_output)
    if not match:
        raise LookupError("CPU die temperature not found in powermetrics output")
    return float(match.group(1))


def read_cpu_temperature(run: Callable = subprocess.run) -> float:
    """Sample CPU temperature. Must run as root (only the privileged helper can call this)."""
    result = run(
        ["powermetrics", "--samplers", "smc", "-i1", "-n1"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return parse_cpu_temperature(result.stdout)


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
