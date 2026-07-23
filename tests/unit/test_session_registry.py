from __future__ import annotations

import pytest

from session_registry import CommandPid, SessionRegistry


def test_new_registry_is_idle_and_empty():
    registry = SessionRegistry()
    assert registry.count() == 0
    assert registry.is_active() is False


def test_acquire_adds_a_session_and_makes_registry_active():
    registry = SessionRegistry()
    session = registry.acquire("key-1", agent="claude", reason="building", pid=111, now=1000.0)

    assert session.key == "key-1"
    assert session.agent == "claude"
    assert session.pid == 111
    assert session.timestamp == 1000.0
    assert registry.count() == 1
    assert registry.is_active() is True


def test_acquire_rejects_unknown_agent():
    registry = SessionRegistry()
    with pytest.raises(ValueError):
        registry.acquire("key-1", agent="not-a-real-agent")


def test_overlapping_sessions_stack_by_distinct_key():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", now=1000.0)
    registry.acquire("key-2", agent="opencode", now=1000.0)
    assert registry.count() == 2


def test_release_removes_session_and_returns_true():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", now=1000.0)
    assert registry.release("key-1") is True
    assert registry.count() == 0


def test_release_returns_false_for_unknown_key():
    registry = SessionRegistry()
    assert registry.release("does-not-exist") is False


def test_sleep_unblocks_only_after_last_session_releases():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", now=1000.0)
    registry.acquire("key-2", agent="opencode", now=1000.0)
    registry.release("key-1")
    assert registry.is_active() is True
    registry.release("key-2")
    assert registry.is_active() is False


def test_add_hold_and_expire_holds():
    registry = SessionRegistry()
    registry.add_hold("hold-1", reason="deploy", duration_seconds=1800, now=1000.0)
    assert registry.count() == 1

    assert registry.expire_holds(now=1000.0) == []
    assert registry.count() == 1

    expired = registry.expire_holds(now=1000.0 + 1800.0)
    assert [h.id for h in expired] == ["hold-1"]
    assert registry.count() == 0


def test_release_all_clears_sessions_and_holds_and_returns_count():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", now=1000.0)
    registry.add_hold("hold-1", reason="deploy", duration_seconds=60, now=1000.0)
    assert registry.release_all() == 2
    assert registry.count() == 0


def test_prune_dead_removes_sessions_whose_pid_is_no_longer_alive():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", pid=111, now=1000.0)
    registry.acquire("key-2", agent="claude", pid=222, now=1000.0)

    removed = registry.prune_dead(is_alive=lambda pid: pid == 222)

    assert removed == ["key-1"]
    assert registry.count() == 1


def test_prune_dead_ignores_sessions_without_a_pid():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="manual", pid=None, now=1000.0)
    removed = registry.prune_dead(is_alive=lambda pid: False)
    assert removed == []
    assert registry.count() == 1


def test_prune_idle_removes_sessions_flagged_idle():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", pid=111, now=1000.0)
    registry.acquire("key-2", agent="claude", pid=222, now=1000.0)

    removed = registry.prune_idle(is_idle=lambda pid: pid == 111)

    assert removed == ["key-1"]
    assert registry.count() == 1


def test_to_state_dict_reports_active_status_and_held_for():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", reason="building", pid=111, now=1000.0)

    state = registry.to_state_dict(now=1932.0)

    assert state["status"] == "ACTIVE"
    session_state = state["active_sessions"]["key-1"]
    assert session_state["agent"] == "claude"
    assert session_state["reason"] == "building"
    assert session_state["pid"] == 111
    assert session_state["held_for"] == "15m 32s"


def test_to_state_dict_reports_idle_status_when_empty():
    registry = SessionRegistry()
    state = registry.to_state_dict(now=1000.0)
    assert state["status"] == "IDLE"
    assert state["active_sessions"] == {}
    assert state["holds"] == []


