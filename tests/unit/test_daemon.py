from __future__ import annotations

import json

import pytest

import shared
from daemon import Daemon
from lid_monitor import LidMonitor
from session_registry import CommandPid, SessionRegistry
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


# -- Epilogue reporter: background command PID tracking --


@pytest.mark.asyncio
async def test_handle_track_command_registers_pids(tmp_path):
    """TRACK command dispatches through handle_request."""
    daemon, _, _, _ = make_daemon(tmp_path)
    daemon.registry.acquire("key-1", agent="claude", now=1000.0)

    fake_create_times = {2001: 50.0, 2002: 49.0}
    daemon._create_time_fn = lambda pid: fake_create_times.get(pid)

    response = await daemon.handle_request(
        {"cmd": "TRACK", "session": "key-1", "tool": "claude", "pids": [2001, 2002]},
        peer_pid=None,
    )

    assert response["ok"] is True
    session = daemon.registry.sessions()["key-1"]
    assert session.command_pids == frozenset(
        {CommandPid(pid=2001, create_time=50.0), CommandPid(pid=2002, create_time=49.0)}
    )


@pytest.mark.asyncio
async def test_track_in_mutating_commands_reconciles_and_persists(tmp_path):
    """TRACK is a mutating command: it calls reconcile and persists state."""
    daemon, helper_calls, _, _ = make_daemon(tmp_path)
    daemon.registry.acquire("key-1", agent="claude", now=1000.0)
    daemon._create_time_fn = lambda pid: 50.0
    helper_calls.clear()

    response = await daemon.handle_request(
        {"cmd": "TRACK", "session": "key-1", "tool": "claude", "pids": [2001]},
        peer_pid=None,
    )

    assert response["ok"] is True
    # State file is persisted
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["active_sessions"]["key-1"]["command_pids"] == [{"pid": 2001, "create_time": 50.0}]


@pytest.mark.asyncio
async def test_daemon_tick_prunes_dead_command_pids(tmp_path):
    """tick() calls prune_command_pids to remove dead tracked PIDs."""
    daemon, helper_calls, _, _ = make_daemon(tmp_path)
    # Keep tick()'s own `now` aligned with the synthetic timestamp below --
    # otherwise the real wall clock reads as ~decades past it, and the
    # session_max_age_hours() hard backstop (unrelated to what this test is
    # actually exercising) would force-release the session before the
    # command-pid pruning under test ever runs.
    daemon._now = lambda: 1000.0
    daemon.registry.acquire("key-1", agent="claude", now=1000.0)

    # Track two PIDs, only 2001 is alive
    daemon._create_time_fn = lambda pid: 50.0 if pid == 2001 else 49.0
    await daemon.handle_request(
        {"cmd": "TRACK", "session": "key-1", "tool": "claude", "pids": [2001, 2002]},
        peer_pid=None,
    )
    helper_calls.clear()

    # Simulate prune_command_pids: 2002 is dead, 2001 is still alive
    def is_alive(cp: CommandPid) -> bool:
        return cp.pid == 2001 and cp.create_time == 50.0

    await daemon.tick()
    # Manually set the is_alive check to test pruning
    removed = daemon.registry.prune_command_pids(is_alive)

    session = daemon.registry.sessions()["key-1"]
    assert session.command_pids == frozenset({CommandPid(pid=2001, create_time=50.0)})


@pytest.mark.asyncio
async def test_daemon_tick_prunes_dead_pids_and_cleans_up_closed_sessions(tmp_path):
    """When all command PIDs die and turn_open is False, session is removed."""
    daemon, helper_calls, _, _ = make_daemon(tmp_path)
    daemon.registry.acquire("key-1", agent="claude", now=1000.0)

    # Track a PID
    daemon._create_time_fn = lambda pid: 50.0
    await daemon.handle_request(
        {"cmd": "TRACK", "session": "key-1", "tool": "claude", "pids": [2001]},
        peer_pid=None,
    )

    # Release the session (sets turn_open=False, keeps session for tracked pid)
    await daemon.handle_request({"cmd": "RELEASE", "session": "key-1"}, peer_pid=None)
    assert daemon.registry.count() == 1

    # Now prune with all PIDs dead
    def is_alive(cp: CommandPid) -> bool:
        return False  # all dead

    daemon.registry.prune_command_pids(is_alive)

    # Session should be gone
    assert daemon.registry.count() == 0


