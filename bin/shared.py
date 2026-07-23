from __future__ import annotations

import os
import re
from pathlib import Path

VERSION = "1.0.0"
CODENAME = "Gummo"

VALID_AGENTS = {"claude", "opencode", "codex", "antigravity", "manual"}

HELPER_BUNDLE_ID = "com.rjmorales.6ix9ine.helper"
DAEMON_BUNDLE_ID = "com.rjmorales.6ix9ine.daemon"

HELPER_SOCKET_PATH = Path("/var/run/6ix9ine-helper.sock")
HELPER_LOG_PATH = Path("/var/log/6ix9ine-helper.log")
HELPER_INSTALL_PATH = Path("/Library/PrivilegedHelperTools") / HELPER_BUNDLE_ID
HELPER_PLIST_PATH = Path("/Library/LaunchDaemons") / f"{HELPER_BUNDLE_ID}.plist"
DAEMON_PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{DAEMON_BUNDLE_ID}.plist"

# Exit codes, per docs/API.md
EXIT_OK = 0
EXIT_GENERAL_ERROR = 1
EXIT_INVALID_ARGS = 2
EXIT_DAEMON_NOT_RUNNING = 3
EXIT_HELPER_NOT_RUNNING = 4
EXIT_PERMISSION_DENIED = 5
EXIT_AGENT_NOT_DETECTED = 6
EXIT_SESSION_NOT_FOUND = 7

_DURATION_PATTERN = re.compile(
    r"^(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+)s)?$"
)


def version_string() -> str:
    return f"6ix9ine v{VERSION} ({CODENAME})"


def state_dir() -> Path:
    override = os.environ.get("SIXNINE_STATE_DIR")
    if override:
        return Path(override)
    return Path.home() / "Library" / "Application Support" / "6ix9ine"


def socket_path() -> Path:
    return state_dir() / "cli.sock"


def state_file_path() -> Path:
    return state_dir() / "state.json"


def filter_file_path() -> Path:
    return state_dir() / "filter.json"


# Thermal color-band boundaries (Celsius). Single source of truth shared by
# the CLI (bin/cli.py) and the dashboard (bin/tui.py) so they never desync.
THERMAL_COOL_MAX = 60.0
THERMAL_WARM_MAX = 80.0
THERMAL_HOT_MAX = 95.0


# Daemon start/stop readiness polling. After `launchctl load` returns, the
# LaunchAgent still needs a moment to fork and open its cli.sock socket, so a
# start is only "ok" once the daemon is actually reachable (not merely because
# launchctl exited 0 — legacy `launchctl load` can exit 0 while doing nothing).
DAEMON_START_POLL_ATTEMPTS = 50
DAEMON_START_POLL_DELAY = 0.2  # seconds -> up to ~10s total
DAEMON_STOP_POLL_ATTEMPTS = 25
DAEMON_STOP_POLL_DELAY = 0.2  # seconds -> up to ~5s total

# Privileged-helper setup/teardown readiness polling. After the sudo script
# runs, the just-registered LaunchDaemon needs a moment to (re)fork and open its
# root socket. Setup success is confirmed by a VERSION HANDSHAKE — the process
# now answering the socket must report the CURRENT version, not merely be
# reachable: after `brew upgrade` a stale KeepAlive helper keeps answering the
# same socket with OLD code, so a bare reachability check would rubber-stamp the
# exact staleness bug. Teardown success is confirmed by the socket going dark.
HELPER_START_POLL_ATTEMPTS = 50
HELPER_START_POLL_DELAY = 0.2  # seconds -> up to ~10s total
HELPER_STOP_POLL_ATTEMPTS = 25
HELPER_STOP_POLL_DELAY = 0.2  # seconds -> up to ~5s total


def thermal_threshold() -> float:
    # Cutout fires at/above this temperature; the daemon releases all sessions.
    return float(os.environ.get("SIXNINE_THERMAL_THRESHOLD", "85"))


def thermal_alert_threshold() -> float:
    # Advisory warning temperature: the CLI's `thermal status` prints an
    # "approaching cutout" note once the current reading reaches this, before
    # the hard cutout at thermal_threshold().
    return float(os.environ.get("SIXNINE_THERMAL_ALERT", "70"))


def idle_timeout_minutes() -> int:
    return int(os.environ.get("SIXNINE_IDLE_TIMEOUT", "5"))


def session_max_age_hours() -> float:
    # Hard defense-in-depth backstop (see daemon.py's tick()): any session
    # older than this, regardless of pid/create_time state, is force-released.
    # Generous by design -- acquire() refreshes `timestamp` on every
    # re-acquire, so an actively-worked-on session never approaches this;
    # only a genuinely abandoned one (e.g. a crashed agent whose pid got
    # reused, evading the create_time guard) does.
    return float(os.environ.get("SIXNINE_SESSION_MAX_AGE_HOURS", "4"))


def sniffing_enabled() -> bool:
    value = os.environ.get("SIXNINE_SNIFFING", "true").strip().lower()
    return value in ("true", "1", "yes", "on")


def log_level() -> str:
    return os.environ.get("SIXNINE_LOG_LEVEL", "info")


def parse_duration(text: str) -> float:
    """Parse durations like '30m', '2h', '1h30m', '45s', or a bare seconds count."""
    text = text.strip()
    if not text:
        raise ValueError("duration cannot be empty")

    if text.isdigit():
        return float(int(text))

    match = _DURATION_PATTERN.match(text)
    if not match or not any(match.groups()):
        raise ValueError(f"invalid duration: {text!r}")

    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return float(hours * 3600 + minutes * 60 + seconds)


def format_duration(total_seconds: float) -> str:
    """Render a second count as human-readable held_for/expires_in text."""
    total = int(total_seconds)
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"