def test_to_state_dict_reports_hold_expires_in():
    registry = SessionRegistry()
    registry.add_hold("hold-1", reason="deploy", duration_seconds=1800, now=1000.0)

    state = registry.to_state_dict(now=1000.0 + 60.0)

    hold = state["holds"][0]
    assert hold["id"] == "hold-1"
    assert hold["reason"] == "deploy"
    assert hold["expires_in"] == "29m 0s"


# -- Epilogue reporter: command PID tracking -----------------------------


def test_acquire_merge_preserves_pids():
    """Re-acquiring an existing key must not clobber tracked command PIDs."""
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", now=1000.0)
    registry.track_pids("key-1", [CommandPid(pid=555, create_time=10.0)], now=1000.0)

    session = registry.acquire("key-1", agent="claude", reason="new turn", now=2000.0)

    assert session.command_pids == frozenset({CommandPid(pid=555, create_time=10.0)})
    assert session.reason == "new turn"
    assert session.timestamp == 2000.0
    assert session.turn_open is True


def test_acquire_new_session_has_no_pids_and_open_turn():
    registry = SessionRegistry()
    session = registry.acquire("key-1", agent="claude", now=1000.0)
    assert session.command_pids == frozenset()
    assert session.turn_open is True


def test_track_pids_on_unknown_session():
    """Race safety: TRACK arriving before/without ACQUIRE creates a closed-turn stub."""
    registry = SessionRegistry()
    session = registry.track_pids(
        "orphan-key", [CommandPid(pid=777, create_time=5.0)], agent="claude", now=1000.0
    )

    assert session.turn_open is False
    assert session.command_pids == frozenset({CommandPid(pid=777, create_time=5.0)})
    assert registry.sessions()["orphan-key"].turn_open is False
    assert registry.is_active() is True


def test_track_pids_adds_to_existing_session():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", now=1000.0)
    registry.track_pids("key-1", [CommandPid(pid=1, create_time=1.0)], now=1000.0)
    session = registry.track_pids("key-1", [CommandPid(pid=2, create_time=2.0)], now=1000.0)

    assert session.command_pids == frozenset(
        {CommandPid(pid=1, create_time=1.0), CommandPid(pid=2, create_time=2.0)}
    )


def test_release_with_live_pids():
    """release() must not drop a session while it still has tracked command PIDs."""
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", now=1000.0)
    registry.track_pids("key-1", [CommandPid(pid=1, create_time=1.0)], now=1000.0)

    assert registry.release("key-1") is True

    session = registry.sessions()["key-1"]
    assert session.turn_open is False
    assert session.command_pids == frozenset({CommandPid(pid=1, create_time=1.0)})
    assert registry.is_active() is True


def test_release_without_pids_removes_session():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", now=1000.0)
    assert registry.release("key-1") is True
    assert registry.count() == 0


def test_prune_command_pids_with_create_time_guard():
    """PID-reuse guard: a matching pid with a mismatched create_time is dead."""
    registry = SessionRegistry()
    registry.track_pids(
        "key-1",
        [CommandPid(pid=100, create_time=50.0), CommandPid(pid=200, create_time=60.0)],
        now=1000.0,
    )

    def is_alive(cp: CommandPid) -> bool:
        # pid=100 is running, but a different process now owns it (OS reused
        # the pid) -- create_time no longer matches, so it must count as dead.
        live_create_times = {200: 60.0}
        return live_create_times.get(cp.pid) == cp.create_time

    removed = registry.prune_command_pids(is_alive)

    session = registry.sessions()["key-1"]
    assert session.command_pids == frozenset({CommandPid(pid=200, create_time=60.0)})
    assert removed == []


def test_prune_command_pids_removes_closed_sessions_with_no_live_pids():
    registry = SessionRegistry()
    registry.track_pids("key-1", [CommandPid(pid=100, create_time=50.0)], now=1000.0)
    registry.release("key-1")

    removed = registry.prune_command_pids(is_alive=lambda cp: False)

    assert removed == ["key-1"]
    assert registry.count() == 0


