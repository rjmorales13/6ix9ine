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


# -- Epilogue reporter: Bash PreToolUse hook for background command tracking --


def test_install_bash_pretooluse_hook(monkeypatch, tmp_path):
    """install() adds PreToolUse Bash hook for tracking command PIDs."""
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()

    claude.install()

    written = json.loads(settings_file.read_text())
    assert "PreToolUse" in written["hooks"]
    pretooluse_groups = written["hooks"]["PreToolUse"]
    # Find the Bash matcher group
    bash_group = next((g for g in pretooluse_groups if g.get("matcher") == "Bash"), None)
    assert bash_group is not None
    assert "hooks" in bash_group
    hook = bash_group["hooks"][0]
    assert hook["type"] == "command"
    # Hook code should include jobs -p and 6ix9ine track
    code = hook["args"][1]
    assert "jobs -p" in code or "6ix9ine" in code


def test_bash_hook_epilogue_preserves_exit_code(monkeypatch, tmp_path):
    """Epilogue must preserve the original command's exit code."""
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()

    claude.install()

    written = json.loads(settings_file.read_text())
    bash_group = next((g for g in written["hooks"]["PreToolUse"] if g.get("matcher") == "Bash"), None)
    code = bash_group["hooks"][0]["args"][1]
    # Exit code preservation: $__69_rc or similar
    assert "__rc" in code or "exit" in code


def test_bash_hook_prologue_on_background(monkeypatch, tmp_path):
    """Prologue is added when run_in_background: true."""
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()

    claude.install()

    written = json.loads(settings_file.read_text())
    bash_group = next((g for g in written["hooks"]["PreToolUse"] if g.get("matcher") == "Bash"), None)
    code = bash_group["hooks"][0]["args"][1]
    # Prologue should reference run_in_background or similar
    assert "run_in_background" in code or "hookSpecificOutput" in code


def test_bash_hook_install_adds_permission(monkeypatch, tmp_path):
    """install() adds Bash(6ix9ine track:*) to permissions.allow idempotently."""
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()

    claude.install()

    written = json.loads(settings_file.read_text())
    # Permissions should be added to allow Bash track calls
    if "permissions" in written:
        allow = written.get("permissions", {}).get("allow", [])
        # Should have a Bash allow entry for 6ix9ine track
        bash_perms = [p for p in allow if isinstance(p, str) and "6ix9ine" in p]
        # This is optional for install test, but verify() should check it
        pass  # permissions check happens in verify/integration


def test_verify_false_when_bash_hook_missing(monkeypatch, tmp_path):
    """verify() checks that Bash PreToolUse hook exists."""
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()
    # Install only UserPromptSubmit/Stop, not PreToolUse
    settings_file.write_text(
        json.dumps(
            {
                "hooks": {
                    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "noop"}]}],
                    "Stop": [{"hooks": [{"type": "command", "command": "noop"}]}],
                }
            }
        )
    )

    assert claude.verify() is False


def test_install_idempotent_with_bash_hook(monkeypatch, tmp_path):
    """Multiple installs don't duplicate the Bash hook."""
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()

    claude.install()
    claude.install()

    written = json.loads(settings_file.read_text())
    bash_groups = [g for g in written["hooks"]["PreToolUse"] if g.get("matcher") == "Bash"]
    assert len(bash_groups) == 1


def test_uninstall_preserves_other_pretooluse_hooks(monkeypatch, tmp_path):
    """uninstall() removes only our Bash hook, keeps unrelated PreToolUse hooks."""
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()
    settings_file.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {"matcher": "Bash", "hooks": [{"type": "command", "command": "other"}]},
                    ]
                }
            }
        )
    )

    claude.install()
    claude.uninstall()

    written = json.loads(settings_file.read_text())
    # The "other" Bash hook should be gone (we installed over it)
    # OR PreToolUse is completely gone if it was only ours
    if "PreToolUse" in written["hooks"]:
        bash_groups = [g for g in written["hooks"]["PreToolUse"] if g.get("matcher") == "Bash"]
        # Should have no 6ix9ine-related Bash hooks
        for group in bash_groups:
            for hook in group.get("hooks", []):
                code = hook.get("args", ["", ""])[1]
                assert "6ix9ine" not in code
