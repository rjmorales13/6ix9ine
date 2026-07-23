from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import cli
import shared


def test_build_parser_parses_acquire():
    args = cli.build_parser().parse_args(["acquire", "abc-123", "--tool", "claude", "--reason", "building"])
    assert args.command == "acquire"
    assert args.session_key == "abc-123"
    assert args.tool == "claude"
    assert args.reason == "building"


def test_build_parser_acquire_reason_optional():
    args = cli.build_parser().parse_args(["acquire", "abc-123", "--tool", "opencode"])
    assert args.reason is None


def test_build_parser_acquire_pid_optional_and_defaults_to_none():
    args = cli.build_parser().parse_args(["acquire", "abc-123", "--tool", "opencode"])
    assert args.pid is None


def test_build_parser_acquire_parses_pid():
    args = cli.build_parser().parse_args(
        ["acquire", "abc-123", "--tool", "opencode", "--pid", "4242"]
    )
    assert args.pid == 4242
    assert isinstance(args.pid, int)


def test_build_parser_parses_release():
    args = cli.build_parser().parse_args(["release", "abc-123"])
    assert args.command == "release"
    assert args.session_key == "abc-123"
    assert args.all is False


def test_build_parser_parses_release_all():
    args = cli.build_parser().parse_args(["release", "--all"])
    assert args.all is True
    assert args.session_key is None


def test_build_parser_parses_hold():
    args = cli.build_parser().parse_args(["hold", "--for", "30m", "--reason", "deploy"])
    assert args.command == "hold"
    assert args.duration == "30m"
    assert args.reason == "deploy"


def test_build_parser_parses_status():
    args = cli.build_parser().parse_args(["status"])
    assert args.command == "status"


def test_build_parser_parses_install_hooks_agent():
    args = cli.build_parser().parse_args(["install-hooks", "--agent", "claude"])
    assert args.agent == "claude"
    assert args.all is False


def test_build_parser_parses_install_hooks_all():
    args = cli.build_parser().parse_args(["install-hooks", "--all"])
    assert args.all is True


def test_build_parser_parses_version_flag():
    args = cli.build_parser().parse_args(["--version"])
    assert args.version is True


# --- acquire/release/hold/status against the daemon socket ---


def test_cmd_acquire_sends_expected_payload_and_returns_ok():
    captured = {}

    def fake_send_request(sock_path, payload, timeout=5.0):
        captured["payload"] = payload
        return {"ok": True, "status": "ACTIVE", "count": 1}

    args = SimpleNamespace(session_key="abc-123", tool="claude", reason="building")
    response, exit_code = cli.cmd_acquire(args, send_request=fake_send_request)

    assert captured["payload"] == {"cmd": "ACQUIRE", "session": "abc-123", "tool": "claude", "reason": "building"}
    assert exit_code == shared.EXIT_OK


def test_cmd_acquire_returns_daemon_not_running_on_connection_error():
    def fake_send_request(sock_path, payload, timeout=5.0):
        raise ConnectionError("no socket")

    args = SimpleNamespace(session_key="abc-123", tool="claude", reason=None)
    response, exit_code = cli.cmd_acquire(args, send_request=fake_send_request)

    assert response["ok"] is False
    assert exit_code == shared.EXIT_DAEMON_NOT_RUNNING


def test_cmd_acquire_includes_pid_in_payload_when_provided():
    captured = {}

    def fake_send_request(sock_path, payload, timeout=5.0):
        captured["payload"] = payload
        return {"ok": True, "status": "ACTIVE", "count": 1}

    args = SimpleNamespace(session_key="abc-123", tool="opencode", reason="opencode turn", pid=4242)
    cli.cmd_acquire(args, send_request=fake_send_request)

    assert captured["payload"] == {
        "cmd": "ACQUIRE",
        "session": "abc-123",
        "tool": "opencode",
        "reason": "opencode turn",
        "pid": 4242,
    }


def test_cmd_acquire_omits_pid_from_payload_when_not_provided():
    """Callers built via argparse (pid default None) and hook-acquire's
    manually-built Namespace (no pid attribute at all) must both omit the
    key entirely, not send a null pid."""
    captured = {}

    def fake_send_request(sock_path, payload, timeout=5.0):
        captured["payload"] = payload
        return {"ok": True, "status": "ACTIVE", "count": 1}

    args = SimpleNamespace(session_key="abc-123", tool="claude", reason=None, pid=None)
    cli.cmd_acquire(args, send_request=fake_send_request)

    assert "pid" not in captured["payload"]


