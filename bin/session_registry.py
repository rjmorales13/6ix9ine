from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional

import shared


@dataclass(frozen=True)
class Session:
    key: str
    agent: str
    reason: str
    timestamp: float
    pid: Optional[int] = None


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
        )
        self._sessions[key] = session
        return session

    def release(self, key: str) -> bool:
        return self._sessions.pop(key, None) is not None

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

    def prune_dead(self, is_alive: Callable[[int], bool]) -> list[str]:
        return self._prune(lambda session: session.pid is not None and not is_alive(session.pid))

    def prune_idle(self, is_idle: Callable[[int], bool]) -> list[str]:
        return self._prune(lambda session: session.pid is not None and is_idle(session.pid))

    def _prune(self, should_remove: Callable[[Session], bool]) -> list[str]:
        keys = [key for key, session in self._sessions.items() if should_remove(session)]
        for key in keys:
            del self._sessions[key]
        return keys

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