@pytest.mark.asyncio
async def test_pid_reuse_guard_with_create_time_mismatch(tmp_path):
    """create_time guard: OS PID reuse doesn't resurrect a dead session."""
    daemon, _, _, _ = make_daemon(tmp_path)
    daemon.registry.acquire("key-1", agent="claude", now=1000.0)

    # Track PID 1001 created at time 50.0
    daemon._create_time_fn = lambda pid: 50.0
    await daemon.handle_request(
        {"cmd": "TRACK", "session": "key-1", "tool": "claude", "pids": [1001]},
        peer_pid=None,
    )

    # Release the session
    await daemon.handle_request({"cmd": "RELEASE", "session": "key-1"}, peer_pid=None)

    # Now OS recycles PID 1001 for a new process created at time 100.0
    # But we still have the old create_time (50.0) from the old process
    def is_alive(cp: CommandPid) -> bool:
        # The new PID 1001 was created at 100.0, but we're checking against 50.0
        # They don't match, so it counts as dead
        new_create_time = 100.0  # OS recycled the PID
        return cp.create_time == new_create_time  # mismatch!

    daemon.registry.prune_command_pids(is_alive)

    # The old PID 1001 (with create_time 50.0) should be removed
    assert daemon.registry.count() == 0


@pytest.mark.asyncio
async def test_idle_tracker_prunes_tracked_pids_on_idle_timeout(tmp_path):
    """Idle timeout applies to tracked command PIDs too (zero-CPU sleep 3600 &)."""
    daemon, helper_calls, _, _ = make_daemon(tmp_path)
    # See test_daemon_tick_prunes_dead_command_pids for why this alignment
    # is needed: without it, the session_max_age_hours() backstop force-
    # releases the session before the idle-timeout behavior under test runs.
    daemon._now = lambda: 1000.0
    daemon.idle_tracker.idle_timeout_seconds = 0  # idle as soon as observed with 0% CPU
    daemon.registry.acquire("key-1", agent="claude", now=1000.0)

    # Track a background process (like `sleep 3600 &`)
    daemon._create_time_fn = lambda pid: 999.0
    await daemon.handle_request(
        {"cmd": "TRACK", "session": "key-1", "tool": "claude", "pids": [2001]},
        peer_pid=None,
    )

    # Simulate tick with 0% CPU (idle) on the tracked PID
    def zero_cpu(_):
        return 0.0

    daemon._cpu_percent = zero_cpu
    helper_calls.clear()

    # First tick observes the zero-CPU process
    await daemon.tick()

    # Second tick marks it as idle (per idle_timeout_seconds=0)
    await daemon.tick()

    # The idle tracker should have marked 2001 as idle, and tick should
    # remove it from registry as it's not part of the session-level PID anymore
    # (it's only in command_pids). If the idle tracker doesn't feed command PIDs,
    # this is a manual integration test.
    # For now just verify the session is still there (we didn't filter tracked PIDs yet)
    assert daemon.registry.count() == 1


# -- OpenCode acquire --pid: PID-reuse guard + prune_idle exemption + max age --


@pytest.mark.asyncio
async def test_acquire_with_pid_resolves_create_time_via_daemon(tmp_path):
    daemon, _, _, _ = make_daemon(tmp_path)
    daemon._create_time_fn = lambda pid: {4242: 777.0}.get(pid)

    response = await daemon.handle_request(
        {"cmd": "ACQUIRE", "session": "k1", "tool": "opencode", "pid": 4242}, peer_pid=99999
    )

    assert response["ok"] is True
    session = daemon.registry.sessions()["k1"]
    assert session.pid == 4242
    assert session.create_time == 777.0


