from __future__ import annotations

import pytest

from thermal_monitor import (
    PRESSURE_TO_TEMP,
    ThermalMonitor,
    parse_cpu_temperature,
    read_cpu_temperature,
)

POWERMETRICS_OUTPUT = """
**** SMC ****
CPU die temperature: 62.73 C
GPU die temperature: 55.10 C
"""

APPLE_SILICON_OUTPUT = """
**** Thermal pressure ****
Current pressure level: Nominal
"""

APPLE_SILICON_HEAVY_OUTPUT = """
**** Thermal pressure ****
Current pressure level: Heavy
"""


class _Result:
    def __init__(self, stdout: str, returncode: int = 0) -> None:
        self.stdout = stdout
        self.returncode = returncode


def test_parse_cpu_temperature_extracts_cpu_die_reading():
    assert parse_cpu_temperature(POWERMETRICS_OUTPUT) == 62.73


def test_parse_cpu_temperature_raises_when_missing():
    with pytest.raises(LookupError):
        parse_cpu_temperature("no thermal data here")


def test_parse_apple_silicon_thermal_pressure_nominal():
    assert parse_cpu_temperature(APPLE_SILICON_OUTPUT) == 40.0


def test_parse_apple_silicon_thermal_pressure_heavy():
    assert parse_cpu_temperature(APPLE_SILICON_HEAVY_OUTPUT) == 85.0


def test_parse_apple_silicon_unknown_pressure_level_falls_back_safe():
    assert parse_cpu_temperature("Current pressure level: Unknown") == 40.0


def test_parse_prefers_cpu_die_over_pressure_when_both_present():
    both = POWERMETRICS_OUTPUT + "\nCurrent pressure level: Critical\n"
    assert parse_cpu_temperature(both) == 62.73


def test_pressure_to_temp_mapping_has_all_known_levels():
    for level in ("Nominal", "Moderate", "Heavy", "Critical"):
        assert level in PRESSURE_TO_TEMP


def test_read_cpu_temperature_tries_smc_first_returns_on_success():
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _Result(POWERMETRICS_OUTPUT)

    assert read_cpu_temperature(run=fake_run) == 62.73
    assert "smc" in calls[0]


def test_read_cpu_temperature_falls_back_to_thermal_when_smc_fails():
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if "smc" in cmd:
            return _Result("", returncode=1)
        return _Result(APPLE_SILICON_OUTPUT)

    assert read_cpu_temperature(run=fake_run) == 40.0
    assert "thermal" in calls[1]


def test_read_cpu_temperature_raises_when_both_samplers_fail():
    def fake_run(cmd, **kwargs):
        return _Result("", returncode=1)

    with pytest.raises(LookupError):
        read_cpu_temperature(run=fake_run)


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


def test_apple_silicon_heavy_pressure_triggers_cutout():
    """Integration: Heavy pressure maps to 85.0°C which equals the
    default 85.0 threshold, triggering the cutout."""
    monitor = ThermalMonitor(threshold=85.0)
    temp = parse_cpu_temperature(APPLE_SILICON_HEAVY_OUTPUT)
    assert temp == 85.0
    assert monitor.observe(temp) is True