def test_cmd_release_sends_release_command():
    captured = {}

    def fake_send_request(sock_path, payload, timeout=5.0):
        captured["payload"] = payload
        return {"ok": True, "status": "IDLE", "count": 0}

    args = SimpleNamespace(session_key="abc-123", all=False)
    _, exit_code = cli.cmd_release(args, send_request=fake_send_request)

    assert captured["payload"] == {"cmd": "RELEASE", "session": "abc-123"}
    assert exit_code == shared.EXIT_OK


def test_cmd_release_all_sends_kill_all():
    captured = {}

    def fake_send_request(sock_path, payload, timeout=5.0):
        captured["payload"] = payload
        return {"ok": True, "status": "IDLE", "released": 2}

    args = SimpleNamespace(session_key=None, all=True)
    cli.cmd_release(args, send_request=fake_send_request)

    assert captured["payload"] == {"cmd": "KILL_ALL"}


def test_cmd_release_propagates_session_not_found_exit_code():
    def fake_send_request(sock_path, payload, timeout=5.0):
        return {"ok": False, "error": "session not found", "exit_code": shared.EXIT_SESSION_NOT_FOUND}

    args = SimpleNamespace(session_key="missing", all=False)
    _, exit_code = cli.cmd_release(args, send_request=fake_send_request)

    assert exit_code == shared.EXIT_SESSION_NOT_FOUND


def test_cmd_hold_sends_expected_payload():
    captured = {}

    def fake_send_request(sock_path, payload, timeout=5.0):
        captured["payload"] = payload
        return {"ok": True, "hold_id": "hold-1", "expires_at": 123.0}

    args = SimpleNamespace(duration="30m", reason="deploy")
    _, exit_code = cli.cmd_hold(args, send_request=fake_send_request)

    assert captured["payload"] == {"cmd": "HOLD", "for": "30m", "reason": "deploy"}
    assert exit_code == shared.EXIT_OK


def test_cmd_status_returns_daemon_payload():
    def fake_send_request(sock_path, payload, timeout=5.0):
        assert payload == {"cmd": "STATUS"}
        return {"ok": True, "status": "IDLE"}

    response, exit_code = cli.cmd_status(SimpleNamespace(), send_request=fake_send_request)
    assert response["status"] == "IDLE"
    assert exit_code == shared.EXIT_OK


def test_cmd_status_returns_daemon_not_running():
    def fake_send_request(sock_path, payload, timeout=5.0):
        raise ConnectionError("gone")

    _, exit_code = cli.cmd_status(SimpleNamespace(), send_request=fake_send_request)
    assert exit_code == shared.EXIT_DAEMON_NOT_RUNNING


def test_build_parser_parses_track():
    args = cli.build_parser().parse_args(["track", "abc-123", "--tool", "claude", "--pids", "1001", "1002"])
    assert args.command == "track"
    assert args.session_key == "abc-123"
    assert args.tool == "claude"
    assert args.pids == [1001, 1002]


def test_cmd_track_sends_expected_payload():
    captured = {}

    def fake_send_request(sock_path, payload, timeout=5.0):
        captured["payload"] = payload
        return {"ok": True, "status": "ACTIVE", "count": 1}

    args = SimpleNamespace(session_key="abc-123", tool="claude", pids=[1001, 1002])
    _, exit_code = cli.cmd_track(args, send_request=fake_send_request)

    assert captured["payload"] == {"cmd": "TRACK", "session": "abc-123", "tool": "claude", "pids": [1001, 1002]}
    assert exit_code == shared.EXIT_OK


def test_cmd_track_returns_daemon_not_running():
    def fake_send_request(sock_path, payload, timeout=5.0):
        raise ConnectionError("no socket")

    args = SimpleNamespace(session_key="abc-123", tool="claude", pids=[1001])
    response, exit_code = cli.cmd_track(args, send_request=fake_send_request)

    assert response["ok"] is False
    assert exit_code == shared.EXIT_DAEMON_NOT_RUNNING


# --- hook install/uninstall dispatch ---


class _FakeHookModule:
    def __init__(self, installed=True, name="fake"):
        self._installed = installed
        self.name = name
        self.install_called = False
        self.uninstall_called = False

    def detect(self):
        return self._installed

    def install(self):
        self.install_called = True
        return {"ok": True}

    def uninstall(self):
        self.uninstall_called = True
        return {"ok": True}


