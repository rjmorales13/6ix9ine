from __future__ import annotations

import pytest

from thermal_monitor import ThermalMonitor, parse_cpu_temperature, read_cpu_temperature

POWERMETRICS_OUTPUT = """
**** SMC ****
CPU die temperature: 62.73 C
GPU die temperature: 55.10 C
"""


def test_parse_cpu_temperature_extracts_cpu_die_reading():
    assert parse_cpu_temperature(POWERMETRICS_OUTPUT) == 62.73


def test_parse_cpu_temperature_raises_when_missing():
    with pytest.raises(LookupError):
        parse_cpu_temperature("no thermal data here")


def test_read_cpu_temperature_invokes_powermetrics_and_parses_result():
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)

        class Result:
            stdout = POWERMETRICS_OUTPUT

        return Result()

    assert read_cpu_temperature(run=fake_run) == 62.73
    assert calls[0][0] == "powermetrics"
    assert "smc" in calls[0]


def test_thermal_monitor_tracks_current_and_peak():
    monitor = ThermalMonitor(threshold=85.0)
    monitor.observe(60.0)
    monitor.observe(70.0)
    monitor.observe(65.0)
    assert monitor.current == 65.0
    assert monitor.peak == 70.0


def test_thermal_monitor_fires_cutout_exactly_once_when_threshold_crossed():
    monitor = ThermalMonitor(threshold=85.0)
    assert monitor.observe(80.0) is False
    assert monitor.observe(90.0) is True
    assert monitor.cutout_fired is True
    assert monitor.observe(95.0) is False  # already fired, no repeat trigger


def test_thermal_monitor_reset_cutout_allows_retriggering():
    monitor = ThermalMonitor(threshold=85.0)
    monitor.observe(90.0)
    monitor.reset_cutout()
    assert monitor.cutout_fired is False
    assert monitor.observe(91.0) is True


def test_thermal_monitor_to_state_dict_matches_status_schema():
    monitor = ThermalMonitor(threshold=85.0)
    monitor.observe(62.5)
    state = monitor.to_state_dict()
    assert state == {
        "current_temp": 62.5,
        "peak_temp": 62.5,
        "cutout_threshold": 85.0,
        "cutout_fired": False,
    }