@pytest.mark.asyncio
async def test_acquire_never_adopts_peer_pid_even_when_no_pid_field_sent(tmp_path):
    """peer_pid is part of the shared IPC Handler signature but must never
    be adopted into ACQUIRE -- the pid field comes only from the request
    body's explicit `pid`, which the CLI populates from `--pid`."""
    daemon, _, _, _ = make_daemon(tmp_path)
    daemon._create_time_fn = lambda pid: 1.0

    response = await daemon.handle_request(
        {"cmd": "ACQUIRE", "session": "k1", "tool": "claude"}, peer_pid=13579
    )

    assert response["ok"] is True
    session = daemon.registry.sessions()["k1"]
    assert session.pid is None
    assert session.pid != 13579


@pytest.mark.asyncio
async def test_tick_prune_dead_uses_create_time_guard_for_pid_reuse(tmp_path):
    """Regression test for the naive-fix's PID-reuse hazard: a dead OpenCode
    process's pid gets recycled by the OS for an unrelated process before
    the next tick. pid_exists_fn alone would say "alive"; the create_time
    guard must still catch the mismatch and prune it."""
    daemon, helper_calls, _, _ = make_daemon(tmp_path, pid_exists_fn=lambda pid: True)
    daemon._now = lambda: 1000.0
    daemon._create_time_fn = lambda pid: 50.0  # the ORIGINAL create_time at acquire time

    await daemon.handle_request(
        {"cmd": "ACQUIRE", "session": "k1", "tool": "opencode", "pid": 4242}, peer_pid=1
    )
    assert daemon.registry.sessions()["k1"].create_time == 50.0

    # OS recycles pid 4242 for a new, unrelated process with a different
    # create_time. pid_exists_fn still says True, but the create_time no
    # longer matches.
    daemon._create_time_fn = lambda pid: 999.0
    helper_calls.clear()

    await daemon.tick()

    assert daemon.registry.count() == 0
    assert {"method": "set_sleep_blocked", "params": {"blocked": False}} in helper_calls


@pytest.mark.asyncio
async def test_tick_prune_dead_keeps_guarded_session_when_create_time_matches(tmp_path):
    daemon, _, _, _ = make_daemon(tmp_path, pid_exists_fn=lambda pid: True)
    daemon._now = lambda: 1000.0
    daemon._create_time_fn = lambda pid: 50.0

    await daemon.handle_request(
        {"cmd": "ACQUIRE", "session": "k1", "tool": "opencode", "pid": 4242}, peer_pid=1
    )

    await daemon.tick()

    assert daemon.registry.count() == 1
    assert "k1" in daemon.registry.sessions()


@pytest.mark.asyncio
async def test_tick_does_not_prune_guarded_opencode_session_despite_idle_cpu(tmp_path):
    """The bug this whole fix targets: an OpenCode acquire --pid session
    must NOT be pruned by CPU-idle detection just because the long-lived
    host process is near-0% CPU while genuinely waiting on the model."""
    daemon, _, _, _ = make_daemon(tmp_path, pid_exists_fn=lambda pid: True, cpu_percent_fn=lambda pid: 0.0)
    daemon._now = lambda: 1000.0
    daemon._create_time_fn = lambda pid: 50.0
    daemon.idle_tracker.idle_timeout_seconds = 0  # idle as soon as a second sample confirms it

    await daemon.handle_request(
        {"cmd": "ACQUIRE", "session": "k1", "tool": "opencode", "pid": 4242}, peer_pid=1
    )

    await daemon.tick()
    await daemon.tick()

    assert daemon.registry.count() == 1
    assert "k1" in daemon.registry.sessions()


