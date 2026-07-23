from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Callable, Optional

import shared


@dataclass(frozen=True)
class CommandPid:
    """A background-command PID self-reported by the epilogue reporter.

    create_time anchors the PID against OS PID reuse: a prune check only
    treats the process as "the same one we tracked" if both the pid and its
    process-start time still match.
    """

    pid: int
    create_time: float


@dataclass(frozen=True)
class Session:
    key: str
    agent: str
    reason: str
    timestamp: float
    pid: Optional[int] = None
    # PID-reuse guard for `pid`, mirroring CommandPid's own pid/create_time
    # pair. Three states matter to prune_dead():
    #   pid is None                        -> not eligible for pid-based pruning at all
    #                                          (e.g. acquire()-based sessions, which
    #                                          deliberately never get a pid -- see
    #                                          daemon_commands.handle_acquire)
    #   pid is not None, create_time is None -> legacy/unguarded liveness check
    #                                          (Claude's process-sniffed sessions,
    #                                          set via _sniff_agents -- must NOT
    #                                          start being pruned differently)
    #   pid is not None, create_time is not None -> guarded liveness check: alive
    #                                          only if the pid exists AND its
    #                                          current create_time still matches
    #                                          (closes the OS PID-reuse hole for
    #                                          e.g. OpenCode's acquire --pid)
    create_time: Optional[float] = None
    # False once the owning agent turn has ended (RELEASE called); the session
    # is kept alive only by any live command_pids until they're pruned.
    turn_open: bool = True
    command_pids: frozenset[CommandPid] = frozenset()


@dataclass(frozen=True)
class Hold:
    id: str
    reason: str
    created_at: float
    expires_at: float


