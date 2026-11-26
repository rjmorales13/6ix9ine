from __future__ import annotations

from hooks import antigravity


def test_detect_reflects_placeholder_config_dir(monkeypatch, tmp_path):
    config_dir = tmp_path / ".antigravity"
    monkeypatch.setattr(antigravity, "CONFIG_DIR", config_dir)
    assert antigravity.detect() is False
    config_dir.mkdir()
    assert antigravity.detect() is True


def test_install_reports_pending_research_not_a_silent_success():
    result = antigravity.install()
    assert result["ok"] is False
    assert "HOOKS.md" in result["error"]


def test_uninstall_reports_pending_research():
    assert antigravity.uninstall()["ok"] is False


def test_verify_is_always_false():
    assert antigravity.verify() is False
