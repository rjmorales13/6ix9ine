from __future__ import annotations

import uuid
from typing import Callable, Optional

import shared
from session_registry import CommandPid, SessionRegistry


def handle_acquire(
    registry: SessionRegistry,
    request: dict,
    create_time_fn: Optional[Callable[[int], Optional[float]]] = None,
    now: Optional[float] = None,
) -> dict:
    # Sessions are identified and reference-counted purely by their UUID
    # `session_key`; only an explicit `release` (or `KILL_ALL`) ends one --
    # that identity model is preserved regardless of the pid handling below.
    #
    # PID handling has two paths:
    #   - No `pid` in the request (the common case, e.g. Claude's
    #     hook-acquire): never track a PID for liveness. The only PID
    #     otherwise visible here is the one-shot `6ix9ine acquire` CLI call's
    #     own process (via the IPC socket's peer credential), which exits
    #     immediately after this request completes -- it is never the actual
    #     agent process. Tracking it caused every session to be auto-pruned
    #     within one daemon tick (~5s) regardless of how long the real work
    #     continued.
    #   - An explicit `pid` in the request (e.g. OpenCode's `chat.message`
    #     handler passing its own long-lived host process's pid): resolve its
    #     create_time SERVER-SIDE via create_time_fn, never trust a
    #     client-sent create_time. This anchors the pid against OS PID reuse
    #     the same way CommandPid/prune_command_pids already do (see
    #     Session.create_time's docstring in session_registry.py). If the
    #     create_time can't be resolved (pid already gone / a race), fall
    #     back to storing NO pid at all rather than a pid with no
    #     create_time -- the latter would silently reuse prune_dead's legacy,
    #     unguarded branch (meant for Claude's sniffed sessions) and
    #     reintroduce the exact PID-reuse hole this guard exists to close.
    #
    # Note `peer_pid` (the IPC caller's own credential, available to
    # daemon.py's handle_request) is never adopted here -- the pid field
    # below comes only from the request body's explicit `pid`, which the CLI
    # populates from `--pid` (see cli.py's cmd_acquire / hooks/opencode.py's
    # PLUGIN_TEMPLATE), never from the IPC peer credential.
    key = request.get("session")
    agent = request.get("tool")
    reason = request.get("reason", "")
    if not key or not agent:
        return {"ok": False, "error": "session and tool are required"}

    pid = request.get("pid")
    create_time: Optional[float] = None
    if pid is not None:
        resolve_create_time = create_time_fn if create_time_fn is not None else (lambda _pid: None)
        create_time = resolve_create_time(pid)
        if create_time is None:
            pid = None

    try:
        registry.acquire(key, agent=agent, reason=reason, pid=pid, create_time=create_time, now=now)
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


def handle_track(
    registry: SessionRegistry,
    request: dict,
    create_time_fn: Optional[Callable[[int], Optional[float]]] = None,
    now: Optional[float] = None,
) -> dict:
    """Register background-command PIDs self-reported by the epilogue reporter.

    This is the receiving side of the daemon.tick() -> epilogue reporter IPC:
    the epilogue hook wraps every Bash command, captures $!, resolves its
    create_time (to guard against OS PID reuse), and submits a TRACK request.

    Unlike handle_acquire(), TRACK deliberately does NOT track a session-level
    PID: the only PID visible in a TRACK request is from the epilogue reporter
    subprocess, which exits immediately after submitting. The session-level PID
    (if any) comes from sniffing agent session files or explicit acquire().
    TRACK only enriches command_pids, which are pruned independently by
    prune_command_pids(is_alive) based on their own create_time guards.
    """
    if create_time_fn is None:
        create_time_fn = lambda pid: None

    session = request.get("session")
    pids = request.get("pids")

    if not session:
        return {"ok": False, "error": "session is required"}
    if pids is None or not isinstance(pids, list):
        return {"ok": False, "error": "pids is required (list of integers)"}

    # Resolve create_time for each PID; skip any that are dead or inaccessible.
    command_pids: list[CommandPid] = []
    for pid in pids:
        create_time = create_time_fn(pid)
        if create_time is not None:
            command_pids.append(CommandPid(pid=pid, create_time=create_time))

    if command_pids:
        registry.track_pids(session, command_pids, agent="manual", now=now)

    return {"ok": True, "status": "ACTIVE" if registry.is_active() else "IDLE", "count": registry.count()}