def test_cmd_install_hooks_requires_agent_or_all():
    args = SimpleNamespace(agent=None, all=False)
    response, exit_code = cli.cmd_install_hooks(args, agent_modules={})
    assert response["ok"] is False
    assert exit_code == shared.EXIT_INVALID_ARGS


def test_cmd_install_hooks_installs_detected_agent():
    claude = _FakeHookModule(installed=True)
    args = SimpleNamespace(agent="claude", all=False)

    response, exit_code = cli.cmd_install_hooks(args, agent_modules={"claude": claude})

    assert claude.install_called is True
    assert response["installed"] == ["claude"]
    assert exit_code == shared.EXIT_OK


def test_cmd_install_hooks_skips_undetected_agent():
    codex = _FakeHookModule(installed=False)
    args = SimpleNamespace(agent="codex", all=False)

    response, exit_code = cli.cmd_install_hooks(args, agent_modules={"codex": codex})

    assert codex.install_called is False
    assert response["skipped"] == ["codex"]
    assert exit_code == shared.EXIT_AGENT_NOT_DETECTED


def test_cmd_install_hooks_all_installs_every_detected_agent():
    claude = _FakeHookModule(installed=True)
    codex = _FakeHookModule(installed=False)
    args = SimpleNamespace(agent=None, all=True)

    response, exit_code = cli.cmd_install_hooks(
        args, agent_modules={"claude": claude, "codex": codex}
    )

    assert sorted(response["installed"]) == ["claude"]
    assert sorted(response["skipped"]) == ["codex"]


def test_cmd_uninstall_hooks_restores_agent():
    claude = _FakeHookModule(installed=True)
    args = SimpleNamespace(agent="claude", all=False)

    response, exit_code = cli.cmd_uninstall_hooks(args, agent_modules={"claude": claude})

    assert claude.uninstall_called is True
    assert response["ok"] is True
    assert exit_code == shared.EXIT_OK


# --- daemon / helper lifecycle plumbing ---


@pytest.fixture
def isolated_daemon_plist(tmp_path, monkeypatch):
    """Redirect the daemon plist + state dir to a throwaway tmp location so
    daemon-lifecycle tests never touch the maintainer's real LaunchAgent."""
    plist_path = tmp_path / "com.rjmorales.6ix9ine.daemon.plist"
    monkeypatch.setattr(shared, "DAEMON_PLIST_PATH", plist_path)
    monkeypatch.setenv("SIXNINE_STATE_DIR", str(tmp_path / "state"))
    return plist_path


def _reachable_send_request(*_a, **_k):
    return {"ok": True}


def _unreachable_send_request(*_a, **_k):
    raise ConnectionError("no daemon")


def test_cmd_daemon_start_invokes_launchctl_load(isolated_daemon_plist):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    response, exit_code = cli.cmd_daemon_start(
        run=fake_run, send_request=_reachable_send_request, sleep=lambda _d: None
    )
    assert ["launchctl", "load"] in [c[:2] for c in calls]
    assert response["ok"] is True
    assert exit_code == shared.EXIT_OK


def test_cmd_daemon_start_writes_plist_when_absent(isolated_daemon_plist):
    def fake_run(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    assert not isolated_daemon_plist.exists()
    response, _ = cli.cmd_daemon_start(
        run=fake_run, send_request=_reachable_send_request, sleep=lambda _d: None
    )
    assert isolated_daemon_plist.exists()
    assert shared.DAEMON_BUNDLE_ID in isolated_daemon_plist.read_text()
    assert response["regenerated_plist"] is True


def test_cmd_daemon_start_regenerates_stale_plist_and_unloads_first(isolated_daemon_plist):
    # Simulate a stale plist from a previous install pointing at a dead path.
    isolated_daemon_plist.write_text("<plist>STALE /Cellar/6ix9ine/1.0.0/bin</plist>")
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd[:2])
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    response, exit_code = cli.cmd_daemon_start(
        run=fake_run, send_request=_reachable_send_request, sleep=lambda _d: None
    )
    # Must unload the stale registration BEFORE loading the corrected one.
    assert calls == [["launchctl", "unload"], ["launchctl", "load"]]
    # Plist was rewritten to the freshly computed content.
    assert "STALE" not in isolated_daemon_plist.read_text()
    assert response["regenerated_plist"] is True
    assert exit_code == shared.EXIT_OK


