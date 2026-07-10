from __future__ import annotations

import json

import pytest

import shared
from daemon import Daemon
from lid_monitor import LidMonitor
from session_registry import SessionRegistry
from thermal_monitor import ThermalMonitor


def make_daemon(tmp_path, **overrides):
    helper_calls = []

    async def fake_transport(sock_path, payload, timeout=5.0):
        helper_calls.append(payload)
        return {"ok": True, "sleep_blocked": payload.get("params", {}).get("blocked", False)}

    chime_calls = []
    notify_calls = []

    scan_dir = tmp_path / "sessions"
    kwargs = dict(
        registry=SessionRegistry(),
        lid=LidMonitor(),
        thermal=ThermalMonitor(threshold=85.0),
        state_file=tmp_path / "state.json",
        transport=fake_transport,
        play_chime_fn=lambda: chime_calls.append(True),
        notify_summary_fn=lambda *a, **k: notify_calls.append((a, k)),
        pid_exists_fn=lambda pid: True,
        cpu_percent_fn=lambda pid: 0.0,
        read_lid_state_fn=lambda: "open",
        agent_scan_dirs={"claude": scan_dir},
    )
    kwargs.update(overrides)
    daemon = Daemon(**kwargs)
    return daemon, helper_calls, chime_calls, notify_calls


@pytest.mark.asyncio
async def test_acquire_then_status_round_trip(tmp_path):
    daemon, helper_calls, _, _ = make_daemon(tmp_path)

    acquire_response = await daemon.handle_request(
        {"cmd": "ACQUIRE", "session": "k1", "tool": "claude", "reason": "building"}, peer_pid=111
    )
    assert acquire_response["ok"] is True
    assert acquire_response["status"] == "ACTIVE"

    status_response = await daemon.handle_request({"cmd": "STATUS"}, peer_pid=111)
    assert status_response["status"] == "ACTIVE"
    assert "k1" in status_response["active_sessions"]

    # first acquire flips sleep_blocked False -> True, so the helper is called once
    assert helper_calls == [{"method": "set_sleep_blocked", "params": {"blocked": True}}]


@pytest.mark.asyncio
async def test_reconcile_only_calls_helper_on_transition(tmp_path):
    daemon, helper_calls, _, _ = make_daemon(tmp_path)

    await daemon.handle_request({"cmd": "ACQUIRE", "session": "k1", "tool": "claude"}, peer_pid=1)
    await daemon.handle_request({"cmd": "ACQUIRE", "session": "k2", "tool": "claude"}, peer_pid=2)
    assert len(helper_calls) == 1  # already blocked, second acquire doesn't re-call

    await daemon.handle_request({"cmd": "RELEASE", "session": "k1"}, peer_pid=1)
    assert len(helper_calls) == 1  # still one session held

    await daemon.handle_request({"cmd": "RELEASE", "session": "k2"}, peer_pid=2)
    assert len(helper_calls) == 2  # last release flips back to unblocked
    assert helper_calls[1] == {"method": "set_sleep_blocked", "params": {"blocked": False}}


@pytest.mark.asyncio
async def test_handle_request_persists_state_file(tmp_path):
    daemon, _, _, _ = make_daemon(tmp_path)
    await daemon.handle_request({"cmd": "ACQUIRE", "session": "k1", "tool": "claude"}, peer_pid=1)

    state = json.loads((tmp_path / "state.json").read_text())
    assert state["status"] == "ACTIVE"
    assert "k1" in state["active_sessions"]


@pytest.mark.asyncio
async def test_kill_all_releases_all_sessions_and_unblocks(tmp_path):
    daemon, helper_calls, _, _ = make_daemon(tmp_path)
    await daemon.handle_request({"cmd": "ACQUIRE", "session": "k1", "tool": "claude"}, peer_pid=1)

    response = await daemon.handle_request({"cmd": "KILL_ALL"}, peer_pid=1)

    assert response["released"] == 1
    assert helper_calls[-1] == {"method": "set_sleep_blocked", "params": {"blocked": False}}


@pytest.mark.asyncio
async def test_unknown_command_returns_error(tmp_path):
    daemon, _, _, _ = make_daemon(tmp_path)
    response = await daemon.handle_request({"cmd": "NOPE"}, peer_pid=1)
    assert response["ok"] is False


