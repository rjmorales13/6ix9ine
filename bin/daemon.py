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
from session_registry import CommandPid, SessionRegistry

MUTATING_COMMANDS = {"ACQUIRE", "RELEASE", "HOLD", "TRACK", "KILL_ALL"}
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


def default_create_time(pid: int) -> Optional[float]:
    try:
        return psutil.Process(pid).create_time()
    except psutil.NoSuchProcess:
        return None


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
        create_time_fn: Callable = default_create_time,
        pid_exists_fn: Callable = psutil.pid_exists,
        agent_scan_dirs: Optional[dict[str, Path]] = None,
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
        self._create_time_fn = create_time_fn
        self._pid_exists = pid_exists_fn
        self._agent_scan_dirs = (
            agent_scan_dirs
            if agent_scan_dirs is not None
            else {"claude": Path.home() / ".claude" / "sessions"}
        )
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

    def _sniff_agents(self) -> bool:
        """Scan for running agent sessions via process + session-file detection.

        Falls back to process-sniffing when agent hooks are not configured or
        are being overridden (e.g., by cmux's --settings flag). Acquires any
        session whose agent PID is alive but not yet tracked in the registry.
        Returns True if any new sessions were acquired.
        """
        now = self._now()
        changed = False

        tracked_keys = set(self.registry.sessions().keys())

        for agent, session_dir in self._agent_scan_dirs.items():
            if not session_dir.is_dir():
                continue
            for session_file in session_dir.iterdir():
                if session_file.suffix != ".json":
                    continue
                try:
                    data = json.loads(session_file.read_text())
                except (json.JSONDecodeError, OSError):
                    continue

                session_id = data.get("sessionId") or data.get("session_id") or ""
                if not session_id:
                    continue
                if session_id in tracked_keys:
                    continue

                pid = data.get("pid")
                status = data.get("status", "")
                if pid is None or not self._pid_exists(pid):
                    continue
                if status != "busy":
                    continue

                self.registry.acquire(
                    session_id,
                    agent=agent,
                    reason=f"sniffed: {data.get('name', '')}",
                    pid=pid,
                    now=now,
                )
                changed = True
                tracked_keys.add(session_id)

        return changed

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
            response = daemon_commands.handle_acquire(
                self.registry, request, create_time_fn=self._create_time_fn, now=now
            )
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
        elif cmd == "TRACK":
            response = daemon_commands.handle_track(
                self.registry, request, create_time_fn=self._create_time_fn, now=now
            )
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

        if self._sniff_agents():
            changed = True

        if self.registry.prune_dead(self._pid_exists, create_time_fn=self._create_time_fn):
            changed = True

        # Only sessions without a create_time (Claude's process-sniffed
        # sessions, currently the only consumer of prune_idle) feed the
        # CPU-idle detector. Guarded acquire sessions (pid + create_time --
        # e.g. OpenCode's chat.message --pid) are exempt: they have their own
        # release signal (session.idle from the plugin) and are frequently
        # near-0% CPU while genuinely waiting on the model mid-turn, so
        # CPU-idle pruning them would put the Mac to sleep during active work.
        # SessionRegistry.prune_idle() enforces this same exemption itself;
        # this local dict just keeps the idle_tracker bookkeeping below
        # consistent with what's actually eligible.
        idle_pids = {
            session.pid: session.key
            for session in self.registry.sessions().values()
            if session.pid is not None and session.create_time is None
        }

        def is_idle(pid: int) -> bool:
            return self.idle_tracker.observe(pid, self._cpu_percent(pid), now)

        if self.registry.prune_idle(is_idle):
            changed = True
        for pid in list(idle_pids):
            if pid not in {s.pid for s in self.registry.sessions().values()}:
                self.idle_tracker.forget(pid)

        def is_command_pid_alive(cp: CommandPid) -> bool:
            # PID reuse guard: only treat a PID as alive if it exists AND its
            # create_time matches (within 1s tolerance). OS PID recycle won't fool us.
            if not self._pid_exists(cp.pid):
                return False
            current_create_time = self._create_time_fn(cp.pid)
            if current_create_time is None:
                return False
            # Allow 1s tolerance for minor timing skew
            return abs(current_create_time - cp.create_time) <= 1.0

        if self.registry.prune_command_pids(is_command_pid_alive):
            changed = True

        # Hard backstop, defense-in-depth: force-release any session older
        # than session_max_age_hours() regardless of pid/create_time state.
        # Every other prune path above depends on some liveness signal being
        # reachable (pid_exists, create_time, CPU sampling); this one doesn't,
        # so it still catches a session that somehow evades all of them.
        # acquire() refreshes `timestamp` on every re-acquire, so an
        # actively-used session (repeated chat.message-style acquires) never
        # approaches this threshold -- only a truly abandoned one does.
        if self.registry.prune_max_age(shared.session_max_age_hours() * 3600.0, now=now):
            changed = True

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
        if not crossed:
            return
        # The cutout threshold was crossed: release every session so the Mac
        # can sleep and cool down, regardless of lid position. (Previously
        # this only fired while the lid was closed, leaving sleep blocked on
        # a hot open-docked Mac.)
        # Notify BEFORE release_all(): the summary reads registry.sessions(),
        # which is empty afterwards, so reordering would always say "agents: none".
        if self.lid.state == "open":
            self._notify_summary(self.registry, self.thermal)
        self.registry.release_all()
        await self._reconcile_sleep_block()
        self._persist_state()

    async def run_forever(self) -> None:
        self._sniff_agents()
        self._persist_state()
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
