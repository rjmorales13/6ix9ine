import io
import json
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

import cli
from hooks import codex


def test_install_reinstall_and_uninstall_preserve_user_hooks(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    binary = tmp_path / "path with spaces" / "staywoke"
    monkeypatch.setattr(codex.shutil, "which", lambda _: str(binary))
    path = tmp_path / "hooks.json"
    original = {
        "description": "My hooks",
        "hooks": {
            "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "my-submit-hook"}]}],
            "Stop": [{"hooks": [{"type": "command", "command": "my-stop-hook"}]}],
            "SessionStart": [{"matcher": "resume", "hooks": []}],
        },
    }
    legacy = {"type": "command", "command": "/old/staywoke hook-acquire --tool codex"}
    on_disk = json.loads(json.dumps(original))
    on_disk["hooks"]["UserPromptSubmit"][0]["hooks"].append(legacy)
    path.write_text(json.dumps(on_disk))

    assert codex.detect()
    assert codex.install()["ok"]
    assert codex.verify()
    first_install = path.read_bytes()
    assert codex.install()["ok"]
    assert path.read_bytes() == first_install
    hooks = json.loads(first_install)["hooks"]
    assert hooks["Stop"][0] == original["hooks"]["Stop"][0]
    assert hooks["UserPromptSubmit"] == original["hooks"]["UserPromptSubmit"]
    for event, subcommand in (
        ("PreModelRequest", "hook-acquire"),
        ("PostModelRequest", "hook-release"),
        ("Stop", "hook-release"),
        ("Interrupt", "hook-release"),
        ("SessionEnd", "hook-release"),
    ):
        assert shlex.split(hooks[event][-1]["hooks"][0]["command"]) == [
            str(binary), subcommand, "--tool", "codex"
        ]

    assert codex.uninstall()["ok"]
    assert not codex.verify()
    assert json.loads(path.read_text()) == original


@pytest.mark.parametrize("invalid", ["{", '[]', '{"hooks":{"Stop":42}}'])
def test_invalid_config_is_preserved(monkeypatch, tmp_path, invalid):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    path = tmp_path / "hooks.json"
    path.write_text(invalid)

    assert not codex.install()["ok"]
    assert not codex.uninstall()["ok"]
    assert not codex.verify()
    assert path.read_text() == invalid


def test_codex_cli_hooks_send_daemon_requests_without_leaking_prompt(monkeypatch, capsys):
    requests = []

    def send_request(path, payload, timeout):
        requests.append(payload)
        return {"ok": True}

    monkeypatch.setattr(cli.ipc, "send_request", send_request)
    monkeypatch.setattr("sys.stdin", io.StringIO('{"session_id":"thread-1","hook_event_name":"PreModelRequest","prompt":"private"}'))
    assert cli.main(["hook-acquire", "--tool", "codex"]) == 0
    assert capsys.readouterr().out == ""
    monkeypatch.setattr("sys.stdin", io.StringIO('{"session_id":"thread-1"}'))
    assert cli.main(["hook-release", "--tool", "codex"]) == 0
    assert json.loads(capsys.readouterr().out) == {}
    assert requests == [
        {"cmd": "ACQUIRE", "session": "thread-1", "tool": "codex", "reason": "codex turn"},
        {"cmd": "RELEASE", "session": "thread-1"},
    ]


def test_codex_release_fails_open_for_malformed_input(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("{"))
    assert cli.main(["hook-release", "--tool", "codex"]) == 0
    assert json.loads(capsys.readouterr().out) == {}


def test_codex_subagent_model_request_does_not_acquire_parent_hold(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli.ipc, "send_request", lambda *args, **kwargs: calls.append(args))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({
        "session_id": "parent-thread",
        "thread_id": "child-thread",
        "hook_event_name": "PreModelRequest",
        "agent_id": "child-thread",
        "agent_type": "default",
    })))
    assert cli.main(["hook-acquire", "--tool", "codex"]) == 0
    assert capsys.readouterr().out == ""
    assert calls == []


