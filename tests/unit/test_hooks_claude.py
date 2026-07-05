from __future__ import annotations

import json

from hooks import claude


def _point_at(monkeypatch, tmp_path):
    config_dir = tmp_path / ".claude"
    settings_file = config_dir / "settings.json"
    monkeypatch.setattr(claude, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(claude, "SETTINGS_FILE", settings_file)
    return config_dir, settings_file


def test_detect_false_when_config_dir_missing(monkeypatch, tmp_path):
    _point_at(monkeypatch, tmp_path)
    assert claude.detect() is False


def test_detect_true_when_config_dir_exists(monkeypatch, tmp_path):
    config_dir, _ = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()
    assert claude.detect() is True


def test_install_writes_real_hook_schema(monkeypatch, tmp_path):
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()

    result = claude.install()

    assert result["ok"] is True
    written = json.loads(settings_file.read_text())
    prompt_hook = written["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    stop_hook = written["hooks"]["Stop"][0]["hooks"][0]
    assert prompt_hook["type"] == "command"
    assert prompt_hook["args"][0] == "-c"
    assert "acquire" in prompt_hook["args"][1]
    assert stop_hook["type"] == "command"
    assert "release" in stop_hook["args"][1]
    # UserPromptSubmit/Stop don't support matchers -- must not be set.
    assert "matcher" not in written["hooks"]["UserPromptSubmit"][0]
    assert "matcher" not in written["hooks"]["Stop"][0]


def test_install_reads_session_id_from_stdin_json_not_placeholders(monkeypatch, tmp_path):
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()

    claude.install()

    written = json.loads(settings_file.read_text())
    code = written["hooks"]["UserPromptSubmit"][0]["hooks"][0]["args"][1]
    assert "{session_id}" not in code
    assert "json.load(sys.stdin)" in code
    assert "session_id" in code


def test_install_is_idempotent(monkeypatch, tmp_path):
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()

    claude.install()
    claude.install()

    written = json.loads(settings_file.read_text())
    assert len(written["hooks"]["UserPromptSubmit"]) == 1
    assert len(written["hooks"]["Stop"]) == 1


def test_install_backs_up_existing_settings(monkeypatch, tmp_path):
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()
    settings_file.write_text(json.dumps({"existing": "config"}))

    claude.install()

    backup = settings_file.with_suffix(settings_file.suffix + ".bak")
    assert json.loads(backup.read_text()) == {"existing": "config"}


def test_install_preserves_unrelated_existing_keys_and_hooks(monkeypatch, tmp_path):
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()
    settings_file.write_text(
        json.dumps(
            {
                "otherSetting": True,
                "hooks": {
                    "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "noop"}]}]
                },
            }
        )
    )

    claude.install()

    written = json.loads(settings_file.read_text())
    assert written["otherSetting"] is True
    assert written["hooks"]["PreToolUse"][0]["matcher"] == "Bash"
    assert "UserPromptSubmit" in written["hooks"]


def test_verify_true_after_install(monkeypatch, tmp_path):
    config_dir, _ = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()
    claude.install()
    assert claude.verify() is True


def test_verify_false_before_install(monkeypatch, tmp_path):
    _point_at(monkeypatch, tmp_path)
    assert claude.verify() is False


def test_uninstall_removes_only_our_entries(monkeypatch, tmp_path):
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()
    settings_file.write_text(
        json.dumps(
            {
                "otherSetting": True,
                "hooks": {
                    "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "noop"}]}]
                },
            }
        )
    )

    claude.install()
    result = claude.uninstall()

    assert result["ok"] is True
    written = json.loads(settings_file.read_text())
    assert written["otherSetting"] is True
    assert written["hooks"]["PreToolUse"][0]["matcher"] == "Bash"
    assert "UserPromptSubmit" not in written["hooks"]
    assert "Stop" not in written["hooks"]


def test_uninstall_drops_hooks_key_when_empty(monkeypatch, tmp_path):
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()

    claude.install()
    claude.uninstall()

    written = json.loads(settings_file.read_text())
    assert "hooks" not in written


def test_uninstall_noop_when_never_installed(monkeypatch, tmp_path):
    _point_at(monkeypatch, tmp_path)
    result = claude.uninstall()
    assert result["ok"] is True
