from __future__ import annotations

from types import SimpleNamespace

import pytest

import cli
import shared
from daemon import Daemon
from thermal_monitor import ThermalMonitor


# --------------------------------------------------------------------------
# Task 1: `6ix9ine thermal status` CLI command
# --------------------------------------------------------------------------


def _status_response(thermal: dict) -> dict:
    return {"ok": True, "status": "ACTIVE", "thermal": thermal}


def _fake_send(state: dict):
    def send_request(sock_path, payload, timeout=5.0):
        assert payload == {"cmd": "STATUS"}
        return state

    return send_request


def test_cmd_thermal_status_cool_output(capsys):
    send = _fake_send(_status_response({"current_temp": 52.0, "peak_temp": 68.0, "cutout_threshold": 85.0, "cutout_fired": False}))
    response, exit_code = cli.cmd_thermal_status(SimpleNamespace(), send_request=send)
    out = capsys.readouterr().out
    assert exit_code == shared.EXIT_OK
    assert "COOL" in out
    assert "52°C" in out
    assert "Peak: 68°C" in out
    assert "Not triggered" in out


def test_cmd_thermal_status_hot_output(capsys):
    send = _fake_send(_status_response({"current_temp": 88.0, "peak_temp": 90.0, "cutout_threshold": 85.0, "cutout_fired": False}))
    response, exit_code = cli.cmd_thermal_status(SimpleNamespace(), send_request=send)
    out = capsys.readouterr().out
    assert exit_code == shared.EXIT_OK
    assert "HOT" in out
    assert "88°C" in out


def test_cmd_thermal_status_critical_cutout_output(capsys):
    send = _fake_send(_status_response({"current_temp": 97.0, "peak_temp": 97.0, "cutout_threshold": 85.0, "cutout_fired": True}))
    response, exit_code = cli.cmd_thermal_status(SimpleNamespace(), send_request=send)
    out = capsys.readouterr().out
    assert exit_code == shared.EXIT_OK
    assert "CRITICAL" in out
    assert "TRIGGERED" in out


def test_cmd_thermal_status_unknown_when_no_reading(capsys):
    send = _fake_send(_status_response({"current_temp": None, "peak_temp": 0.0, "cutout_threshold": 85.0, "cutout_fired": False}))
    response, exit_code = cli.cmd_thermal_status(SimpleNamespace(), send_request=send)
    out = capsys.readouterr().out
    assert exit_code == shared.EXIT_OK
    assert "UNKNOWN" in out


def test_cmd_thermal_status_daemon_not_running():
    def send_request(sock_path, payload, timeout=5.0):
        raise ConnectionError("no socket")

    response, exit_code = cli.cmd_thermal_status(SimpleNamespace(), send_request=send_request)
    assert response["ok"] is False
    assert exit_code == shared.EXIT_DAEMON_NOT_RUNNING


def test_build_parser_parses_thermal_status():
    args = cli.build_parser().parse_args(["thermal", "status"])
    assert args.command == "thermal"
    assert args.thermal_command == "status"


def test_thermal_label_bands():
    assert cli.thermal_label(40.0)[0] == "COOL"
    assert cli.thermal_label(60.0)[0] == "WARM"
    assert cli.thermal_label(80.0)[0] == "HOT"
    assert cli.thermal_label(95.0)[0] == "CRITICAL"


# --------------------------------------------------------------------------
# Task 2: dashboard thermal chip (tui.build_thermal_meta)
# --------------------------------------------------------------------------


def test_build_thermal_meta_renders_temp():
    from tui import build_thermal_meta

    meta = build_thermal_meta({"thermal": {"current_temp": 52.0, "peak_temp": 68.0, "cutout_fired": False}})
    assert meta is not None
    assert "52°C" in meta.plain
    assert "peak 68°C" in meta.plain


def test_build_thermal_meta_color_coding():
    from tui import build_thermal_meta

    cool = build_thermal_meta({"thermal": {"current_temp": 40.0}})
    warm = build_thermal_meta({"thermal": {"current_temp": 70.0}})
    hot = build_thermal_meta({"thermal": {"current_temp": 88.0}})
    critical = build_thermal_meta({"thermal": {"current_temp": 97.0}})

    def color_of(text):
        # Rich drops spans that match the Text's base style, so fall back to it.
        if text.spans:
            return str(text.spans[0].style)
        return str(text.style)

    assert color_of(cool) == "#4ec973"
    assert color_of(warm) == "#e8c84a"
    assert color_of(hot) == "#ff8c42"
    assert color_of(critical) == "#ff5b5b"


