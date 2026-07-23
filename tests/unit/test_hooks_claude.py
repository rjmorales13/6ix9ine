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
    assert stop_hook["type"] == "command"
    # New shape: command is the resolved 6ix9ine binary, sole arg is a
    # subcommand dispatched through cli.py's own argparse (works frozen too).
    assert prompt_hook["args"] == ["hook-acquire"]
    assert stop_hook["args"] == ["hook-release"]
    assert prompt_hook["command"].endswith("6ix9ine")
    assert stop_hook["command"].endswith("6ix9ine")
    # UserPromptSubmit/Stop don't support matchers -- must not be set.
    assert "matcher" not in written["hooks"]["UserPromptSubmit"][0]
    assert "matcher" not in written["hooks"]["Stop"][0]


def test_install_never_uses_dash_c_interpreter_mechanism(monkeypatch, tmp_path):
    """Regression: NO installed hook may use `<interpreter> -c "<code>"`. In the
    frozen binary that hits argparse and exits 2, which Claude Code treats as a
    hard block -- the original lockout bug."""
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()

    claude.install()

    written = json.loads(settings_file.read_text())
    for groups in written.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                assert hook.get("args", [])[:1] != ["-c"]


def test_install_resolves_cli_path_via_which(monkeypatch, tmp_path):
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()
    monkeypatch.setattr(claude.shutil, "which", lambda name: "/opt/homebrew/bin/6ix9ine")

    claude.install()

    written = json.loads(settings_file.read_text())
    prompt_hook = written["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    assert prompt_hook["command"] == "/opt/homebrew/bin/6ix9ine"


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


# -- Bash PreToolUse hook is intentionally NOT installed (descoped) --
#
# The old PID-tracking Bash hook never worked (a swallowed NameError left every
# command unmodified) and used the same exit-2-prone `<interpreter> -c` shape as
# the prompt hooks. Installing it in the frozen binary would block every Bash
# tool call. It is not installed; install()/uninstall() only strip stale copies.


def test_install_does_not_add_bash_pretooluse_hook(monkeypatch, tmp_path):
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()

    claude.install()

    written = json.loads(settings_file.read_text())
    assert "PreToolUse" not in written["hooks"]


def test_install_does_not_add_bash_track_permission(monkeypatch, tmp_path):
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()

    claude.install()

    written = json.loads(settings_file.read_text())
    allow = written.get("permissions", {}).get("allow", [])
    assert "Bash(6ix9ine track:*)" not in allow


def test_verify_true_without_bash_hook(monkeypatch, tmp_path):
    """verify() only requires the acquire/release prompt hooks now."""
    config_dir, _ = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()

    claude.install()

    assert claude.verify() is True


def test_uninstall_preserves_unrelated_pretooluse_hooks(monkeypatch, tmp_path):
    """A foreign Bash PreToolUse hook is left untouched by install/uninstall."""
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
    bash_groups = [g for g in written["hooks"]["PreToolUse"] if g.get("matcher") == "Bash"]
    assert any(h.get("command") == "other" for g in bash_groups for h in g.get("hooks", []))


# -- Migration: old broken `<interpreter> -c "<code>"` shape (the lockout bug) --


def _old_acquire_hook(python="/usr/bin/python3", cli="/Users/x/.local/bin/6ix9ine"):
    code = (
        "import json, subprocess, sys\n"
        "data = json.load(sys.stdin)\n"
        f"subprocess.run([{cli!r}, 'acquire', data['session_id']])\n"
    )
    return {"hooks": [{"type": "command", "command": python, "args": ["-c", code]}]}


def _old_release_hook(python="/usr/bin/python3", cli="/Users/x/.local/bin/6ix9ine"):
    code = (
        "import json, subprocess, sys\n"
        "data = json.load(sys.stdin)\n"
        f"subprocess.run([{cli!r}, 'release', data['session_id']])\n"
    )
    return {"hooks": [{"type": "command", "command": python, "args": ["-c", code]}]}


def _old_bash_hook(python="/usr/bin/python3"):
    code = (
        "import json, subprocess, sys\n"
        "data = json.load(sys.stdin)\n"
        "pids = 'jobs -p'\n"
        "subprocess.run(['6ix9ine', 'track'])\n"
    )
    return {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": python, "args": ["-c", code]}],
    }


def _seed_old_broken_settings(settings_file):
    settings_file.write_text(
        json.dumps(
            {
                "hooks": {
                    "UserPromptSubmit": [_old_acquire_hook()],
                    "Stop": [_old_release_hook()],
                    "PreToolUse": [_old_bash_hook()],
                },
                "permissions": {"allow": ["Bash(6ix9ine track:*)"]},
            }
        )
    )


def test_uninstall_removes_old_broken_shape(monkeypatch, tmp_path):
    """uninstall() must strip the OLD `-c` entries, or an affected user (who was
    locked out) stays locked out even after a 'successful' uninstall."""
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()
    _seed_old_broken_settings(settings_file)

    claude.uninstall()

    written = json.loads(settings_file.read_text())
    assert "hooks" not in written
    assert "permissions" not in written


def test_install_self_heals_old_broken_shape(monkeypatch, tmp_path):
    """Re-running install() after upgrading auto-repairs an affected user: the
    old broken entries are replaced with exactly one current-shape group."""
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()
    _seed_old_broken_settings(settings_file)

    claude.install()

    written = json.loads(settings_file.read_text())
    # Exactly one group per event, none using the -c mechanism.
    assert len(written["hooks"]["UserPromptSubmit"]) == 1
    assert len(written["hooks"]["Stop"]) == 1
    assert written["hooks"]["UserPromptSubmit"][0]["hooks"][0]["args"] == ["hook-acquire"]
    assert written["hooks"]["Stop"][0]["hooks"][0]["args"] == ["hook-release"]
    # Stale Bash hook + permission gone.
    assert "PreToolUse" not in written["hooks"]
    assert "Bash(6ix9ine track:*)" not in written.get("permissions", {}).get("allow", [])
    for groups in written["hooks"].values():
        for group in groups:
            for hook in group.get("hooks", []):
                assert hook.get("args", [])[:1] != ["-c"]
    assert claude.verify() is True


def test_install_self_heal_preserves_foreign_entries(monkeypatch, tmp_path):
    """Self-heal must not clobber unrelated hooks or permissions."""
    config_dir, settings_file = _point_at(monkeypatch, tmp_path)
    config_dir.mkdir()
    settings_file.write_text(
        json.dumps(
            {
                "hooks": {
                    "UserPromptSubmit": [
                        _old_acquire_hook(),
                        {"hooks": [{"type": "command", "command": "foreign-tool"}]},
                    ],
                },
                "permissions": {"allow": ["Bash(6ix9ine track:*)", "Read(*)"]},
            }
        )
    )

    claude.install()

    written = json.loads(settings_file.read_text())
    commands = [
        h.get("command")
        for g in written["hooks"]["UserPromptSubmit"]
        for h in g.get("hooks", [])
    ]
    assert "foreign-tool" in commands
    # Our old -c acquire hook replaced by exactly one new-shape hook.
    assert commands.count("foreign-tool") == 1
    assert any(
        h.get("args") == ["hook-acquire"]
        for g in written["hooks"]["UserPromptSubmit"]
        for h in g.get("hooks", [])
    )
    assert written["permissions"]["allow"] == ["Read(*)"]
