from __future__ import annotations

import pytest

import shared


def test_version_string_includes_codename():
    assert shared.CODENAME == "Gummo"
    assert shared.version_string() == f"6ix9ine v{shared.VERSION} ({shared.CODENAME})"


def test_state_dir_defaults_to_application_support(monkeypatch):
    monkeypatch.delenv("SIXNINE_STATE_DIR", raising=False)
    expected = shared.Path.home() / "Library" / "Application Support" / "6ix9ine"
    assert shared.state_dir() == expected


def test_state_dir_respects_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("SIXNINE_STATE_DIR", str(tmp_path))
    assert shared.state_dir() == tmp_path


def test_socket_and_state_paths_live_under_state_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("SIXNINE_STATE_DIR", str(tmp_path))
    assert shared.socket_path() == tmp_path / "cli.sock"
    assert shared.state_file_path() == tmp_path / "state.json"
    assert shared.filter_file_path() == tmp_path / "filter.json"


def test_thermal_threshold_default_and_override(monkeypatch):
    monkeypatch.delenv("SIXNINE_THERMAL_THRESHOLD", raising=False)
    assert shared.thermal_threshold() == 85.0
    monkeypatch.setenv("SIXNINE_THERMAL_THRESHOLD", "72.5")
    assert shared.thermal_threshold() == 72.5


def test_idle_timeout_minutes_default_and_override(monkeypatch):
    monkeypatch.delenv("SIXNINE_IDLE_TIMEOUT", raising=False)
    assert shared.idle_timeout_minutes() == 5
    monkeypatch.setenv("SIXNINE_IDLE_TIMEOUT", "10")
    assert shared.idle_timeout_minutes() == 10


@pytest.mark.parametrize("value,expected", [("true", True), ("false", False), ("1", True), ("0", False)])
def test_sniffing_enabled_parses_bool_like_strings(monkeypatch, value, expected):
    monkeypatch.setenv("SIXNINE_SNIFFING", value)
    assert shared.sniffing_enabled() is expected


def test_sniffing_enabled_defaults_true(monkeypatch):
    monkeypatch.delenv("SIXNINE_SNIFFING", raising=False)
    assert shared.sniffing_enabled() is True


@pytest.mark.parametrize(
    "text,seconds",
    [
        ("30m", 30 * 60),
        ("2h", 2 * 3600),
        ("1h30m", 3600 + 30 * 60),
        ("45s", 45),
        ("1h2m3s", 3600 + 120 + 3),
        ("90", 90),
    ],
)
def test_parse_duration_accepts_documented_formats(text, seconds):
    assert shared.parse_duration(text) == seconds


@pytest.mark.parametrize("text", ["", "abc", "30x", "-5m", "h30m"])
def test_parse_duration_rejects_invalid_input(text):
    with pytest.raises(ValueError):
        shared.parse_duration(text)


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (0, "0s"),
        (5, "5s"),
        (65, "1m 5s"),
        (3600, "1h 0m 0s"),
        (3725, "1h 2m 5s"),
    ],
)
def test_format_duration(seconds, expected):
    assert shared.format_duration(seconds) == expected


def test_valid_agents_contains_documented_agents():
    assert shared.VALID_AGENTS == {"claude", "opencode", "codex", "antigravity", "manual"}


def test_exit_codes_match_api_doc():
    assert shared.EXIT_OK == 0
    assert shared.EXIT_GENERAL_ERROR == 1
    assert shared.EXIT_INVALID_ARGS == 2
    assert shared.EXIT_DAEMON_NOT_RUNNING == 3
    assert shared.EXIT_HELPER_NOT_RUNNING == 4
    assert shared.EXIT_PERMISSION_DENIED == 5
    assert shared.EXIT_AGENT_NOT_DETECTED == 6
    assert shared.EXIT_SESSION_NOT_FOUND == 7
