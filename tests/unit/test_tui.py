from __future__ import annotations

import json

import pytest

import shared
import tui


def test_build_session_rows_extracts_expected_columns():
    state = {
        "active_sessions": {
            "k1": {"agent": "claude", "reason": "building", "held_for": "15m 32s"},
        }
    }
    assert tui.build_session_rows(state) == [("k1", "claude", "building", "15m 32s")]


def test_build_session_rows_empty_when_idle():
    assert tui.build_session_rows({"active_sessions": {}}) == []


def test_build_auxiliary_rows_formats_cpu_and_memory():
    processes = [{"name": "ollama", "pid": 9876, "status": "sleeping", "cpu_percent": 0.0, "memory_gb": 2.14}]
    rows = tui.build_auxiliary_rows(processes, ignored=set())
    assert rows == [("ollama", "9876", "sleeping", "0.0%", "2.14 GB")]


def test_build_auxiliary_rows_skips_ignored_processes():
    processes = [
        {"name": "ollama", "pid": 1, "status": "sleeping", "cpu_percent": 0.0, "memory_gb": 1.0},
        {"name": "dockerd", "pid": 2, "status": "running", "cpu_percent": 1.2, "memory_gb": 0.85},
    ]
    rows = tui.build_auxiliary_rows(processes, ignored={"ollama"})
    assert [row[0] for row in rows] == ["dockerd"]


def test_save_and_load_filter_round_trip(tmp_path):
    filter_path = tmp_path / "filter.json"
    tui.save_filter({"ollama", "dockerd"}, path=filter_path)
    assert tui.load_filter(path=filter_path) == {"ollama", "dockerd"}


def test_load_filter_returns_empty_set_when_missing(tmp_path):
    assert tui.load_filter(path=tmp_path / "missing.json") == set()


def test_load_filter_returns_empty_set_on_corrupt_file(tmp_path):
    filter_path = tmp_path / "filter.json"
    filter_path.write_text("not json")
    assert tui.load_filter(path=filter_path) == set()


def test_perform_hard_kill_wipes_state_file_and_calls_both_sockets(tmp_path):
    state_file = tmp_path / "state.json"
    state_file.write_text("{}")
    calls = []

    def fake_send_request(sock_path, payload, timeout=5.0):
        calls.append((str(sock_path), payload))
        return {"ok": True}

    result = tui.perform_hard_kill(send_request=fake_send_request, state_file=state_file)

    assert result["ok"] is True
    assert not state_file.exists()
    assert {"cmd": "KILL_ALL"} in [payload for _, payload in calls]
    assert {"method": "set_sleep_blocked", "params": {"blocked": False}} in [payload for _, payload in calls]


def test_perform_hard_kill_tolerates_daemon_and_helper_being_down(tmp_path):
    state_file = tmp_path / "state.json"
    state_file.write_text("{}")

    def fake_send_request(sock_path, payload, timeout=5.0):
        raise ConnectionError("nothing running")

    result = tui.perform_hard_kill(send_request=fake_send_request, state_file=state_file)

    assert result["ok"] is True
    assert not state_file.exists()


def test_build_parser_kill_flag():
    args = tui.build_parser().parse_args(["--kill"])
    assert args.kill is True


def test_build_parser_defaults_kill_false():
    args = tui.build_parser().parse_args([])
    assert args.kill is False


def test_main_kill_flag_invokes_hard_kill_and_returns_ok(monkeypatch, tmp_path, capsys):
    state_file = tmp_path / "state.json"
    state_file.write_text("{}")
    monkeypatch.setattr(shared, "state_file_path", lambda: state_file)

    def fake_send_request(sock_path, payload, timeout=5.0):
        return {"ok": True}

    monkeypatch.setattr(tui.ipc, "send_request", fake_send_request)

    exit_code = tui.main(["--kill"])

    assert exit_code == shared.EXIT_OK
    printed = json.loads(capsys.readouterr().out)
    assert printed["ok"] is True
