from __future__ import annotations

from types import SimpleNamespace

import psutil
import pytest

import helper


def test_read_owner_uid_returns_none_when_file_missing(tmp_path):
    assert helper.read_owner_uid(tmp_path / "nope") is None


def test_read_owner_uid_parses_integer_from_file(tmp_path):
    owner_file = tmp_path / "owner"
    owner_file.write_text("501\n")
    assert helper.read_owner_uid(owner_file) == 501


def test_read_owner_uid_returns_none_on_garbage_content(tmp_path):
    owner_file = tmp_path / "owner"
    owner_file.write_text("not-a-uid")
    assert helper.read_owner_uid(owner_file) is None


def _fake_lookup(uid: int):
    def lookup(pid):
        return SimpleNamespace(uids=lambda: SimpleNamespace(real=uid))

    return lookup


def test_authorize_rejects_missing_peer_pid():
    ok, reason = helper.authorize(None, owner_uid=501)
    assert ok is False
    assert "pid" in reason


def test_authorize_rejects_when_no_owner_registered():
    ok, reason = helper.authorize(123, owner_uid=None)
    assert ok is False
    assert "owner" in reason


def test_authorize_rejects_uid_mismatch():
    ok, reason = helper.authorize(123, owner_uid=501, process_lookup=_fake_lookup(999))
    assert ok is False
    assert "999" in reason and "501" in reason


def test_authorize_accepts_matching_uid():
    ok, reason = helper.authorize(123, owner_uid=501, process_lookup=_fake_lookup(501))
    assert ok is True
    assert reason == "ok"


def test_authorize_rejects_when_process_vanished():
    def lookup(pid):
        raise psutil.NoSuchProcess(pid)

    ok, reason = helper.authorize(123, owner_uid=501, process_lookup=lookup)
    assert ok is False
    assert "no longer exists" in reason


def test_run_pmset_disablesleep_invokes_correct_arguments():
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0)

    assert helper.run_pmset_disablesleep(True, run=fake_run) is True
    assert calls[0] == ["pmset", "disablesleep", "1"]

    assert helper.run_pmset_disablesleep(False, run=fake_run) is True
    assert calls[1] == ["pmset", "disablesleep", "0"]


def test_run_pmset_disablesleep_returns_false_on_nonzero_exit():
    def fake_run(cmd, **kwargs):
        return SimpleNamespace(returncode=1)

    assert helper.run_pmset_disablesleep(True, run=fake_run) is False


def test_log_line_appends_timestamped_entry(tmp_path):
    log_path = tmp_path / "helper.log"
    helper.log_line("hello", log_path=log_path)
    helper.log_line("world", log_path=log_path)
    lines = log_path.read_text().splitlines()
    assert len(lines) == 2
    assert lines[0].endswith("hello")
    assert lines[1].endswith("world")


@pytest.mark.asyncio
async def test_handler_rejects_unauthorized_caller():
    state = helper.HelperState()
    handle = helper.make_handler(state, owner_uid=501, process_lookup=_fake_lookup(999))

    response = await handle({"method": "set_sleep_blocked", "params": {"blocked": True}}, 123)

    assert response["ok"] is False
    assert "unauthorized" in response["error"]
    assert state.sleep_blocked is False


@pytest.mark.asyncio
async def test_handler_set_sleep_blocked_updates_state_when_authorized(monkeypatch):
    state = helper.HelperState()
    monkeypatch.setattr(helper, "run_pmset_disablesleep", lambda blocked, run=None: True)
    handle = helper.make_handler(state, owner_uid=501, process_lookup=_fake_lookup(501))

    response = await handle({"method": "set_sleep_blocked", "params": {"blocked": True}}, 123)

    assert response == {"ok": True, "sleep_blocked": True}
    assert state.sleep_blocked is True


@pytest.mark.asyncio
async def test_handler_set_sleep_blocked_does_not_update_state_on_pmset_failure(monkeypatch):
    state = helper.HelperState()
    monkeypatch.setattr(helper, "run_pmset_disablesleep", lambda blocked, run=None: False)
    handle = helper.make_handler(state, owner_uid=501, process_lookup=_fake_lookup(501))

    response = await handle({"method": "set_sleep_blocked", "params": {"blocked": True}}, 123)

    assert response == {"ok": False, "sleep_blocked": False}
    assert state.sleep_blocked is False


@pytest.mark.asyncio
async def test_handler_get_state_reports_version_and_sleep_blocked():
    state = helper.HelperState()
    state.sleep_blocked = True
    handle = helper.make_handler(state, owner_uid=501, process_lookup=_fake_lookup(501))

    response = await handle({"method": "get_state"}, 123)

    assert response == {"ok": True, "sleep_blocked": True, "version": helper.shared.VERSION}


@pytest.mark.asyncio
async def test_handler_get_thermal_returns_temperature(monkeypatch):
    state = helper.HelperState()
    monkeypatch.setattr(helper.thermal_monitor, "read_cpu_temperature", lambda: 62.5)
    handle = helper.make_handler(state, owner_uid=501, process_lookup=_fake_lookup(501))

    response = await handle({"method": "get_thermal"}, 123)

    assert response == {"ok": True, "temperature": 62.5}


@pytest.mark.asyncio
async def test_handler_get_thermal_reports_failure_gracefully(monkeypatch):
    state = helper.HelperState()

    def boom():
        raise LookupError("no smc data")

    monkeypatch.setattr(helper.thermal_monitor, "read_cpu_temperature", boom)
    handle = helper.make_handler(state, owner_uid=501, process_lookup=_fake_lookup(501))

    response = await handle({"method": "get_thermal"}, 123)

    assert response["ok"] is False
    assert "no smc data" in response["error"]


@pytest.mark.asyncio
async def test_handler_ping_does_not_require_authorization():
    state = helper.HelperState()
    handle = helper.make_handler(state, owner_uid=None, process_lookup=_fake_lookup(999))

    response = await handle({"method": "ping"}, 123)

    assert response == {"ok": True, "version": helper.shared.VERSION}


@pytest.mark.asyncio
async def test_handler_rejects_unknown_method():
    state = helper.HelperState()
    handle = helper.make_handler(state, owner_uid=501, process_lookup=_fake_lookup(501))

    response = await handle({"method": "delete_everything"}, 123)

    assert response["ok"] is False
    assert "unknown method" in response["error"]