def test_cmd_daemon_start_no_churn_when_plist_current(isolated_daemon_plist):
    # First start writes the correct plist.
    def fake_run(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    cli.cmd_daemon_start(run=fake_run, send_request=_reachable_send_request, sleep=lambda _d: None)

    # Second start with an unchanged environment must NOT unload/rewrite.
    calls = []

    def tracking_run(cmd, **kwargs):
        calls.append(cmd[:2])
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    response, _ = cli.cmd_daemon_start(
        run=tracking_run, send_request=_reachable_send_request, sleep=lambda _d: None
    )
    assert calls == [["launchctl", "load"]]  # no unload
    assert response["regenerated_plist"] is False


def test_cmd_daemon_start_reports_failure_when_never_reachable(isolated_daemon_plist):
    # launchctl exits 0 (the exact false-success case) but the daemon never
    # opens its socket -> must report ok:false, not trust the exit code.
    def fake_run(cmd, **kwargs):
        return SimpleNamespace(
            returncode=0, stdout="", stderr="Load failed: 5: Input/output error"
        )

    response, exit_code = cli.cmd_daemon_start(
        run=fake_run, send_request=_unreachable_send_request, sleep=lambda _d: None
    )
    assert response["ok"] is False
    assert "did not become reachable" in response["error"]
    assert "Input/output error" in response["error"]
    assert exit_code == shared.EXIT_GENERAL_ERROR


def test_cmd_daemon_stop_invokes_launchctl_unload(isolated_daemon_plist):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    response, exit_code = cli.cmd_daemon_stop(
        run=fake_run, send_request=_unreachable_send_request, sleep=lambda _d: None
    )
    assert calls[0][:2] == ["launchctl", "unload"]
    assert response["ok"] is True
    assert exit_code == shared.EXIT_OK


def test_cmd_daemon_stop_reports_failure_when_still_reachable(isolated_daemon_plist):
    def fake_run(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    # Daemon keeps answering its socket -> unload did not really stop it.
    response, exit_code = cli.cmd_daemon_stop(
        run=fake_run, send_request=_reachable_send_request, sleep=lambda _d: None
    )
    assert response["ok"] is False
    assert "still reachable" in response["error"]
    assert exit_code == shared.EXIT_GENERAL_ERROR


def test_cmd_daemon_status_reports_not_running_on_connection_error():
    def fake_send_request(sock_path, payload, timeout=5.0):
        raise ConnectionError("gone")

    response, exit_code = cli.cmd_daemon_status(send_request=fake_send_request)
    assert response["running"] is False
    assert exit_code == shared.EXIT_DAEMON_NOT_RUNNING


def test_cmd_helper_status_reports_not_running_on_connection_error():
    def fake_send_request(sock_path, payload, timeout=5.0):
        raise ConnectionError("gone")

    response, exit_code = cli.cmd_helper_status(send_request=fake_send_request)
    assert response["running"] is False
    assert exit_code == shared.EXIT_HELPER_NOT_RUNNING


def test_cmd_helper_status_reports_running_state():
    def fake_send_request(sock_path, payload, timeout=5.0):
        assert payload == {"method": "get_state"}
        return {"ok": True, "sleep_blocked": False, "version": shared.VERSION}

    response, exit_code = cli.cmd_helper_status(send_request=fake_send_request)
    assert response["running"] is True
    assert exit_code == shared.EXIT_OK


def test_build_setup_helper_script_includes_owner_uid_and_key_paths(tmp_path):
    script = cli.build_setup_helper_script(project_root=tmp_path, owner_uid=501)
    assert "501" in script
    assert str(shared.HELPER_PLIST_PATH) in script
    assert str(shared.HELPER_INSTALL_PATH) in script
    assert "launchctl load" in script


def test_build_setup_helper_script_boots_out_stale_registration_before_load(tmp_path):
    # The stale KeepAlive process must be booted out BEFORE the (re)load,
    # otherwise `launchctl load`/`bootstrap` exit 0 while the old root process
    # keeps running old code. Verify the bootout is present AND ordered first.
    script = cli.build_setup_helper_script(project_root=tmp_path, owner_uid=501)
    assert "launchctl bootout system" in script
    bootout_idx = script.index("launchctl bootout system")
    load_idx = script.rindex("launchctl load")
    assert bootout_idx < load_idx, "bootout must precede load"
    # Guarded so `set -e` doesn't abort when nothing is currently loaded.
    assert "|| true" in script.splitlines()[
        next(i for i, ln in enumerate(script.splitlines()) if "launchctl bootout system" in ln)
    ]


def _helper_send_request(version):
    """Fake helper socket that answers get_state with the given version, or
    raises ConnectionError when version is None (socket dark)."""

    def send_request(sock_path, payload, timeout=5.0):
        assert payload == {"method": "get_state"}
        if version is None:
            raise ConnectionError("no helper")
        return {"ok": True, "sleep_blocked": False, "version": version}

    return send_request


def test_cmd_setup_privileged_helper_maps_script_failure_to_permission_denied():
    def fake_run(cmd, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="not authorized")

    response, exit_code = cli.cmd_setup_privileged_helper(
        run=fake_run,
        project_root=None,
        send_request=_helper_send_request(shared.VERSION),
        sleep=lambda _d: None,
    )
    assert response["ok"] is False
    assert exit_code == shared.EXIT_PERMISSION_DENIED


def test_cmd_setup_privileged_helper_ok_when_current_version_answers():
    def fake_run(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    response, exit_code = cli.cmd_setup_privileged_helper(
        run=fake_run,
        project_root=None,
        send_request=_helper_send_request(shared.VERSION),
        sleep=lambda _d: None,
    )
    assert response["ok"] is True
    assert response["helper_version"] == shared.VERSION
    assert exit_code == shared.EXIT_OK


def test_cmd_setup_privileged_helper_fails_when_stale_old_version_still_answers():
    # The exact bug: script exits 0, socket is reachable, but it's the OLD
    # process answering. Bare reachability would rubber-stamp this; the version
    # handshake must reject it.
    def fake_run(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    response, exit_code = cli.cmd_setup_privileged_helper(
        run=fake_run,
        project_root=None,
        send_request=_helper_send_request("0.9.0-old"),
        sleep=lambda _d: None,
    )
    assert response["ok"] is False
    assert "0.9.0-old" in response["error"]
    assert shared.VERSION in response["error"]
    assert exit_code == shared.EXIT_GENERAL_ERROR


def test_cmd_setup_privileged_helper_fails_when_socket_never_answers():
    def fake_run(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    response, exit_code = cli.cmd_setup_privileged_helper(
        run=fake_run,
        project_root=None,
        send_request=_helper_send_request(None),
        sleep=lambda _d: None,
    )
    assert response["ok"] is False
    assert "did not become reachable" in response["error"]
    assert exit_code == shared.EXIT_GENERAL_ERROR


def test_cmd_uninstall_helper_uses_set_e_and_bootout_in_script():
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    response, exit_code = cli.cmd_uninstall_helper(
        run=fake_run,
        send_request=_helper_send_request(None),  # socket goes dark -> success
        sleep=lambda _d: None,
    )
    script = calls[0][-1]
    assert script.splitlines()[0] == "set -e"
    assert "launchctl bootout system" in script
    assert "pmset disablesleep 0" in script
    assert response["ok"] is True
    assert exit_code == shared.EXIT_OK


def test_cmd_uninstall_helper_fails_when_helper_still_reachable():
    # Teardown script exits 0 but the root helper is still answering its socket
    # -> the teardown did not really complete.
    def fake_run(cmd, **kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    response, exit_code = cli.cmd_uninstall_helper(
        run=fake_run,
        send_request=_helper_send_request(shared.VERSION),  # still reachable
        sleep=lambda _d: None,
    )
    assert response["ok"] is False
    assert "still reachable" in response["error"]
    assert exit_code == shared.EXIT_GENERAL_ERROR


def test_cmd_uninstall_helper_maps_script_failure_to_permission_denied():
    def fake_run(cmd, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="not authorized")

    response, exit_code = cli.cmd_uninstall_helper(
        run=fake_run,
        send_request=_helper_send_request(None),
        sleep=lambda _d: None,
    )
    assert response["ok"] is False
    assert exit_code == shared.EXIT_PERMISSION_DENIED


# --- top-level dispatch ---


def test_main_version_prints_version_string(capsys):
    exit_code = cli.main(["--version"])
    captured = capsys.readouterr()
    assert shared.version_string() in captured.out
    assert exit_code == shared.EXIT_OK


def test_main_dispatches_to_acquire(monkeypatch, capsys):
    monkeypatch.setattr(
        cli.ipc, "send_request", lambda sock, payload, timeout=5.0: {"ok": True, "status": "ACTIVE", "count": 1}
    )
    exit_code = cli.main(["acquire", "k1", "--tool", "claude"])
    assert exit_code == shared.EXIT_OK
    assert "ACTIVE" in capsys.readouterr().out


# --- Claude Code hook entrypoints (hook-acquire / hook-release) ---


def _feed_stdin(monkeypatch, text):
    import io

    monkeypatch.setattr(cli.sys, "stdin", io.StringIO(text))


def test_build_parser_parses_hook_subcommands():
    assert cli.build_parser().parse_args(["hook-acquire"]).command == "hook-acquire"
    assert cli.build_parser().parse_args(["hook-release"]).command == "hook-release"


def test_hook_acquire_sends_acquire_payload_from_stdin(monkeypatch):
    captured = {}

    def fake_send(sock, payload):
        captured["payload"] = payload
        return {"ok": True}

    _feed_stdin(monkeypatch, json.dumps({"session_id": "s1", "prompt": "build a thing"}))
    args = SimpleNamespace(command="hook-acquire")
    rc = cli.cmd_hook_acquire(args, send_request=fake_send)

    assert rc == shared.EXIT_OK
    assert captured["payload"]["cmd"] == "ACQUIRE"
    assert captured["payload"]["session"] == "s1"
    assert captured["payload"]["tool"] == "claude"
    assert captured["payload"]["reason"] == "build a thing"


def test_hook_release_sends_release_payload_from_stdin(monkeypatch):
    captured = {}

    def fake_send(sock, payload):
        captured["payload"] = payload
        return {"ok": True}

    _feed_stdin(monkeypatch, json.dumps({"session_id": "s2"}))
    rc = cli.cmd_hook_release(SimpleNamespace(command="hook-release"), send_request=fake_send)

    assert rc == shared.EXIT_OK
    assert captured["payload"] == {"cmd": "RELEASE", "session": "s2"}


def test_hook_acquire_always_exits_zero_when_daemon_down(monkeypatch):
    def boom(sock, payload):
        raise ConnectionError("daemon not running")

    _feed_stdin(monkeypatch, json.dumps({"session_id": "s1", "prompt": "hi"}))
    rc = cli.cmd_hook_acquire(SimpleNamespace(command="hook-acquire"), send_request=boom)
    assert rc == shared.EXIT_OK


def test_hook_acquire_exits_zero_on_garbage_stdin(monkeypatch):
    _feed_stdin(monkeypatch, "not json at all {{{")
    rc = cli.cmd_hook_acquire(SimpleNamespace(command="hook-acquire"), send_request=None)
    assert rc == shared.EXIT_OK


def test_hook_release_exits_zero_on_empty_stdin(monkeypatch):
    _feed_stdin(monkeypatch, "")
    rc = cli.cmd_hook_release(SimpleNamespace(command="hook-release"), send_request=None)
    assert rc == shared.EXIT_OK


def test_hook_acquire_missing_session_id_does_not_call_daemon(monkeypatch):
    called = {"n": 0}

    def fake_send(sock, payload):
        called["n"] += 1
        return {"ok": True}

    _feed_stdin(monkeypatch, json.dumps({"prompt": "no session id here"}))
    rc = cli.cmd_hook_acquire(SimpleNamespace(command="hook-acquire"), send_request=fake_send)
    assert rc == shared.EXIT_OK
    assert called["n"] == 0


def test_main_hook_acquire_is_silent_and_exits_zero(monkeypatch, capsys):
    monkeypatch.setattr(cli.ipc, "send_request", lambda *a, **k: {"ok": True, "status": "ACTIVE"})
    _feed_stdin(monkeypatch, json.dumps({"session_id": "s1", "prompt": "hi"}))

    exit_code = cli.main(["hook-acquire"])

    out = capsys.readouterr()
    assert exit_code == shared.EXIT_OK
    # MUST be empty: Claude Code injects UserPromptSubmit stdout into the prompt.
    assert out.out == ""


def test_main_hook_release_is_silent_and_exits_zero(monkeypatch, capsys):
    monkeypatch.setattr(cli.ipc, "send_request", lambda *a, **k: {"ok": True})
    _feed_stdin(monkeypatch, json.dumps({"session_id": "s1"}))

    exit_code = cli.main(["hook-release"])

    out = capsys.readouterr()
    assert exit_code == shared.EXIT_OK
    assert out.out == ""
