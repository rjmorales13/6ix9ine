from __future__ import annotations

import uuid
from typing import Optional

import shared
from session_registry import SessionRegistry


def handle_acquire(registry: SessionRegistry, request: dict, now: Optional[float] = None) -> dict:
    # Deliberately does not track a PID for liveness: the only PID visible here
    # is the one-shot `6ix9ine acquire` CLI call's own process (via the IPC
    # socket's peer credential), which exits immediately after this request
    # completes -- it is never the actual agent process. Tracking it caused
    # every session to be auto-pruned within one daemon tick (~5s) regardless
    # of how long the real work continued. Sessions are identified and
    # reference-counted purely by their UUID `session_key`; only an explicit
    # `release` (or `KILL_ALL`) ends one.
    key = request.get("session")
    agent = request.get("tool")
    reason = request.get("reason", "")
    if not key or not agent:
        return {"ok": False, "error": "session and tool are required"}
    try:
        registry.acquire(key, agent=agent, reason=reason, now=now)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "status": "ACTIVE" if registry.is_active() else "IDLE", "count": registry.count()}


def handle_release(registry: SessionRegistry, request: dict) -> dict:
    key = request.get("session")
    if not key:
        return {"ok": False, "error": "session is required"}
    if not registry.release(key):
        return {"ok": False, "error": "session not found", "exit_code": shared.EXIT_SESSION_NOT_FOUND}
    return {"ok": True, "status": "ACTIVE" if registry.is_active() else "IDLE", "count": registry.count()}


def handle_hold(registry: SessionRegistry, request: dict, now: Optional[float] = None) -> dict:
    duration_text = request.get("for")
    if not duration_text:
        return {"ok": False, "error": "'for' duration is required"}
    try:
        duration_seconds = shared.parse_duration(duration_text)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    hold_id = request.get("hold_id") or f"hold-{uuid.uuid4().hex[:8]}"
    reason = request.get("reason", "")
    hold = registry.add_hold(hold_id, reason=reason, duration_seconds=duration_seconds, now=now)
    return {"ok": True, "hold_id": hold.id, "expires_at": hold.expires_at}


def handle_status(
    registry: SessionRegistry,
    lid_state: str,
    thermal_state: dict,
    sleep_blocked: bool,
    now: Optional[float] = None,
) -> dict:
    state = registry.to_state_dict(now=now)
    state["ok"] = True
    state["count"] = registry.count()
    state["lid"] = lid_state
    state["thermal"] = thermal_state
    state["sleep_blocked"] = sleep_blocked
    return state


def handle_kill_all(registry: SessionRegistry) -> dict:
    released = registry.release_all()
    return {"ok": True, "status": "IDLE", "released": released}
