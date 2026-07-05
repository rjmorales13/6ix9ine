from __future__ import annotations

import daemon_commands
import shared
from session_registry import SessionRegistry


def test_handle_acquire_adds_session_and_reports_active():
    registry = SessionRegistry()
    response = daemon_commands.handle_acquire(
        registry, {"session": "key-1", "tool": "claude", "reason": "building"}, now=1000.0
    )
    assert response == {"ok": True, "status": "ACTIVE", "count": 1}
    # No PID is tracked: the only PID visible to the daemon is the one-shot
    # CLI call's own process, which always exits immediately -- tracking it
    # caused every session to be auto-pruned within one tick regardless of
    # how long the real work continued (see handle_acquire's docstring).
    assert registry.sessions()["key-1"].pid is None


def test_handle_acquire_requires_session_and_tool():
    registry = SessionRegistry()
    response = daemon_commands.handle_acquire(registry, {"tool": "claude"})
    assert response["ok"] is False


def test_handle_acquire_rejects_unknown_agent():
    registry = SessionRegistry()
    response = daemon_commands.handle_acquire(registry, {"session": "k", "tool": "bogus"})
    assert response["ok"] is False


def test_handle_release_reports_idle_when_last_session_released():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", now=1000.0)
    response = daemon_commands.handle_release(registry, {"session": "key-1"})
    assert response == {"ok": True, "status": "IDLE", "count": 0}


def test_handle_release_reports_session_not_found():
    registry = SessionRegistry()
    response = daemon_commands.handle_release(registry, {"session": "missing"})
    assert response["ok"] is False
    assert response["exit_code"] == shared.EXIT_SESSION_NOT_FOUND


def test_handle_hold_parses_duration_and_creates_hold():
    registry = SessionRegistry()
    response = daemon_commands.handle_hold(
        registry, {"for": "30m", "reason": "deploy", "hold_id": "hold-abc"}, now=1000.0
    )
    assert response == {"ok": True, "hold_id": "hold-abc", "expires_at": 1000.0 + 1800.0}
    assert registry.count() == 1


def test_handle_hold_generates_id_when_not_supplied():
    registry = SessionRegistry()
    response = daemon_commands.handle_hold(registry, {"for": "10m"}, now=1000.0)
    assert response["ok"] is True
    assert response["hold_id"].startswith("hold-")


def test_handle_hold_rejects_missing_duration():
    registry = SessionRegistry()
    response = daemon_commands.handle_hold(registry, {"reason": "deploy"})
    assert response["ok"] is False


def test_handle_hold_rejects_invalid_duration():
    registry = SessionRegistry()
    response = daemon_commands.handle_hold(registry, {"for": "not-a-duration"})
    assert response["ok"] is False


def test_handle_status_reports_full_snapshot():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", reason="building", pid=111, now=1000.0)

    response = daemon_commands.handle_status(
        registry,
        lid_state="closed",
        thermal_state={"current_temp": 60.0, "peak_temp": 60.0, "cutout_threshold": 85.0, "cutout_fired": False},
        sleep_blocked=True,
        now=1060.0,
    )

    assert response["ok"] is True
    assert response["status"] == "ACTIVE"
    assert response["count"] == 1
    assert response["lid"] == "closed"
    assert response["sleep_blocked"] is True
    assert response["thermal"]["current_temp"] == 60.0
    assert response["active_sessions"]["key-1"]["held_for"] == "1m 0s"


def test_handle_kill_all_releases_everything():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", now=1000.0)
    registry.add_hold("hold-1", reason="deploy", duration_seconds=60, now=1000.0)

    response = daemon_commands.handle_kill_all(registry)

    assert response == {"ok": True, "status": "IDLE", "released": 2}
    assert registry.count() == 0
