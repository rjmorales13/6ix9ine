from __future__ import annotations

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


def test_cmd_daemon_start_invokes_launchctl_load():
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    _, exit_code = cli.cmd_daemon_start(run=fake_run)
    assert calls[0][:2] == ["launchctl", "load"]
    assert exit_code == shared.EXIT_OK


def test_cmd_daemon_stop_invokes_launchctl_unload():
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    cli.cmd_daemon_stop(run=fake_run)
    assert calls[0][:2] == ["launchctl", "unload"]


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


def test_cmd_setup_privileged_helper_maps_failure_to_permission_denied():
    def fake_run(cmd, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="not authorized")

    _, exit_code = cli.cmd_setup_privileged_helper(run=fake_run, project_root=None)
    assert exit_code == shared.EXIT_PERMISSION_DENIED


def test_cmd_uninstall_helper_resets_pmset_in_script():
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    _, exit_code = cli.cmd_uninstall_helper(run=fake_run)
    script = calls[0][-1]
    assert "pmset disablesleep 0" in script
    assert exit_code == shared.EXIT_OK


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