@pytest.mark.asyncio
async def test_tick_does_not_prune_acquired_sessions_despite_dead_pid_check(tmp_path):
    # Regression test: handle_acquire no longer tracks a PID (see its
    # docstring), so a session must survive tick()'s prune_dead pass even
    # when pid_exists_fn reports everything as dead. Before the fix, this
    # session was destroyed on the very next tick regardless of real agent
    # activity, defeating the whole point of holding sleep prevention.
    daemon, helper_calls, _, _ = make_daemon(tmp_path, pid_exists_fn=lambda pid: False)
    await daemon.handle_request({"cmd": "ACQUIRE", "session": "k1", "tool": "claude"}, peer_pid=1234)
    helper_calls.clear()

    await daemon.tick()

    assert daemon.registry.count() == 1
    assert "k1" in daemon.registry.sessions()
    assert {"method": "set_sleep_blocked", "params": {"blocked": False}} not in helper_calls


@pytest.mark.asyncio
async def test_tick_does_not_prune_acquired_sessions_despite_idle_cpu(tmp_path):
    # Regression test: same as above, but for the idle-timeout path.
    daemon, helper_calls, _, _ = make_daemon(
        tmp_path, pid_exists_fn=lambda pid: True, cpu_percent_fn=lambda pid: 0.0
    )
    daemon.idle_tracker.idle_timeout_seconds = 0  # idle as soon as a second sample confirms it
    await daemon.handle_request({"cmd": "ACQUIRE", "session": "k1", "tool": "claude"}, peer_pid=1234)
    helper_calls.clear()

    await daemon.tick()
    await daemon.tick()

    assert daemon.registry.count() == 1
    assert "k1" in daemon.registry.sessions()


@pytest.mark.asyncio
async def test_tick_expires_holds_and_unblocks(tmp_path):
    daemon, helper_calls, _, _ = make_daemon(tmp_path)
    await daemon.handle_request({"cmd": "HOLD", "for": "1s", "reason": "deploy"}, peer_pid=None)
    helper_calls.clear()

    import time as time_module

    real_time = time_module.time
    daemon._now = lambda: real_time() + 10  # force the hold to look expired

    await daemon.tick()

    assert daemon.registry.count() == 0
    assert {"method": "set_sleep_blocked", "params": {"blocked": False}} in helper_calls


@pytest.mark.asyncio
async def test_tick_lid_close_plays_chime_when_sessions_active(tmp_path):
    lid_states = iter(["open", "closed"])
    daemon, _, chime_calls, notify_calls = make_daemon(
        tmp_path, read_lid_state_fn=lambda: next(lid_states)
    )
    await daemon.handle_request({"cmd": "ACQUIRE", "session": "k1", "tool": "claude"}, peer_pid=1)

    await daemon.tick()  # establishes baseline "open" (unknown -> open is not a transition)
    await daemon.tick()  # real "open" -> "closed" transition while a session is active

    assert chime_calls == [True]
    assert notify_calls == []


@pytest.mark.asyncio
async def test_tick_lid_open_sends_summary_notification(tmp_path):
    lid_states = iter(["closed", "open"])
    daemon, _, chime_calls, notify_calls = make_daemon(
        tmp_path, read_lid_state_fn=lambda: next(lid_states)
    )
    await daemon.tick()  # observes closed first (no prior state -> no transition)
    await daemon.tick()  # observes open -> transition

    assert len(notify_calls) == 1


@pytest.mark.asyncio
async def test_tick_thermal_cutout_releases_all_sessions_while_lid_closed(tmp_path):
    async def hot_transport(sock_path, payload, timeout=5.0):
        if payload["method"] == "get_thermal":
            return {"ok": True, "temperature": 95.0}
        return {"ok": True}

    daemon, helper_calls, _, _ = make_daemon(
        tmp_path, transport=hot_transport, read_lid_state_fn=lambda: "closed"
    )
    await daemon.handle_request({"cmd": "ACQUIRE", "session": "k1", "tool": "claude"}, peer_pid=1)

    await daemon.tick()

    assert daemon.registry.count() == 0
    assert daemon.thermal.cutout_fired is True


def _write_session(session_dir, pid, session_id, status="busy", name="", alive=True):
    data = {"pid": pid, "sessionId": session_id, "status": status, "name": name}
    (session_dir / f"{pid}.json").write_text(json.dumps(data))


