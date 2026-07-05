from __future__ import annotations


class IdleTracker:
    """Flags a PID idle once its CPU usage has stayed below threshold for long enough."""

    def __init__(self, idle_timeout_seconds: float, cpu_threshold: float = 1.0) -> None:
        self.idle_timeout_seconds = idle_timeout_seconds
        self.cpu_threshold = cpu_threshold
        self._last_active: dict[int, float] = {}

    def observe(self, pid: int, cpu_percent: float, now: float) -> bool:
        """Record a CPU sample; return True once pid has been idle >= timeout."""
        if cpu_percent > self.cpu_threshold or pid not in self._last_active:
            self._last_active[pid] = now
            return False
        return (now - self._last_active[pid]) >= self.idle_timeout_seconds

    def forget(self, pid: int) -> None:
        self._last_active.pop(pid, None)