def test_prune_command_pids_keeps_open_turn_even_with_no_pids():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", now=1000.0)

    removed = registry.prune_command_pids(is_alive=lambda cp: False)

    assert removed == []
    assert registry.count() == 1


def test_prune_command_pids_keeps_session_with_agent_pid_even_if_closed():
    """A session with a live agent-level pid must survive even with turn_open False."""
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", pid=999, now=1000.0)
    registry.track_pids("key-1", [CommandPid(pid=100, create_time=50.0)], now=1000.0)
    registry.release("key-1")

    removed = registry.prune_command_pids(is_alive=lambda cp: False)

    assert removed == []
    assert registry.count() == 1


def test_to_state_dict_includes_command_pids():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", now=1000.0)
    registry.track_pids("key-1", [CommandPid(pid=42, create_time=7.5)], now=1000.0)

    state = registry.to_state_dict(now=1000.0)

    session_state = state["active_sessions"]["key-1"]
    assert session_state["command_pids"] == [{"pid": 42, "create_time": 7.5}]


def test_to_state_dict_command_pids_empty_by_default():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", now=1000.0)

    state = registry.to_state_dict(now=1000.0)

    assert state["active_sessions"]["key-1"]["command_pids"] == []


# -- prune_dead: pid-reuse-guarded acquire sessions (OpenCode --pid) -----


def test_prune_dead_no_pid_is_not_eligible_for_pruning():
    """A session with no pid at all (today's handle_acquire default) is
    never touched by prune_dead, regardless of what is_alive says."""
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", pid=None, now=1000.0)

    removed = registry.prune_dead(is_alive=lambda pid: False, create_time_fn=lambda pid: None)

    assert removed == []
    assert registry.count() == 1


def test_prune_dead_pid_without_create_time_uses_legacy_liveness_only():
    """pid set but no create_time (Claude's process-sniffed sessions): alive
    iff is_alive(pid), unaffected by create_time_fn -- unchanged behavior."""
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", pid=111, now=1000.0)

    removed = registry.prune_dead(is_alive=lambda pid: True, create_time_fn=lambda pid: None)
    assert removed == []
    assert registry.count() == 1

    removed = registry.prune_dead(is_alive=lambda pid: False, create_time_fn=lambda pid: None)
    assert removed == ["key-1"]
    assert registry.count() == 0


def test_prune_dead_guarded_session_survives_when_pid_and_create_time_match():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="opencode", pid=222, create_time=50.0, now=1000.0)

    removed = registry.prune_dead(is_alive=lambda pid: True, create_time_fn=lambda pid: 50.0)

    assert removed == []
    assert registry.count() == 1


def test_prune_dead_guarded_session_removed_when_pid_reused_by_new_process():
    """PID-reuse hazard: pid_exists is True (the OS handed the pid to an
    unrelated process), but create_time no longer matches -- must be pruned."""
    registry = SessionRegistry()
    registry.acquire("key-1", agent="opencode", pid=222, create_time=50.0, now=1000.0)

    removed = registry.prune_dead(is_alive=lambda pid: True, create_time_fn=lambda pid: 999.0)

    assert removed == ["key-1"]
    assert registry.count() == 0


def test_prune_dead_guarded_session_within_tolerance_survives():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="opencode", pid=222, create_time=50.0, now=1000.0)

    removed = registry.prune_dead(is_alive=lambda pid: True, create_time_fn=lambda pid: 50.9)

    assert removed == []
    assert registry.count() == 1


def test_prune_dead_guarded_session_removed_when_pid_no_longer_exists():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="opencode", pid=222, create_time=50.0, now=1000.0)

    removed = registry.prune_dead(is_alive=lambda pid: False, create_time_fn=lambda pid: 50.0)

    assert removed == ["key-1"]
    assert registry.count() == 0