def test_build_thermal_meta_none_when_unknown():
    from tui import build_thermal_meta

    assert build_thermal_meta({"thermal": {}}) is None
    assert build_thermal_meta({}) is None


def test_build_topline_meta_includes_thermal_when_present():
    from tui import build_topline_meta

    meta = build_topline_meta(
        {"active_sessions": {}, "holds": [], "lid": "open", "thermal": {"current_temp": 52.0}},
        clock="14:32:08",
    ).plain
    assert "52°C" in meta
    assert "lid open" in meta


# --------------------------------------------------------------------------
# Task 3: daemon releases sessions when cutout fires (any lid state)
# --------------------------------------------------------------------------


def _make_daemon_for_thermal(tmp_path, lid_state, temperature):
    import lid_monitor
    import session_registry

    helper_calls = []

    async def fake_transport(sock_path, payload, timeout=5.0):
        if payload.get("method") == "get_thermal":
            return {"ok": True, "temperature": temperature}
        helper_calls.append(payload)
        return {"ok": True, "sleep_blocked": payload.get("params", {}).get("blocked", False)}

    notify_calls = []
    daemon = Daemon(
        registry=session_registry.SessionRegistry(),
        lid=lid_monitor.LidMonitor(),
        thermal=ThermalMonitor(threshold=85.0),
        state_file=tmp_path / "state.json",
        transport=fake_transport,
        play_chime_fn=lambda: None,
        notify_summary_fn=lambda *a, **k: notify_calls.append((a, k)),
        pid_exists_fn=lambda pid: True,
        read_lid_state_fn=lambda: lid_state,
    )
    return daemon, helper_calls, notify_calls


@pytest.mark.asyncio
async def test_daemon_releases_on_cutout_with_lid_open(tmp_path):
    daemon, helper_calls, notify_calls = _make_daemon_for_thermal(tmp_path, "open", 95.0)
    await daemon.handle_request({"cmd": "ACQUIRE", "session": "k1", "tool": "claude"}, peer_pid=1)

    await daemon.tick()

    assert daemon.registry.count() == 0
    assert daemon.thermal.cutout_fired is True
    # Lid open => user-facing notification that sleep protection was released.
    assert len(notify_calls) == 1


@pytest.mark.asyncio
async def test_daemon_releases_on_cutout_with_lid_closed(tmp_path):
    daemon, helper_calls, notify_calls = _make_daemon_for_thermal(tmp_path, "closed", 95.0)
    await daemon.handle_request({"cmd": "ACQUIRE", "session": "k1", "tool": "claude"}, peer_pid=1)

    await daemon.tick()

    assert daemon.registry.count() == 0
    assert daemon.thermal.cutout_fired is True
    # Lid closed => no open-lid summary notification.
    assert len(notify_calls) == 0


@pytest.mark.asyncio
async def test_daemon_does_not_release_below_threshold(tmp_path):
    daemon, helper_calls, notify_calls = _make_daemon_for_thermal(tmp_path, "open", 70.0)
    await daemon.handle_request({"cmd": "ACQUIRE", "session": "k1", "tool": "claude"}, peer_pid=1)

    await daemon.tick()

    assert daemon.registry.count() == 1
    assert daemon.thermal.cutout_fired is False


@pytest.mark.asyncio
async def test_daemon_persists_thermal_state(tmp_path):
    daemon, helper_calls, notify_calls = _make_daemon_for_thermal(tmp_path, "open", 90.0)
    await daemon.tick()

    import json

    state = json.loads((tmp_path / "state.json").read_text())
    assert state.get("last_thermal_reading") == 90.0


# --------------------------------------------------------------------------
# Task 5: env-var overrides
# --------------------------------------------------------------------------


def test_env_var_threshold_override(monkeypatch):
    monkeypatch.setenv("SIXNINE_THERMAL_THRESHOLD", "90")
    assert shared.thermal_threshold() == 90.0


def test_env_var_threshold_default(monkeypatch):
    monkeypatch.delenv("SIXNINE_THERMAL_THRESHOLD", raising=False)
    assert shared.thermal_threshold() == 85.0


def test_env_var_alert_override(monkeypatch):
    monkeypatch.setenv("SIXNINE_THERMAL_ALERT", "75")
    assert shared.thermal_alert_threshold() == 75.0


def test_env_var_alert_default(monkeypatch):
    monkeypatch.delenv("SIXNINE_THERMAL_ALERT", raising=False)
    assert shared.thermal_alert_threshold() == 70.0
