from __future__ import annotations

import time
import uuid

# NOTE on scoping: assertions below check the *specific* session/hold key each
# test created, not the machine's global pmset/status state. 6ix9ine is
# deliberately refcounted/concurrent -- another legitimate session (including
# the very Claude Code conversation used to run this suite, if its own
# UserPromptSubmit hook is still holding a session open) can coexist. Asserting
# a global "sleep_disabled() is False" after releasing only this test's own
# key is a false failure waiting to happen, not a real bug.


def test_acquire_release_roundtrip(run_cli, sleep_disabled):
    session_key = f"human-sim-{uuid.uuid4().hex[:8]}"

    acquire = run_cli("acquire", session_key, "--tool", "claude", "--reason", "human sim: roundtrip")
    assert acquire["ok"] is True, acquire
    assert acquire["status"] == "ACTIVE"
    assert sleep_disabled() is True, "pmset should show SleepDisabled 1 while a session is held"

    release = run_cli("release", session_key)
    assert release["ok"] is True, release

    status_after = run_cli("status")
    assert session_key not in status_after["active_sessions"], (
        f"released session should no longer appear in active_sessions: {status_after}"
    )


def test_multi_session_refcounting_keeps_sleep_blocked_until_last_release(run_cli, sleep_disabled):
    # Regression test for bug #6 (6ix9ine-rap-sheet-docs/handoff-road-to-gummo.md): sessions used
    # to be auto-pruned within ~5 seconds regardless of real activity, because the daemon tracked
    # the wrong PID for liveness. This proves the fix on the real, running daemon: releasing one
    # of two held sessions must NOT drop the other one, and sleep must stay blocked while it does.
    key_a = f"human-sim-a-{uuid.uuid4().hex[:8]}"
    key_b = f"human-sim-b-{uuid.uuid4().hex[:8]}"

    run_cli("acquire", key_a, "--tool", "claude", "--reason", "human sim: refcount A")
    run_cli("acquire", key_b, "--tool", "claude", "--reason", "human sim: refcount B")
    assert sleep_disabled() is True

    release_a = run_cli("release", key_a)
    assert release_a["ok"] is True, release_a

    status_mid = run_cli("status")
    assert key_a not in status_mid["active_sessions"], "session A should be gone after its release"
    assert key_b in status_mid["active_sessions"], "session B should still be held (this is the bug #6 regression check)"
    assert sleep_disabled() is True, "sleep must stay blocked while session B is still held"

    release_b = run_cli("release", key_b)
    assert release_b["ok"] is True, release_b

    status_final = run_cli("status")
    assert key_b not in status_final["active_sessions"], "session B should be gone after its release"


def test_hold_duration_expires_automatically(run_cli, sleep_disabled):
    hold = run_cli("hold", "--for", "3s", "--reason", "human sim: hold expiry")
    assert hold["ok"] is True, hold
    hold_id = hold["hold_id"]
    assert sleep_disabled() is True

    time.sleep(8)  # daemon tick interval is 5s; give it at least one full tick past expiry

    status = run_cli("status")
    assert all(h["id"] != hold_id for h in status["holds"]), (
        f"hold {hold_id} should have auto-expired by now: {status['holds']}"
    )