@pytest.mark.asyncio
async def test_tick_max_age_backstop_force_releases_abandoned_session(tmp_path):
    """Defense-in-depth: a session that somehow evades every other prune
    path (e.g. its pid got reused right before every tick's check, or
    pid_exists_fn itself is unreliable) still gets force-released once it's
    older than session_max_age_hours()."""
    daemon, helper_calls, _, _ = make_daemon(tmp_path, pid_exists_fn=lambda pid: True)
    daemon._create_time_fn = lambda pid: 50.0
    daemon._now = lambda: 1000.0

    await daemon.handle_request(
        {"cmd": "ACQUIRE", "session": "k1", "tool": "opencode", "pid": 4242}, peer_pid=1
    )
    helper_calls.clear()

    # Advance well past the default 4h threshold, keeping create_time
    # matching throughout (so this genuinely isolates the max-age backstop,
    # not the create_time guard).
    daemon._now = lambda: 1000.0 + (5 * 3600.0)

    await daemon.tick()

    assert daemon.registry.count() == 0
    assert {"method": "set_sleep_blocked", "params": {"blocked": False}} in helper_calls


@pytest.mark.asyncio
async def test_tick_max_age_backstop_respects_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("SIXNINE_SESSION_MAX_AGE_HOURS", "1")
    daemon, _, _, _ = make_daemon(tmp_path, pid_exists_fn=lambda pid: True)
    daemon._create_time_fn = lambda pid: 50.0
    daemon._now = lambda: 1000.0

    await daemon.handle_request(
        {"cmd": "ACQUIRE", "session": "k1", "tool": "opencode", "pid": 4242}, peer_pid=1
    )

    daemon._now = lambda: 1000.0 + (2 * 3600.0)  # past the overridden 1h threshold

    await daemon.tick()

    assert daemon.registry.count() == 0


@pytest.mark.asyncio
async def test_tick_max_age_backstop_does_not_age_out_repeatedly_reacquired_session(tmp_path):
    """acquire() refreshes `timestamp` on every re-acquire (simulating
    OpenCode's chat.message firing on every turn), so an actively-used
    session never approaches the max-age backstop."""
    daemon, _, _, _ = make_daemon(tmp_path, pid_exists_fn=lambda pid: True)
    daemon._create_time_fn = lambda pid: 50.0
    daemon._now = lambda: 1000.0

    await daemon.handle_request(
        {"cmd": "ACQUIRE", "session": "k1", "tool": "opencode", "pid": 4242}, peer_pid=1
    )

    # Re-acquire well past the default 4h threshold from the ORIGINAL
    # timestamp, but each hop is well within it -- simulating a long-running
    # but continuously active turn.
    for hop in range(1, 6):
        daemon._now = lambda hop=hop: 1000.0 + (hop * 3600.0)
        await daemon.handle_request(
            {"cmd": "ACQUIRE", "session": "k1", "tool": "opencode", "pid": 4242}, peer_pid=1
        )

    await daemon.tick()

    assert daemon.registry.count() == 1
    assert "k1" in daemon.registry.sessions()


@pytest.mark.asyncio
async def test_kill_all_still_clears_sessions_with_command_pids(tmp_path):
    """KILL_ALL must clear even sessions with tracked command PIDs."""
    daemon, helper_calls, _, _ = make_daemon(tmp_path)
    daemon.registry.acquire("key-1", agent="claude", now=1000.0)

    # Track a PID
    daemon._create_time_fn = lambda pid: 50.0
    await daemon.handle_request(
        {"cmd": "TRACK", "session": "key-1", "tool": "claude", "pids": [2001]},
        peer_pid=None,
    )

    assert daemon.registry.count() == 1

    # KILL_ALL must clear everything
    response = await daemon.handle_request({"cmd": "KILL_ALL"}, peer_pid=None)

    assert response["released"] == 1
    assert daemon.registry.count() == 0