class SessionRegistry:
    """Reference-counted registry of sleep-blocking sessions and timed holds.

    Pure in-memory logic, deliberately free of sockets/subprocess/asyncio so
    it can be unit tested directly; daemon.py wires it to the outside world.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._holds: dict[str, Hold] = {}

    def acquire(
        self,
        key: str,
        agent: str,
        reason: str = "",
        pid: Optional[int] = None,
        create_time: Optional[float] = None,
        now: Optional[float] = None,
    ) -> Session:
        if agent not in shared.VALID_AGENTS:
            raise ValueError(f"unknown agent: {agent!r}")
        session = Session(
            key=key,
            agent=agent,
            reason=reason,
            timestamp=now if now is not None else time.time(),
            pid=pid,
            create_time=create_time,
        )
        existing = self._sessions.get(key)
        if existing is not None:
            # Merge, don't overwrite: a re-acquire of a live key must carry
            # forward any command PIDs the epilogue reporter already tracked
            # for it, or they'd leak out of the registry silently.
            session = replace(session, command_pids=existing.command_pids)
        self._sessions[key] = session
        return session

    def track_pids(
        self,
        key: str,
        pids: list[CommandPid],
        agent: str = "manual",
        now: Optional[float] = None,
    ) -> Session:
        """Record background-command PIDs self-reported by the epilogue reporter.

        If the session key is unknown (e.g. TRACK racing ahead of ACQUIRE, or
        arriving after RELEASE already popped an empty session), create a
        stub session with turn_open=False so it's kept alive purely by the
        tracked command PIDs and cleaned up once they die.
        """
        existing = self._sessions.get(key)
        if existing is not None:
            session = replace(existing, command_pids=existing.command_pids | frozenset(pids))
        else:
            session = Session(
                key=key,
                agent=agent,
                reason="",
                timestamp=now if now is not None else time.time(),
                pid=None,
                turn_open=False,
                command_pids=frozenset(pids),
            )
        self._sessions[key] = session
        return session

    def release(self, key: str) -> bool:
        session = self._sessions.get(key)
        if session is None:
            return False
        if session.command_pids:
            # Turn is over, but background commands are still running -- keep
            # the session so sleep stays blocked until prune_command_pids
            # observes them exit.
            self._sessions[key] = replace(session, turn_open=False)
        else:
            del self._sessions[key]
        return True

    def add_hold(
        self, hold_id: str, reason: str, duration_seconds: float, now: Optional[float] = None
    ) -> Hold:
        created_at = now if now is not None else time.time()
        hold = Hold(
            id=hold_id,
            reason=reason,
            created_at=created_at,
            expires_at=created_at + duration_seconds,
        )
        self._holds[hold_id] = hold
        return hold

    def expire_holds(self, now: Optional[float] = None) -> list[Hold]:
        now = now if now is not None else time.time()
        expired = [hold for hold in self._holds.values() if hold.expires_at <= now]
        for hold in expired:
            del self._holds[hold.id]
        return expired

    def release_all(self) -> int:
        released = self.count()
        self._sessions.clear()
        self._holds.clear()
        return released

    def prune_dead(
        self,
        is_alive: Callable[[int], bool],
        create_time_fn: Optional[Callable[[int], Optional[float]]] = None,
    ) -> list[str]:
        """Remove sessions whose tracked pid is no longer alive.

        See the Session.create_time docstring for the three branches this
        implements. The guarded branch (pid + create_time both set) mirrors
        daemon.py's is_command_pid_alive tolerance check exactly -- a pid is
        only "the same process we tracked" if it exists AND its current
        create_time matches ours within 1.0s, so an OS PID-recycle can't
        resurrect a dead session under someone else's process.
        """

        def is_dead(session: Session) -> bool:
            if session.pid is None:
                return False
            if not is_alive(session.pid):
                return True
            if session.create_time is None:
                # Legacy/unguarded path (e.g. Claude's sniffed sessions):
                # pid liveness alone is sufficient, unchanged from before.
                return False
            current_create_time = create_time_fn(session.pid) if create_time_fn else None
            if current_create_time is None:
                return True
            return abs(current_create_time - session.create_time) > 1.0

        return self._prune(is_dead)

    def prune_idle(self, is_idle: Callable[[int], bool]) -> list[str]:
        # Guarded acquire sessions (pid + create_time -- e.g. OpenCode's
        # long-lived plugin host, tracked via `acquire --pid`) are exempt from
        # CPU-idle detection entirely: they're often near-0% CPU while
        # genuinely waiting on the model mid-turn, and have their own explicit
        # release signal ("session.idle" from the plugin). Only pid-only
        # sessions without a create_time (Claude's sniffed sessions, which have
        # no independent release signal) are eligible for idle detection. The
        # `and` short-circuits before is_idle() is ever called for a guarded
        # session, so it also never touches the CPU-percent sampler for one.
        return self._prune(
            lambda session: session.pid is not None
            and session.create_time is None
            and is_idle(session.pid)
        )

    def prune_max_age(self, max_age_seconds: float, now: Optional[float] = None) -> list[str]:
        """Hard backstop: force-remove any session older than max_age_seconds,
        regardless of pid/create_time/command_pid state.

        Defense-in-depth for a truly abandoned session that somehow evades
        every other prune path (e.g. a crashed agent process whose pid was
        recycled by the OS before the next tick). acquire() refreshes
        `timestamp` on every re-acquire, so an actively-used session (repeated
        chat.message-style acquires) never ages out -- only one that never
        got a matching release does.
        """
        now = now if now is not None else time.time()
        keys = [key for key, session in self._sessions.items() if now - session.timestamp > max_age_seconds]
        for key in keys:
            del self._sessions[key]
        return keys

    def _prune(self, should_remove: Callable[[Session], bool]) -> list[str]:
        keys = [key for key, session in self._sessions.items() if should_remove(session)]
        for key in keys:
            del self._sessions[key]
        return keys

    def prune_command_pids(self, is_alive: Callable[[CommandPid], bool]) -> list[str]:
        """Drop dead command PIDs everywhere, then remove sessions they were
        the only thing keeping alive.

        A session is removed once turn_open is False (its agent turn ended),
        it has no remaining live command_pids, and it has no session-level
        pid (the peer-cred pid from acquire() -- daemon_commands.handle_track
        deliberately never stores one, so this branch only fires for
        acquire()-based sessions once prune_dead has already cleared theirs).
        """
        removed: list[str] = []
        for key, session in list(self._sessions.items()):
            live_pids = frozenset(cp for cp in session.command_pids if is_alive(cp))
            if live_pids != session.command_pids:
                session = replace(session, command_pids=live_pids)
                self._sessions[key] = session
            if not session.turn_open and not session.command_pids and session.pid is None:
                del self._sessions[key]
                removed.append(key)
        return removed

    def count(self) -> int:
        return len(self._sessions) + len(self._holds)

    def is_active(self) -> bool:
        return self.count() > 0

    def sessions(self) -> dict[str, Session]:
        return dict(self._sessions)

    def holds(self) -> dict[str, Hold]:
        return dict(self._holds)

    def to_state_dict(self, now: Optional[float] = None) -> dict:
        now = now if now is not None else time.time()
        active_sessions = {
            key: {
                "agent": session.agent,
                "timestamp": session.timestamp,
                "pid": session.pid,
                "reason": session.reason,
                "held_for": shared.format_duration(now - session.timestamp),
                "command_pids": [
                    {"pid": cp.pid, "create_time": cp.create_time}
                    for cp in sorted(session.command_pids, key=lambda cp: cp.pid)
                ],
            }
            for key, session in self._sessions.items()
        }
        holds = [
            {
                "id": hold.id,
                "reason": hold.reason,
                "expires_in": shared.format_duration(max(0.0, hold.expires_at - now)),
            }
            for hold in self._holds.values()
        ]
        return {
            "version": 1,
            "status": "ACTIVE" if self.is_active() else "IDLE",
            "active_sessions": active_sessions,
            "holds": holds,
        }
