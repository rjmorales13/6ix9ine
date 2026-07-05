from __future__ import annotations

import pytest

import lid_monitor
from lid_monitor import LidMonitor, parse_clamshell_state, read_lid_state

IOREG_CLOSED = """
+-o IOPMrootDomain  <class IOPMrootDomain, id 0x100000110>
    | {
    |   "AppleClamshellState" = Yes
    | }
"""

IOREG_OPEN = """
+-o IOPMrootDomain  <class IOPMrootDomain, id 0x100000110>
    | {
    |   "AppleClamshellState" = No
    | }
"""


def test_parse_clamshell_state_yes_means_closed():
    assert parse_clamshell_state(IOREG_CLOSED) == "closed"


def test_parse_clamshell_state_no_means_open():
    assert parse_clamshell_state(IOREG_OPEN) == "open"


def test_parse_clamshell_state_raises_when_key_missing():
    with pytest.raises(LookupError):
        parse_clamshell_state("no relevant keys here")


def test_read_lid_state_invokes_ioreg_and_parses_result():
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)

        class Result:
            stdout = IOREG_CLOSED

        return Result()

    assert read_lid_state(run=fake_run) == "closed"
    assert calls[0][0] == "ioreg"
    assert "AppleClamshellState" in calls[0]


def test_lid_monitor_starts_unknown_and_first_observation_is_not_a_change():
    monitor = LidMonitor()
    assert monitor.state == "unknown"
    assert monitor.observe("open") is False
    assert monitor.state == "open"


def test_lid_monitor_reports_change_on_transition():
    monitor = LidMonitor()
    monitor.observe("open")
    assert monitor.observe("closed") is True
    assert monitor.state == "closed"


def test_lid_monitor_reports_no_change_when_state_repeats():
    monitor = LidMonitor()
    monitor.observe("open")
    assert monitor.observe("open") is False
