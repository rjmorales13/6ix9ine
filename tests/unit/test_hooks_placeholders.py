from __future__ import annotations

import pytest

from hooks import antigravity, codex


@pytest.mark.parametrize("module,config_attr,default_name", [(codex, "CONFIG_DIR", ".codex"), (antigravity, "CONFIG_DIR", ".antigravity")])
def test_detect_reflects_placeholder_config_dir(monkeypatch, tmp_path, module, config_attr, default_name):
    config_dir = tmp_path / default_name
    monkeypatch.setattr(module, config_attr, config_dir)
    assert module.detect() is False
    config_dir.mkdir()
    assert module.detect() is True


@pytest.mark.parametrize("module", [codex, antigravity])
def test_install_reports_pending_research_not_a_silent_success(module):
    result = module.install()
    assert result["ok"] is False
    assert "HOOKS.md" in result["error"]


@pytest.mark.parametrize("module", [codex, antigravity])
def test_uninstall_reports_pending_research(module):
    result = module.uninstall()
    assert result["ok"] is False


@pytest.mark.parametrize("module", [codex, antigravity])
def test_verify_is_always_false(module):
    assert module.verify() is False