class TestSniffAgents:
    """_sniff_agents auto-detects running agent sessions via session files."""

    def test_acquires_busy_session(self, tmp_path):
        daemon, _, _, _ = make_daemon(tmp_path)
        scan_dir = daemon._agent_scan_dirs["claude"]
        scan_dir.mkdir(parents=True)
        _write_session(scan_dir, pid=1001, session_id="ses-busy", status="busy")

        result = daemon._sniff_agents()

        assert result is True
        assert "ses-busy" in daemon.registry.sessions()
        assert daemon.registry.sessions()["ses-busy"].agent == "claude"
        assert daemon.registry.sessions()["ses-busy"].pid == 1001

    def test_skips_idle_session(self, tmp_path):
        daemon, _, _, _ = make_daemon(tmp_path)
        scan_dir = daemon._agent_scan_dirs["claude"]
        scan_dir.mkdir(parents=True)
        _write_session(scan_dir, pid=1002, session_id="ses-idle", status="idle")

        result = daemon._sniff_agents()

        assert result is False
        assert "ses-idle" not in daemon.registry.sessions()

    def test_skips_dead_pid(self, tmp_path):
        daemon, _, _, _ = make_daemon(tmp_path, pid_exists_fn=lambda pid: False)
        scan_dir = daemon._agent_scan_dirs["claude"]
        scan_dir.mkdir(parents=True)
        _write_session(scan_dir, pid=1003, session_id="ses-dead", status="busy")

        result = daemon._sniff_agents()

        assert result is False
        assert "ses-dead" not in daemon.registry.sessions()

    def test_skips_session_without_pid(self, tmp_path):
        daemon, _, _, _ = make_daemon(tmp_path)
        scan_dir = daemon._agent_scan_dirs["claude"]
        scan_dir.mkdir(parents=True)
        data = {"sessionId": "ses-nopid", "status": "busy"}
        (scan_dir / "nopid.json").write_text(json.dumps(data))

        result = daemon._sniff_agents()

        assert result is False

    def test_skips_already_tracked_session(self, tmp_path):
        daemon, _, _, _ = make_daemon(tmp_path)
        daemon.registry.acquire("ses-tracked", agent="claude", pid=1004)
        scan_dir = daemon._agent_scan_dirs["claude"]
        scan_dir.mkdir(parents=True)
        _write_session(scan_dir, pid=1004, session_id="ses-tracked", status="busy")

        result = daemon._sniff_agents()

        assert result is False  # no new sessions acquired

    def test_handles_missing_session_dir(self, tmp_path):
        daemon, _, _, _ = make_daemon(tmp_path)

        result = daemon._sniff_agents()

        assert result is False

    def test_handles_empty_session_dir(self, tmp_path):
        daemon, _, _, _ = make_daemon(tmp_path)
        daemon._agent_scan_dirs["claude"].mkdir(parents=True)

        result = daemon._sniff_agents()

        assert result is False

    def test_handles_invalid_json_gracefully(self, tmp_path):
        daemon, _, _, _ = make_daemon(tmp_path)
        scan_dir = daemon._agent_scan_dirs["claude"]
        scan_dir.mkdir(parents=True)
        (scan_dir / "garbage.json").write_text("not valid json{{{")

        result = daemon._sniff_agents()

        assert result is False

    def test_skips_non_json_files(self, tmp_path):
        daemon, _, _, _ = make_daemon(tmp_path)
        scan_dir = daemon._agent_scan_dirs["claude"]
        scan_dir.mkdir(parents=True)
        (scan_dir / "readme.txt").write_text("hello")

        result = daemon._sniff_agents()

        assert result is False

    def test_acquires_named_session(self, tmp_path):
        daemon, _, _, _ = make_daemon(tmp_path)
        scan_dir = daemon._agent_scan_dirs["claude"]
        scan_dir.mkdir(parents=True)
        _write_session(scan_dir, pid=1005, session_id="ses-named", status="busy", name="omega-42")

        daemon._sniff_agents()

        assert daemon.registry.sessions()["ses-named"].reason == "sniffed: omega-42"

    @pytest.mark.asyncio
    async def test_tick_integrates_sniffing(self, tmp_path):
        daemon, _, _, _ = make_daemon(tmp_path)
        scan_dir = daemon._agent_scan_dirs["claude"]
        scan_dir.mkdir(parents=True)
        _write_session(scan_dir, pid=1006, session_id="ses-tick", status="busy")

        await daemon.tick()

        assert "ses-tick" in daemon.registry.sessions()
        assert daemon.registry.is_active()

    def test_run_forever_sniffs_on_startup(self, tmp_path):
        daemon, helper_calls, _, _ = make_daemon(tmp_path)
        scan_dir = daemon._agent_scan_dirs["claude"]
        scan_dir.mkdir(parents=True)
        _write_session(scan_dir, pid=1007, session_id="ses-startup", status="busy")

        # Manually simulate run_forever's startup sniff
        daemon._sniff_agents()

        assert "ses-startup" in daemon.registry.sessions()

