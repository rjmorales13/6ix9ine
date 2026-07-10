from __future__ import annotations

import asyncio
import json
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

import psutil

import daemon_commands
import ipc
import lid_monitor
import shared
import thermal_monitor
from idle_tracker import IdleTracker
from lid_monitor import LidMonitor
from session_registry import SessionRegistry

MUTATING_COMMANDS = {"ACQUIRE", "RELEASE", "HOLD", "KILL_ALL"}
_GLASS_CHIME = Path("/System/Library/Sounds/Glass.aiff")


def play_chime() -> None:
    try:
        subprocess.run(["afplay", str(_GLASS_CHIME)], timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        pass  # a missed chime must never block sleep-block bookkeeping


def notify_summary(registry: SessionRegistry, thermal: "thermal_monitor.ThermalMonitor") -> None:
    agents = sorted({session.agent for session in registry.sessions().values()})
    message_parts = [f"agents: {', '.join(agents) or 'none'}"]
    if thermal.cutout_fired:
        message_parts.append(f"thermal cutout fired at {thermal.peak:.1f}°C")
    message = "; ".join(message_parts)
    script = f'display notification "{message}" with title "6ix9ine"'
    try:
        subprocess.run(["osascript", "-e", script], timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        pass


def default_cpu_percent(pid: int) -> float:
    try:
        return psutil.Process(pid).cpu_percent(interval=None)
    except psutil.NoSuchProcess:
        return 0.0


class Daemon:
    """Wires SessionRegistry + lid/thermal monitors to the CLI socket and the helper."""

    def __init__(
        self,
        registry: Optional[SessionRegistry] = None,
        lid: Optional[LidMonitor] = None,
        thermal: Optional[thermal_monitor.ThermalMonitor] = None,
        idle_tracker: Optional[IdleTracker] = None,
        helper_socket_path: Path = shared.HELPER_SOCKET_PATH,
        state_file: Optional[Path] = None,
        socket_path: Optional[Path] = None,
        transport: Callable = ipc.send_request_async,
        read_lid_state_fn: Callable = lid_monitor.read_lid_state,
        play_chime_fn: Callable = play_chime,
        notify_summary_fn: Callable = notify_summary,
        cpu_percent_fn: Callable = default_cpu_percent,
        pid_exists_fn: Callable = psutil.pid_exists,
        tick_interval: float = 5.0,
    ) -> None:
        self.registry = registry if registry is not None else SessionRegistry()
        self.lid = lid if lid is not None else LidMonitor()
        self.thermal = thermal if thermal is not None else thermal_monitor.ThermalMonitor(
            shared.thermal_threshold()
        )
        self.idle_tracker = idle_tracker if idle_tracker is not None else IdleTracker(
            idle_timeout_seconds=shared.idle_timeout_minutes() * 60
        )
        self.helper_socket_path = helper_socket_path
        self.state_file = state_file if state_file is not None else shared.state_file_path()
        self.socket_path = socket_path if socket_path is not None else shared.socket_path()
        self._transport = transport
        self._read_lid_state = read_lid_state_fn
        self._play_chime = play_chime_fn
        self._notify_summary = notify_summary_fn
        self._cpu_percent = cpu_percent_fn
        self._pid_exists = pid_exists_fn
        self.tick_interval = tick_interval
        self._now = time.time
        self._sleep_blocked = False

    async def _call_helper(self, method: str, **params: object) -> dict:
        try:
            return await self._transport(self.helper_socket_path, {"method": method, "params": params})
        except (OSError, TimeoutError) as exc:
            return {"ok": False, "error": str(exc)}

    async def _reconcile_sleep_block(self) -> None:
        desired = self.registry.is_active()
        if desired == self._sleep_blocked:
            return
        response = await self._call_helper("set_sleep_blocked", blocked=desired)
        if response.get("ok"):
            self._sleep_blocked = desired

    async def _reconcile_sleep_block_periodic(self) -> None:
        """Verify helper state matches desired state on every tick.

        Unlike _reconcile_sleep_block (called on state changes), this runs
        unconditionally every tick to catch helper restarts that reset
        pmset disablesleep to 0 without the daemon noticing.
        """
        desired = self.registry.is_active()
        state_resp = await self._call_helper("get_state")
        if not state_resp.get("ok"):
            return
        if state_resp.get("sleep_blocked") == desired:
            return
        response = await self._call_helper("set_sleep_blocked", blocked=desired)
        if response.get("ok"):
            self._sleep_blocked = desired

    def _persist_state(self) -> None:
        state = self.registry.to_state_dict(now=self._now())
        state["lid_state"] = self.lid.state
        state["last_thermal_reading"] = self.thermal.current
        state["thermal_cutout_fired"] = self.thermal.cutout_fired
        state["sleep_blocked"] = self._sleep_blocked
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state, indent=2))

    async def handle_request(self, request: dict, peer_pid: Optional[int]) -> dict:
        # peer_pid is part of the shared IPC Handler signature (helper.py's
        # handler uses it for caller authorization) but is deliberately not
        # forwarded into ACQUIRE -- see daemon_commands.handle_acquire.
        cmd = request.get("cmd")
        now = self._now()

        if cmd == "ACQUIRE":
            response = daemon_commands.handle_acquire(self.registry, request, now=now)
        elif cmd == "RELEASE":
            response = daemon_commands.handle_release(self.registry, request)
        elif cmd == "HOLD":
            response = daemon_commands.handle_hold(self.registry, request, now=now)
        elif cmd == "STATUS":
            response = daemon_commands.handle_status(
                self.registry, self.lid.state, self.thermal.to_state_dict(), self._sleep_blocked, now=now
            )
        elif cmd == "KILL_ALL":
            response = daemon_commands.handle_kill_all(self.registry)
        else:
            return {"ok": False, "error": f"unknown command: {cmd}"}

        if cmd in MUTATING_COMMANDS:
            await self._reconcile_sleep_block()
            self._persist_state()
        return response

    async def tick(self) -> None:
        """One periodic maintenance pass: process watch, idle release, holds, lid, thermal."""
        now = self._now()
        changed = False

        if self.registry.prune_dead(self._pid_exists):
            changed = True

        idle_pids = {
            session.pid: session.key
            for session in self.registry.sessions().values()
            if session.pid is not None
        }

        def is_idle(pid: int) -> bool:
            return self.idle_tracker.observe(pid, self._cpu_percent(pid), now)

        if self.registry.prune_idle(is_idle):
            changed = True
        for pid in list(idle_pids):
            if pid not in {s.pid for s in self.registry.sessions().values()}:
                self.idle_tracker.forget(pid)

        if self.registry.expire_holds(now=now):
            changed = True

        if changed:
            await self._reconcile_sleep_block()
            self._persist_state()

        await self._reconcile_sleep_block_periodic()
        await self._poll_lid()
        await self._poll_thermal()

    async def _poll_lid(self) -> None:
        try:
            state = self._read_lid_state()
        except Exception:
            return
        if not self.lid.observe(state):
            return
        if state == "closed" and self.registry.is_active():
            self._play_chime()
        elif state == "open":
            self._notify_summary(self.registry, self.thermal)

    async def _poll_thermal(self) -> None:
        response = await self._call_helper("get_thermal")
        temperature = response.get("temperature") if response.get("ok") else None
        if temperature is None:
            return
        crossed = self.thermal.observe(temperature)
        if crossed and self.lid.state == "closed":
            self.registry.release_all()
            await self._reconcile_sleep_block()
            self._persist_state()

    async def run_forever(self) -> None:
        server = ipc.LineJSONServer(self.socket_path, self.handle_request)
        await server.start()
        try:
            while True:
                await self.tick()
                await asyncio.sleep(self.tick_interval)
        finally:
            await server.stop()


if __name__ == "__main__":
    asyncio.run(Daemon().run_forever())