def test_prune_dead_guarded_session_removed_when_create_time_unresolvable():
    """is_alive True but create_time_fn can't resolve current create_time
    (process just exited) -- treat as dead, mirroring is_command_pid_alive."""
    registry = SessionRegistry()
    registry.acquire("key-1", agent="opencode", pid=222, create_time=50.0, now=1000.0)

    removed = registry.prune_dead(is_alive=lambda pid: True, create_time_fn=lambda pid: None)

    assert removed == ["key-1"]
    assert registry.count() == 0


def test_prune_dead_guarded_session_without_create_time_fn_treated_as_dead():
    """If no create_time_fn is supplied at all for a guarded session, we
    can't verify identity, so fail toward pruning rather than trusting it."""
    registry = SessionRegistry()
    registry.acquire("key-1", agent="opencode", pid=222, create_time=50.0, now=1000.0)

    removed = registry.prune_dead(is_alive=lambda pid: True)

    assert removed == ["key-1"]
    assert registry.count() == 0


# -- prune_idle: guarded acquire sessions are exempt from CPU-idle pruning --


def test_prune_idle_exempts_sessions_with_create_time():
    """A guarded acquire session (pid + create_time) must never be pruned for
    CPU idleness -- it has its own release signal (session.idle)."""
    registry = SessionRegistry()
    registry.acquire("key-1", agent="opencode", pid=222, create_time=50.0, now=1000.0)

    calls = []

    def is_idle(pid):
        calls.append(pid)
        return True  # even if "idle", must not be pruned

    removed = registry.prune_idle(is_idle)

    assert removed == []
    assert registry.count() == 1
    # is_idle must never even be called for a guarded session -- the `and`
    # short-circuits before touching the CPU-percent sampler.
    assert calls == []


def test_prune_idle_still_applies_to_pid_only_sessions():
    """Claude's process-sniffed sessions (pid, no create_time) are unaffected
    -- they remain the only consumer of CPU-idle pruning."""
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", pid=111, now=1000.0)

    removed = registry.prune_idle(is_idle=lambda pid: True)

    assert removed == ["key-1"]
    assert registry.count() == 0


# -- prune_max_age: hard defense-in-depth backstop -----------------------


def test_prune_max_age_removes_sessions_older_than_threshold():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="opencode", pid=222, create_time=50.0, now=1000.0)

    removed = registry.prune_max_age(max_age_seconds=3600.0, now=1000.0 + 3601.0)

    assert removed == ["key-1"]
    assert registry.count() == 0


def test_prune_max_age_keeps_sessions_within_threshold():
    registry = SessionRegistry()
    registry.acquire("key-1", agent="opencode", pid=222, create_time=50.0, now=1000.0)

    removed = registry.prune_max_age(max_age_seconds=3600.0, now=1000.0 + 3599.0)

    assert removed == []
    assert registry.count() == 1


def test_prune_max_age_ignores_pid_state_entirely():
    """The hard backstop force-releases regardless of pid/create_time -- it's
    a last resort, not another liveness check."""
    registry = SessionRegistry()
    registry.acquire("key-1", agent="claude", pid=None, now=1000.0)
    registry.acquire("key-2", agent="opencode", pid=222, create_time=50.0, now=1000.0)

    removed = registry.prune_max_age(max_age_seconds=100.0, now=1000.0 + 200.0)

    assert set(removed) == {"key-1", "key-2"}
    assert registry.count() == 0


def test_reacquire_refreshes_timestamp_so_active_sessions_never_age_out():
    """acquire() on an existing key replaces `timestamp` with the fresh
    `now` -- an actively-used session (repeated chat.message acquires) never
    approaches the max-age backstop."""
    registry = SessionRegistry()
    registry.acquire("key-1", agent="opencode", pid=222, create_time=50.0, now=1000.0)
    registry.acquire("key-1", agent="opencode", pid=222, create_time=50.0, now=1000.0 + 3600.0)

    assert registry.sessions()["key-1"].timestamp == 1000.0 + 3600.0

    removed = registry.prune_max_age(max_age_seconds=100.0, now=1000.0 + 3650.0)

    assert removed == []
    assert registry.count() == 1
