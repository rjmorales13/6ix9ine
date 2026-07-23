from __future__ import annotations

from pathlib import Path

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


def test_install_does_not_hardcode_a_home_directory_path(monkeypatch, tmp_path):
    # Regression test: an earlier version hardcoded the CLI as an absolute
    # ~/.local/bin/6ix9ine path, which went stale the moment the user switched
    # install methods (e.g. to a Homebrew install) -- every opencode turn then
    # leaked "No such file or directory" to the terminal. The CLI must be
    # invoked as a bare command name so it re-resolves against PATH on every
    # call instead of being baked in once at install time.
    project_dir, _ = _point_at(monkeypatch, tmp_path)
    project_dir.mkdir(parents=True)

    opencode.install()

    content = (project_dir / "plugins" / "6ix9ine-hook.ts").read_text()
    assert str(Path.home()) not in content
    assert ".local/bin" not in content
    assert "const CLI = '6ix9ine'" in content


def test_install_uses_execfile_form_not_shell_interpolation(monkeypatch, tmp_path):
    # Regression test: the old template used execSync with a template-literal
    # shell command (`${CLI} acquire ${input.sessionID} ...`), which both
    # inherited stderr straight to the user's terminal on failure and
    # shell-interpolated the session ID unsanitized. execFileSync with array
    # args avoids both.
    project_dir, _ = _point_at(monkeypatch, tmp_path)
    project_dir.mkdir(parents=True)

    opencode.install()

    content = (project_dir / "plugins" / "6ix9ine-hook.ts").read_text()
    assert "execFileSync" in content
    assert "execSync(`" not in content
    assert 'stdio: "ignore"' in content


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


def test_install_passes_process_pid_to_acquire(monkeypatch, tmp_path):
    # Regression test for the never-cleaned-up-session sleep leak: if
    # OpenCode ever fails to emit "session.idle" cleanly (crash, force-quit,
    # connection drop), the daemon has no pid to fall back on and the
    # session blocks sleep forever. Passing the plugin host's own
    # process.pid lets the daemon guard-prune it via create_time on top of
    # the existing UUID-based release path.
    project_dir, _ = _point_at(monkeypatch, tmp_path)
    project_dir.mkdir(parents=True)

    opencode.install()

    content = (project_dir / "plugins" / "6ix9ine-hook.ts").read_text()
    assert "--pid" in content
    assert "process.pid.toString()" in content
    # The --pid flag must be wired into the chat.message (acquire) call, not
    # the release call.
    acquire_call = content.split('"chat.message"')[1].split("event:")[0]
    assert "--pid" in acquire_call
    release_call = content.split("event:")[1]
    assert "--pid" not in release_call


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
