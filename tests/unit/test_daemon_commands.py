from __future__ import annotations

import daemon_commands
import shared
from session_registry import CommandPid, SessionRegistry


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


# -- ACQUIRE with an explicit pid (e.g. OpenCode's chat.message --pid) ----


def test_handle_acquire_with_pid_resolves_create_time_server_side():
    """The daemon must resolve create_time itself from the pid -- never
    trust a client-sent create_time (there isn't one in the request at all)."""
    registry = SessionRegistry()

    def fake_create_time_fn(pid):
        return {4242: 12345.0}.get(pid)

    response = daemon_commands.handle_acquire(
        registry,
        {"session": "key-1", "tool": "opencode", "pid": 4242},
        create_time_fn=fake_create_time_fn,
        now=1000.0,
    )

    assert response["ok"] is True
    session = registry.sessions()["key-1"]
    assert session.pid == 4242
    assert session.create_time == 12345.0


def test_handle_acquire_without_pid_stores_no_pid_or_create_time():
    """Unchanged default path (e.g. Claude's hook-acquire): no pid at all."""
    registry = SessionRegistry()
    response = daemon_commands.handle_acquire(
        registry, {"session": "key-1", "tool": "claude"}, create_time_fn=lambda pid: 1.0, now=1000.0
    )
    assert response["ok"] is True
    session = registry.sessions()["key-1"]
    assert session.pid is None
    assert session.create_time is None


def test_handle_acquire_with_pid_falls_back_to_no_pid_when_create_time_unresolvable():
    """If create_time_fn can't resolve a create_time for the given pid (the
    process already exited / a race), storing the bare pid with no
    create_time would silently drop into prune_dead's UNGUARDED legacy
    branch (meant only for Claude's sniffed sessions) -- reintroducing the
    exact PID-reuse hole this fix closes. Must fall back to no pid at all."""
    registry = SessionRegistry()
    response = daemon_commands.handle_acquire(
        registry,
        {"session": "key-1", "tool": "opencode", "pid": 9999},
        create_time_fn=lambda pid: None,
        now=1000.0,
    )
    assert response["ok"] is True
    session = registry.sessions()["key-1"]
    assert session.pid is None
    assert session.create_time is None


def test_handle_acquire_with_pid_and_no_create_time_fn_falls_back_to_no_pid():
    registry = SessionRegistry()
    response = daemon_commands.handle_acquire(
        registry, {"session": "key-1", "tool": "opencode", "pid": 9999}, now=1000.0
    )
    assert response["ok"] is True
    session = registry.sessions()["key-1"]
    assert session.pid is None


def test_handle_acquire_ignores_client_sent_create_time():
    """A client-sent create_time field must be ignored entirely -- only the
    server-resolved value (via create_time_fn) is ever trusted."""
    registry = SessionRegistry()

    def fake_create_time_fn(pid):
        return 555.0

    response = daemon_commands.handle_acquire(
        registry,
        {"session": "key-1", "tool": "opencode", "pid": 4242, "create_time": 1.0},
        create_time_fn=fake_create_time_fn,
        now=1000.0,
    )

    assert response["ok"] is True
    assert registry.sessions()["key-1"].create_time == 555.0


def test_handle_acquire_never_adopts_peer_pid():
    """ACQUIRE has no notion of peer_pid at all -- daemon.py's
    handle_request deliberately never forwards it into the request dict
    handle_acquire receives. Confirm handle_acquire ignores any stray
    peer_pid key entirely even if present."""
    registry = SessionRegistry()
    response = daemon_commands.handle_acquire(
        registry,
        {"session": "key-1", "tool": "opencode", "peer_pid": 424242},
        create_time_fn=lambda pid: 1.0,
        now=1000.0,
    )
    assert response["ok"] is True
    session = registry.sessions()["key-1"]
    assert session.pid is None
    assert session.create_time is None


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


# -- Epilogue reporter: background command PID tracking --


def test_handle_track_registers_command_pids():
    """TRACK command registers background command PIDs with create_time."""
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", now=1000.0)

    def fake_create_time_fn(pid):
        return {1001: 999.0, 1002: 998.0}.get(pid)

    response = daemon_commands.handle_track(
        registry,
        {"session": "key-1", "tool": "claude", "pids": [1001, 1002]},
        create_time_fn=fake_create_time_fn,
        now=1000.0,
    )

    assert response["ok"] is True
    assert response["status"] == "ACTIVE"
    session = registry.sessions()["key-1"]
    assert session.command_pids == frozenset(
        {CommandPid(pid=1001, create_time=999.0), CommandPid(pid=1002, create_time=998.0)}
    )


def test_handle_track_requires_session():
    registry = SessionRegistry()

    def fake_create_time_fn(pid):
        return 100.0

    response = daemon_commands.handle_track(
        registry, {"pids": [1001]}, create_time_fn=fake_create_time_fn
    )

    assert response["ok"] is False
    assert "session" in response["error"]


def test_handle_track_skips_pids_with_no_create_time():
    """A PID with no create_time (dead or inaccessible) is silently skipped."""
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", now=1000.0)

    def fake_create_time_fn(pid):
        # 1001 is accessible, 1002 is dead
        return 999.0 if pid == 1001 else None

    response = daemon_commands.handle_track(
        registry,
        {"session": "key-1", "tool": "claude", "pids": [1001, 1002]},
        create_time_fn=fake_create_time_fn,
        now=1000.0,
    )

    assert response["ok"] is True
    session = registry.sessions()["key-1"]
    # Only the live PID is tracked
    assert session.command_pids == frozenset({CommandPid(pid=1001, create_time=999.0)})


def test_handle_track_on_unknown_session():
    """TRACK arriving before ACQUIRE creates a closed-turn session stub."""
    registry = SessionRegistry()

    def fake_create_time_fn(pid):
        return 50.0

    response = daemon_commands.handle_track(
        registry,
        {"session": "orphan-key", "tool": "claude", "pids": [2001]},
        create_time_fn=fake_create_time_fn,
        now=1000.0,
    )

    assert response["ok"] is True
    session = registry.sessions()["orphan-key"]
    assert session.turn_open is False
    assert session.command_pids == frozenset({CommandPid(pid=2001, create_time=50.0)})


def test_handle_track_requires_pids_list():
    registry = SessionRegistry()

    def fake_create_time_fn(pid):
        return 100.0

    response = daemon_commands.handle_track(
        registry,
        {"session": "key-1"},  # missing pids
        create_time_fn=fake_create_time_fn,
    )

    assert response["ok"] is False
    assert "pids" in response["error"]