def test_homebrew_registers_codex_with_homebrew_binary(monkeypatch, tmp_path):
    project = Path(__file__).resolve().parents[2]
    prefix = tmp_path / "brew prefix"
    bin_dir = prefix / "bin"
    bin_dir.mkdir(parents=True)
    shadow_dir = tmp_path / "source bin"
    shadow_dir.mkdir()
    codex_home = tmp_path / "codex"
    codex_home.mkdir()

    def executable(path, body):
        path.write_text("#!/bin/sh\n" + body)
        path.chmod(0o755)

    executable(shadow_dir / "staywoke", "exit 99\n")
    executable(shadow_dir / "uname", "echo Darwin\n")
    executable(shadow_dir / "brew", f"""
case "$1" in
  tap) echo rjmorales13/staywoke ;;
  command) exit 1 ;;
  --cellar|--prefix) echo {shlex.quote(str(prefix))} ;;
  list) echo 'staywoke 1.0.0' ;;
esac
""")
    cli_cmd = shlex.join([sys.executable, str(project / "bin" / "cli.py")])
    executable(bin_dir / "staywoke", f"""
if [ "$1" = install-hooks ] && [ "$3" = codex ]; then
    exec {cli_cmd} "$@"
fi
""")
    monkeypatch.setenv("PATH", f"{shadow_dir}:/usr/bin:/bin")
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    subprocess.run(["/bin/bash", project / "scripts/install-staywoke-homebrew.sh"], check=True)
    hooks = json.loads((codex_home / "hooks.json").read_text())["hooks"]
    command = hooks["PreModelRequest"][0]["hooks"][0]["command"]
    assert shlex.split(command)[0] == str(bin_dir / "staywoke")


def test_frozen_codex_install_prefers_its_invoked_launcher(monkeypatch, tmp_path):
    cellared = tmp_path / "Cellar" / "staywoke" / "1.0.6" / "bin" / "staywoke"
    stable = tmp_path / "brew prefix" / "bin" / "staywoke"
    shadow = tmp_path / "source bin" / "staywoke"
    for path in (cellared, stable, shadow):
        path.parent.mkdir(parents=True)
    for binary in (cellared, shadow):
        binary.touch()
        binary.chmod(0o755)
    stable.symlink_to(cellared)

    monkeypatch.setenv("PATH", f"{shadow.parent}:{stable.parent}")
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    monkeypatch.setattr(codex.sys, "frozen", True, raising=False)
    monkeypatch.setattr(codex.sys, "executable", str(cellared))
    monkeypatch.setattr(codex.sys, "argv", [str(stable), "install-hooks", "--agent", "codex"])

    assert codex.install()["ok"]
    path = tmp_path / "codex" / "hooks.json"
    hooks = json.loads(path.read_text())["hooks"]
    assert shlex.split(hooks["PreModelRequest"][0]["hooks"][0]["command"])[0] == str(stable)

    stable.unlink()
    assert codex.install()["ok"]
    hooks = json.loads(path.read_text())["hooks"]
    assert shlex.split(hooks["PreModelRequest"][0]["hooks"][0]["command"])[0] == str(cellared)


@pytest.mark.parametrize("status, agent_id, releases", [
    ("completed", None, False),
    ("failed", "child-thread", False),
    ("cancelled", "child-thread", False),
    ("failed", None, True),
    ("cancelled", None, True),
])
def test_codex_post_model_only_releases_failed_main_thread_requests(
    monkeypatch, capsys, status, agent_id, releases
):
    requests = []

    def send_request(path, payload, timeout):
        requests.append(payload)
        return {"ok": True}

    monkeypatch.setattr(cli.ipc, "send_request", send_request)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({
        "session_id": "parent-thread",
        "hook_event_name": "PostModelRequest",
        "status": status,
        "agent_id": agent_id,
    })))
    assert cli.main(["hook-release", "--tool", "codex"]) == 0
    assert json.loads(capsys.readouterr().out) == {}
    assert requests == ([{"cmd": "RELEASE", "session": "parent-thread"}] if releases else [])
