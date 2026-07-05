from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional

import psutil

import shared
import thermal_monitor
from ipc import Handler, LineJSONServer

# Written by `6ix9ine setup-privileged-helper` with the UID of the
# installing (non-root) user. Only that UID may issue mutating commands.
OWNER_FILE = shared.HELPER_INSTALL_PATH.parent / f"{shared.HELPER_BUNDLE_ID}.owner"


def read_owner_uid(owner_file: Path = OWNER_FILE) -> Optional[int]:
    try:
        return int(owner_file.read_text().strip())
    except (OSError, ValueError):
        return None


def authorize(
    peer_pid: Optional[int],
    owner_uid: Optional[int],
    process_lookup: Callable = psutil.Process,
) -> tuple[bool, str]:
    """Gate mutating helper calls to the single registered owner UID.

    This is not code-signature verification (there is no pure-Python XPC
    binding to do that) -- it is a peer-PID lookup over the LOCAL_PEERPID
    socket option, cross-checked against the UID recorded at install time.
    """
    if peer_pid is None:
        return False, "could not determine caller pid"
    if owner_uid is None:
        return False, "helper has no registered owner; run setup-privileged-helper"
    try:
        proc = process_lookup(peer_pid)
        caller_uid = proc.uids().real
    except psutil.NoSuchProcess:
        return False, "caller process no longer exists"
    if caller_uid != owner_uid:
        return False, f"caller uid {caller_uid} does not match registered owner {owner_uid}"
    return True, "ok"


def log_line(message: str, log_path: Path = shared.HELPER_LOG_PATH) -> None:
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except OSError:
        pass  # logging must never be able to break sleep control


def run_pmset_disablesleep(blocked: bool, run: Callable = subprocess.run) -> bool:
    value = "1" if blocked else "0"
    result = run(["pmset", "disablesleep", value], capture_output=True, text=True, timeout=10, check=False)
    return result.returncode == 0


class HelperState:
    def __init__(self) -> None:
        self.sleep_blocked = False


def make_handler(
    state: HelperState,
    owner_uid: Optional[int],
    process_lookup: Callable = psutil.Process,
) -> Handler:
    async def handle(request: dict, peer_pid: Optional[int]) -> dict:
        method = request.get("method")

        if method == "ping":
            return {"ok": True, "version": shared.VERSION}

        authorized, reason = authorize(peer_pid, owner_uid, process_lookup)
        if not authorized:
            log_line(f"REJECTED method={method} pid={peer_pid} reason={reason}")
            return {"ok": False, "error": f"unauthorized: {reason}"}

        if method == "set_sleep_blocked":
            blocked = bool((request.get("params") or {}).get("blocked"))
            success = run_pmset_disablesleep(blocked)
            if success:
                state.sleep_blocked = blocked
            log_line(f"set_sleep_blocked({blocked}) success={success} pid={peer_pid}")
            return {"ok": success, "sleep_blocked": state.sleep_blocked}

        if method == "get_state":
            return {"ok": True, "sleep_blocked": state.sleep_blocked, "version": shared.VERSION}

        if method == "get_thermal":
            try:
                temperature = thermal_monitor.read_cpu_temperature()
                return {"ok": True, "temperature": temperature}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

        return {"ok": False, "error": f"unknown method: {method}"}

    return handle


async def main() -> None:
    if os.geteuid() != 0:
        print("6ix9ine-helper must run as root", file=sys.stderr)
        sys.exit(1)

    state = HelperState()
    owner_uid = read_owner_uid()

    # Safety net: always start from a known-unblocked state, so a crash
    # loop or an unclean shutdown can never leave disablesleep stuck at 1.
    run_pmset_disablesleep(False)
    log_line(f"helper starting version={shared.VERSION} owner_uid={owner_uid}")

    handler = make_handler(state, owner_uid)
    server = LineJSONServer(shared.HELPER_SOCKET_PATH, handler)
    await server.start()
    os.chmod(shared.HELPER_SOCKET_PATH, 0o666)

    try:
        await server.serve_forever()
    finally:
        run_pmset_disablesleep(False)
        log_line("helper stopping, reset sleep_blocked=False")
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
