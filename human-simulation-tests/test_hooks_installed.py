from __future__ import annotations

import json
from pathlib import Path


def test_claude_settings_has_real_hook_schema():
    # Regression test for bug #5 (docs/planning/handoff-road-to-gummo.md): the old
    # implementation wrote to a standalone ~/.claude/hooks.json that Claude Code never reads.
    # Real hook config lives in the "hooks" key inside ~/.claude/settings.json.
    settings_file = Path.home() / ".claude" / "settings.json"
    assert settings_file.exists(), f"{settings_file} does not exist"

    settings = json.loads(settings_file.read_text())
    hooks = settings.get("hooks", {})

    assert "UserPromptSubmit" in hooks, "no UserPromptSubmit hook installed -- run `6ix9ine install-hooks --agent claude`"
    assert "Stop" in hooks, "no Stop hook installed -- run `6ix9ine install-hooks --agent claude`"

    prompt_hook = hooks["UserPromptSubmit"][0]["hooks"][0]
    stop_hook = hooks["Stop"][0]["hooks"][0]
    assert prompt_hook["type"] == "command"
    assert "acquire" in prompt_hook["args"][1]
    assert stop_hook["type"] == "command"
    assert "release" in stop_hook["args"][1]
    # UserPromptSubmit/Stop don't support matchers at all (silently ignored if present).
    assert "matcher" not in hooks["UserPromptSubmit"][0]
    assert "matcher" not in hooks["Stop"][0]


def test_opencode_plugin_installed():
    # Regression test for bug #7 (docs/planning/handoff-road-to-gummo.md): the old
    # implementation wrote to ~/.opencode/plugin/ (singular -- just where the opencode binary
    # itself lives, not a config/plugin-loading location) using made-up hook names
    # (beforeCommand/afterCommand) that don't exist in the real @opencode-ai/plugin API. Real
    # global plugins load from ~/.config/opencode/plugins/ (plural).
    plugin_path = Path.home() / ".config" / "opencode" / "plugins" / "6ix9ine-hook.ts"
    assert plugin_path.exists(), (
        f"{plugin_path} does not exist -- run `6ix9ine install-hooks --agent opencode`"
    )

    content = plugin_path.read_text()
    assert "beforeCommand" not in content, "old, wrong, made-up hook name -- bug #7 regressed"
    assert "afterCommand" not in content, "old, wrong, made-up hook name -- bug #7 regressed"
    assert "chat.message" in content, "real hook name for acquiring on a new message"
    assert "session.idle" in content, "real event type for releasing when the session goes idle"
