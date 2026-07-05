from __future__ import annotations

from hooks import opencode


def _point_at(monkeypatch, tmp_path):
    project_dir = tmp_path / "project" / ".opencode"
    home_dir = tmp_path / "home" / ".config" / "opencode"
    monkeypatch.setattr(opencode, "PROJECT_CONFIG_DIR", project_dir)
    monkeypatch.setattr(opencode, "HOME_CONFIG_DIR", home_dir)
    return project_dir, home_dir


def test_detect_false_when_no_config_dir_exists(monkeypatch, tmp_path):
    _point_at(monkeypatch, tmp_path)
    assert opencode.detect() is False


def test_detect_true_for_project_level_config(monkeypatch, tmp_path):
    project_dir, _ = _point_at(monkeypatch, tmp_path)
    project_dir.mkdir(parents=True)
    assert opencode.detect() is True


def test_detect_true_for_home_level_config(monkeypatch, tmp_path):
    _, home_dir = _point_at(monkeypatch, tmp_path)
    home_dir.mkdir(parents=True)
    assert opencode.detect() is True


def test_install_prefers_project_level_over_home_level(monkeypatch, tmp_path):
    project_dir, home_dir = _point_at(monkeypatch, tmp_path)
    project_dir.mkdir(parents=True)
    home_dir.mkdir(parents=True)

    result = opencode.install()

    assert result["ok"] is True
    # Real OpenCode plugin directories are "plugins" (plural), not "plugin".
    plugin_path = project_dir / "plugins" / "6ix9ine-hook.ts"
    assert plugin_path.exists()
    content = plugin_path.read_text()
    assert "acquire" in content
    assert "release" in content


def test_install_uses_real_hook_names_not_placeholders(monkeypatch, tmp_path):
    project_dir, _ = _point_at(monkeypatch, tmp_path)
    project_dir.mkdir(parents=True)

    opencode.install()

    content = (project_dir / "plugins" / "6ix9ine-hook.ts").read_text()
    # "beforeCommand"/"afterCommand" were the old, wrong, made-up hook names.
    assert "beforeCommand" not in content
    assert "afterCommand" not in content
    # Real hooks, verified against the installed @opencode-ai/plugin types.
    assert "chat.message" in content
    assert "session.idle" in content
    assert "input.sessionID" in content


def test_install_falls_back_to_home_level(monkeypatch, tmp_path):
    _, home_dir = _point_at(monkeypatch, tmp_path)
    home_dir.mkdir(parents=True)

    result = opencode.install()

    plugin_path = home_dir / "plugins" / "6ix9ine-hook.ts"
    assert plugin_path.exists()
    assert result["config_path"] == str(plugin_path)


def test_verify_true_after_install(monkeypatch, tmp_path):
    project_dir, _ = _point_at(monkeypatch, tmp_path)
    project_dir.mkdir(parents=True)
    opencode.install()
    assert opencode.verify() is True


def test_verify_false_before_install(monkeypatch, tmp_path):
    project_dir, _ = _point_at(monkeypatch, tmp_path)
    project_dir.mkdir(parents=True)
    assert opencode.verify() is False


def test_uninstall_removes_plugin_file(monkeypatch, tmp_path):
    project_dir, _ = _point_at(monkeypatch, tmp_path)
    project_dir.mkdir(parents=True)
    opencode.install()

    result = opencode.uninstall()

    assert result["ok"] is True
    assert not (project_dir / "plugins" / "6ix9ine-hook.ts").exists()


def test_uninstall_is_a_noop_when_nothing_installed(monkeypatch, tmp_path):
    project_dir, _ = _point_at(monkeypatch, tmp_path)
    project_dir.mkdir(parents=True)
    result = opencode.uninstall()
    assert result["ok"] is True
