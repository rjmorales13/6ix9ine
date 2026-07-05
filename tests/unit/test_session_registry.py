from __future__ import annotations

import pytest

from session_registry import SessionRegistry


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
