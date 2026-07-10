from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

import ipc
import shared

Deps = Optional[Callable]


def default_agent_modules() -> dict:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from hooks import antigravity, claude, codex, opencode

    return {"claude": claude, "opencode": opencode, "codex": codex, "antigravity": antigravity}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="6ix9ine")
    parser.add_argument("--version", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    acquire = subparsers.add_parser("acquire")
    acquire.add_argument("session_key")
    acquire.add_argument("--tool", required=True, choices=sorted(shared.VALID_AGENTS))
    acquire.add_argument("--reason", default=None)

    release = subparsers.add_parser("release")
    release.add_argument("session_key", nargs="?", default=None)
    release.add_argument("--all", action="store_true")

    hold = subparsers.add_parser("hold")
    hold.add_argument("--for", dest="duration", required=True)
    hold.add_argument("--reason", required=True)

    track = subparsers.add_parser("track")
    track.add_argument("session_key")
    track.add_argument("--tool", required=True, choices=sorted(shared.VALID_AGENTS))
    track.add_argument("--pids", nargs="+", type=int, required=True)

    subparsers.add_parser("status")

    install_hooks = subparsers.add_parser("install-hooks")
    install_hooks.add_argument("--agent", default=None, choices=sorted(shared.VALID_AGENTS - {"manual"}))
    install_hooks.add_argument("--all", action="store_true")

    uninstall_hooks = subparsers.add_parser("uninstall-hooks")
    uninstall_hooks.add_argument("--agent", default=None, choices=sorted(shared.VALID_AGENTS - {"manual"}))
    uninstall_hooks.add_argument("--all", action="store_true")

    subparsers.add_parser("setup-privileged-helper")
    subparsers.add_parser("helper-status")
    subparsers.add_parser("uninstall-helper")

    subparsers.add_parser("daemon-start")
    subparsers.add_parser("daemon-stop")
    subparsers.add_parser("daemon-restart")
    subparsers.add_parser("daemon-status")

    return parser


# --- session management (talks to the user daemon over cli.sock) ---


def cmd_acquire(args, send_request: Deps = None) -> tuple[dict, int]:
    send_request = send_request or ipc.send_request
    payload = {"cmd": "ACQUIRE", "session": args.session_key, "tool": args.tool, "reason": args.reason or ""}
    try:
        response = send_request(shared.socket_path(), payload)
    except ConnectionError as exc:
        return {"ok": False, "error": f"daemon not running: {exc}"}, shared.EXIT_DAEMON_NOT_RUNNING
    return response, (shared.EXIT_OK if response.get("ok") else shared.EXIT_GENERAL_ERROR)


def cmd_release(args, send_request: Deps = None) -> tuple[dict, int]:
    send_request = send_request or ipc.send_request
    payload = {"cmd": "KILL_ALL"} if getattr(args, "all", False) else {"cmd": "RELEASE", "session": args.session_key}
    try:
        response = send_request(shared.socket_path(), payload)
    except ConnectionError as exc:
        return {"ok": False, "error": f"daemon not running: {exc}"}, shared.EXIT_DAEMON_NOT_RUNNING
    if response.get("ok"):
        return response, shared.EXIT_OK
    return response, response.get("exit_code", shared.EXIT_GENERAL_ERROR)


def cmd_hold(args, send_request: Deps = None) -> tuple[dict, int]:
    send_request = send_request or ipc.send_request
    payload = {"cmd": "HOLD", "for": args.duration, "reason": args.reason}
    try:
        response = send_request(shared.socket_path(), payload)
    except ConnectionError as exc:
        return {"ok": False, "error": f"daemon not running: {exc}"}, shared.EXIT_DAEMON_NOT_RUNNING
    return response, (shared.EXIT_OK if response.get("ok") else shared.EXIT_GENERAL_ERROR)


def cmd_track(args, send_request: Deps = None) -> tuple[dict, int]:
    send_request = send_request or ipc.send_request
    payload = {"cmd": "TRACK", "session": args.session_key, "tool": args.tool, "pids": args.pids}
    try:
        response = send_request(shared.socket_path(), payload)
    except ConnectionError as exc:
        return {"ok": False, "error": f"daemon not running: {exc}"}, shared.EXIT_DAEMON_NOT_RUNNING
    return response, (shared.EXIT_OK if response.get("ok") else shared.EXIT_GENERAL_ERROR)


def cmd_status(args, send_request: Deps = None) -> tuple[dict, int]:
    send_request = send_request or ipc.send_request
    try:
        response = send_request(shared.socket_path(), {"cmd": "STATUS"})
    except ConnectionError as exc:
        return {"ok": False, "error": f"daemon not running: {exc}"}, shared.EXIT_DAEMON_NOT_RUNNING
    return response, shared.EXIT_OK


# --- hook installers ---


def cmd_install_hooks(args, agent_modules: Optional[dict] = None) -> tuple[dict, int]:
    agent_modules = agent_modules if agent_modules is not None else default_agent_modules()
    agents = [args.agent] if args.agent else (list(agent_modules) if args.all else [])
    if not agents:
        return {"ok": False, "error": "specify --agent or --all"}, shared.EXIT_INVALID_ARGS

    installed, skipped, failed = [], [], {}
    for name in agents:
        module = agent_modules.get(name)
        if module is None or not module.detect():
            skipped.append(name)
            continue
        result = module.install()
        if result.get("ok"):
            installed.append(name)
        else:
            failed[name] = result.get("error", "install failed")

    if installed:
        exit_code = shared.EXIT_OK
    elif failed:
        exit_code = shared.EXIT_GENERAL_ERROR
    else:
        exit_code = shared.EXIT_AGENT_NOT_DETECTED
    return (
        {"ok": bool(installed), "installed": installed, "skipped": skipped, "failed": failed},
        exit_code,
    )


def cmd_uninstall_hooks(args, agent_modules: Optional[dict] = None) -> tuple[dict, int]:
    agent_modules = agent_modules if agent_modules is not None else default_agent_modules()
    agents = [args.agent] if args.agent else (list(agent_modules) if args.all else [])
    if not agents:
        return {"ok": False, "error": "specify --agent or --all"}, shared.EXIT_INVALID_ARGS

    uninstalled, failed = [], {}
    for name in agents:
        module = agent_modules.get(name)
        if module is None:
            continue
        result = module.uninstall()
        if result.get("ok"):
            uninstalled.append(name)
        else:
            failed[name] = result.get("error", "uninstall failed")

    return {"ok": not failed, "uninstalled": uninstalled, "failed": failed}, shared.EXIT_OK


# --- daemon lifecycle (LaunchAgent, runs as the current user) ---


def cmd_daemon_start(run: Deps = None) -> tuple[dict, int]:
    run = run or subprocess.run
    result = run(["launchctl", "load", str(shared.DAEMON_PLIST_PATH)], capture_output=True, text=True, check=False)
    ok = result.returncode == 0
    return {"ok": ok, "output": result.stdout or result.stderr}, (shared.EXIT_OK if ok else shared.EXIT_GENERAL_ERROR)


def cmd_daemon_stop(run: Deps = None) -> tuple[dict, int]:
    run = run or subprocess.run
    result = run(["launchctl", "unload", str(shared.DAEMON_PLIST_PATH)], capture_output=True, text=True, check=False)
    ok = result.returncode == 0
    return {"ok": ok, "output": result.stdout or result.stderr}, (shared.EXIT_OK if ok else shared.EXIT_GENERAL_ERROR)


def cmd_daemon_restart(run: Deps = None) -> tuple[dict, int]:
    run = run or subprocess.run
    cmd_daemon_stop(run=run)
    return cmd_daemon_start(run=run)


def cmd_daemon_status(send_request: Deps = None) -> tuple[dict, int]:
    send_request = send_request or ipc.send_request
    try:
        response = send_request(shared.socket_path(), {"cmd": "STATUS"})
    except ConnectionError:
        return {"ok": False, "running": False}, shared.EXIT_DAEMON_NOT_RUNNING
    return {"ok": True, "running": True, "status": response}, shared.EXIT_OK


# --- privileged helper lifecycle (the only root-touching commands) ---


def build_setup_helper_script(project_root: Optional[Path], owner_uid: int) -> str:
    project_root = project_root or Path(__file__).resolve().parent.parent
    install_dir = f"{shared.HELPER_INSTALL_PATH}.d"
    src_files = ["helper.py", "shared.py", "ipc.py", "thermal_monitor.py"]
    copy_cmds = "\n".join(f'cp "{project_root / "bin" / name}" "{install_dir}/{name}"' for name in src_files)
    owner_file = shared.HELPER_INSTALL_PATH.parent / f"{shared.HELPER_BUNDLE_ID}.owner"
    launcher_py = f"{install_dir}/_launcher.py"
    launcher_py_body = (
        f'import sys; sys.path.insert(0, "{install_dir}")\n'
        "import asyncio, helper\n"
        "asyncio.run(helper.main())\n"
    )
    # A shebang line cannot itself contain a space in the interpreter path (the
    # kernel splits on the first whitespace), which breaks when sys.executable
    # lives under e.g. "Application Support". /bin/sh has no such path, so it's
    # used as a fixed, space-free wrapper that execs the real interpreter with
    # its path passed as a normal (safely quoted) argv element instead.
    launcher_sh = f'#!/bin/sh\nexec "{sys.executable}" "{launcher_py}"\n'
    plist_src = project_root / "plists" / f"{shared.HELPER_BUNDLE_ID}.plist"
    return "\n".join(
        [
            "set -e",
            f'mkdir -p "{install_dir}"',
            copy_cmds,
            f"cat > \"{launcher_py}\" <<'HELPER_LAUNCHER_PY_EOF'",
            launcher_py_body + "HELPER_LAUNCHER_PY_EOF",
            f"cat > \"{shared.HELPER_INSTALL_PATH}\" <<'HELPER_LAUNCHER_SH_EOF'",
            launcher_sh + "HELPER_LAUNCHER_SH_EOF",
            f'chmod 755 "{shared.HELPER_INSTALL_PATH}"',
            f'echo "{owner_uid}" > "{owner_file}"',
            f'cp "{plist_src}" "{shared.HELPER_PLIST_PATH}"',
            f'chown -R root:wheel "{install_dir}" "{shared.HELPER_INSTALL_PATH}" "{shared.HELPER_PLIST_PATH}" "{owner_file}"',
            f'chmod 644 "{shared.HELPER_PLIST_PATH}"',
            f'launchctl load "{shared.HELPER_PLIST_PATH}"',
        ]
    )


def cmd_setup_privileged_helper(run: Deps = None, project_root: Optional[Path] = None) -> tuple[dict, int]:
    run = run or subprocess.run
    script = build_setup_helper_script(project_root, owner_uid=os.getuid())
    result = run(["sudo", "bash", "-c", script], text=True, check=False)
    ok = result.returncode == 0
    return {"ok": ok}, (shared.EXIT_OK if ok else shared.EXIT_PERMISSION_DENIED)


def cmd_uninstall_helper(run: Deps = None) -> tuple[dict, int]:
    run = run or subprocess.run
    install_dir = f"{shared.HELPER_INSTALL_PATH}.d"
    owner_file = shared.HELPER_INSTALL_PATH.parent / f"{shared.HELPER_BUNDLE_ID}.owner"
    script = "\n".join(
        [
            f'launchctl unload "{shared.HELPER_PLIST_PATH}" || true',
            f'rm -f "{shared.HELPER_PLIST_PATH}"',
            f'rm -f "{shared.HELPER_INSTALL_PATH}"',
            f'rm -f "{owner_file}"',
            f'rm -rf "{install_dir}"',
            "pmset disablesleep 0",
        ]
    )
    result = run(["sudo", "bash", "-c", script], text=True, check=False)
    ok = result.returncode == 0
    return {"ok": ok}, (shared.EXIT_OK if ok else shared.EXIT_PERMISSION_DENIED)


def cmd_helper_status(send_request: Deps = None) -> tuple[dict, int]:
    send_request = send_request or ipc.send_request
    try:
        response = send_request(shared.HELPER_SOCKET_PATH, {"method": "get_state"})
    except ConnectionError:
        return {"ok": False, "running": False}, shared.EXIT_HELPER_NOT_RUNNING
    return {"ok": True, "running": True, "state": response}, shared.EXIT_OK


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(shared.version_string())
        return shared.EXIT_OK

    dispatch = {
        "acquire": cmd_acquire,
        "release": cmd_release,
        "hold": cmd_hold,
        "track": cmd_track,
        "status": cmd_status,
        "install-hooks": cmd_install_hooks,
        "uninstall-hooks": cmd_uninstall_hooks,
        "setup-privileged-helper": lambda a: cmd_setup_privileged_helper(),
        "helper-status": lambda a: cmd_helper_status(),
        "uninstall-helper": lambda a: cmd_uninstall_helper(),
        "daemon-start": lambda a: cmd_daemon_start(),
        "daemon-stop": lambda a: cmd_daemon_stop(),
        "daemon-restart": lambda a: cmd_daemon_restart(),
        "daemon-status": lambda a: cmd_daemon_status(),
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return shared.EXIT_INVALID_ARGS

    response, exit_code = handler(args)
    print(json.dumps(response, indent=2, default=str))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
