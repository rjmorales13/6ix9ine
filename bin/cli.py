from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional

import ipc
import shared

Deps = Optional[Callable]

# ANSI styling for user-facing CLI output (no external deps).
ANSI_RESET = "\033[0m"
ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_ORANGE = "\033[38;5;208m"
ANSI_DIM = "\033[2m"
ANSI_BOLD = "\033[1m"

# Thermal color-band boundaries live in shared (single source of truth, also
# used by the dashboard). The CLI renders them with ANSI colors; the dashboard
# uses hex.

def thermal_label(temp: float) -> tuple[str, str]:
    """Return (LABEL, ANSI_COLOR) for a CPU temperature in Celsius."""
    if temp >= shared.THERMAL_HOT_MAX:
        return "CRITICAL", ANSI_RED
    if temp >= shared.THERMAL_WARM_MAX:
        return "HOT", ANSI_ORANGE
    if temp >= shared.THERMAL_COOL_MAX:
        return "WARM", ANSI_YELLOW
    return "COOL", ANSI_GREEN


def _colored(text: str, color: str) -> str:
    return f"{color}{text}{ANSI_RESET}"


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

    thermal = subparsers.add_parser("thermal")
    thermal_sub = thermal.add_subparsers(dest="thermal_command")
    thermal_sub.add_parser("status")

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

    # Claude Code hook entrypoints. These read the hook payload as JSON on
    # stdin, ALWAYS exit 0, and print NOTHING (handled specially in main()).
    subparsers.add_parser("hook-acquire")
    subparsers.add_parser("hook-release")

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


# --- Claude Code hook entrypoints ---
#
# These are invoked by Claude Code as `6ix9ine hook-acquire` / `hook-release`
# with the hook payload delivered as JSON on stdin. They have two hard
# contracts that the normal CLI commands do NOT:
#   1. ALWAYS exit 0. UserPromptSubmit/Stop treat a non-zero exit as a blocking
#      error (erasing the prompt / refusing to let Claude stop). A failure of
#      6ix9ine itself must never break the user's actual Claude Code session.
#   2. Print NOTHING to stdout. Claude Code injects a UserPromptSubmit hook's
#      stdout into the prompt context, so any normal CLI JSON output would
#      corrupt every prompt. main() dispatches these BEFORE its print path.


def _hook_send_request(send_request: Deps) -> Callable:
    # Keep the prompt hot path snappy: bound the daemon round-trip at 3s.
    return send_request or (lambda path, payload: ipc.send_request(path, payload, timeout=3.0))


def cmd_hook_acquire(args, send_request: Deps = None) -> int:
    """UserPromptSubmit hook: acquire the session, then exit 0 silently."""
    try:
        data = json.load(sys.stdin)
        session_id = data.get("session_id") or ""
        reason = (data.get("prompt") or "")[:80]
        if session_id:
            ns = argparse.Namespace(session_key=session_id, tool="claude", reason=reason)
            cmd_acquire(ns, send_request=_hook_send_request(send_request))
    except Exception:
        pass
    return shared.EXIT_OK


def cmd_hook_release(args, send_request: Deps = None) -> int:
    """Stop hook: release the session, then exit 0 silently."""
    try:
        data = json.load(sys.stdin)
        session_id = data.get("session_id") or ""
        if session_id:
            ns = argparse.Namespace(session_key=session_id, all=False)
            cmd_release(ns, send_request=_hook_send_request(send_request))
    except Exception:
        pass
    return shared.EXIT_OK


def cmd_status(args, send_request: Deps = None) -> tuple[dict, int]:
    send_request = send_request or ipc.send_request
    try:
        response = send_request(shared.socket_path(), {"cmd": "STATUS"})
    except ConnectionError as exc:
        return {"ok": False, "error": f"daemon not running: {exc}"}, shared.EXIT_DAEMON_NOT_RUNNING
    return response, shared.EXIT_OK


def cmd_thermal_status(args, send_request: Deps = None) -> tuple[dict, int]:
    """Read the daemon's thermal state and render a color-coded summary."""
    send_request = send_request or ipc.send_request
    try:
        response = send_request(shared.socket_path(), {"cmd": "STATUS"})
    except ConnectionError as exc:
        return (
            {"ok": False, "error": f"daemon not running: {exc}"},
            shared.EXIT_DAEMON_NOT_RUNNING,
        )
    if not isinstance(response, dict) or not response.get("ok", True):
        return {"ok": False, "error": "unexpected daemon response"}, shared.EXIT_GENERAL_ERROR

    state = response.get("thermal", {}) or {}
    current = state.get("current_temp")
    peak = state.get("peak_temp")
    threshold = state.get("cutout_threshold", shared.thermal_threshold())
    cutout_fired = bool(state.get("cutout_fired", False))

    lines = []
    if current is None:
        lines.append(_colored("Thermal Status: UNKNOWN", ANSI_DIM))
        lines.append(_colored("  No temperature reading available", ANSI_DIM))
    else:
        label, color = thermal_label(float(current))
        lines.append(f"Thermal Status: {_colored(label, color)} ({_colored(f'{current:g}°C', color)})")
        lines.append(f"  Current: {_colored(f'{current:g}°C', color)}")
        if peak is not None:
            lines.append(f"  Peak: {peak:g}°C")
        lines.append(f"  Threshold: {threshold:g}°C (override via SIXNINE_THERMAL_THRESHOLD)")
        if cutout_fired:
            lines.append(_colored("  Cutout: TRIGGERED — all sessions released", ANSI_RED))
        else:
            lines.append(_colored("  Cutout: Not triggered", ANSI_GREEN))
            alert = shared.thermal_alert_threshold()
            if current is not None and float(current) >= alert:
                lines.append(_colored(f"  Alert: approaching cutout (warn at {alert:g}°C)", ANSI_YELLOW))

    print("\n".join(lines))
    return {"ok": True}, shared.EXIT_OK


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


def _daemon_launch_config() -> tuple[list[str], str]:
    """Compute the daemon's ProgramArguments + WorkingDirectory from where THIS
    binary is actually running right now. Recomputed on every start so a moved
    install (e.g. after `brew upgrade` relocates the versioned Cellar path) is
    reflected instead of trusting a plist written by a prior version."""
    if getattr(sys, "frozen", False):
        # Running as a compiled binary
        cli_dir = Path(sys.executable).parent
        daemon_bin = cli_dir / "com.rjmorales.6ix9ine.daemon"
        if not daemon_bin.exists():
            import shutil

            daemon_path_str = shutil.which("com.rjmorales.6ix9ine.daemon")
            if daemon_path_str:
                daemon_bin = Path(daemon_path_str)
            else:
                daemon_bin = Path("/usr/local/bin/com.rjmorales.6ix9ine.daemon")
        return [str(daemon_bin)], str(shared.state_dir())

    # Running as a Python script
    cli_dir = Path(__file__).resolve().parent
    daemon_py = cli_dir / "daemon.py"
    return [sys.executable, str(daemon_py)], str(cli_dir)


def _render_daemon_plist(program_arguments: list[str], working_dir: str) -> str:
    log_out = str(shared.state_dir() / "daemon.log")
    log_err = str(shared.state_dir() / "daemon.err.log")
    args_str = "\n".join(f"\t\t<string>{arg}</string>" for arg in program_arguments)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>{shared.DAEMON_BUNDLE_ID}</string>
	<key>ProgramArguments</key>
	<array>
{args_str}
	</array>
	<key>WorkingDirectory</key>
	<string>{working_dir}</string>
	<key>RunAtLoad</key>
	<true/>
	<key>KeepAlive</key>
	<true/>
	<key>ThrottleInterval</key>
	<integer>10</integer>
	<key>StandardOutPath</key>
	<string>{log_out}</string>
	<key>StandardErrorPath</key>
	<string>{log_err}</string>
</dict>
</plist>
"""


def _read_plist_text() -> Optional[str]:
    try:
        return shared.DAEMON_PLIST_PATH.read_text()
    except OSError:
        return None


def _daemon_reachable(send_request: Callable) -> bool:
    """True iff the daemon answers STATUS on its socket — the real, direct
    signal, as opposed to guessing from launchctl's exit code."""
    try:
        send_request(shared.socket_path(), {"cmd": "STATUS"})
        return True
    except ConnectionError:
        return False
    except Exception:
        # A malformed/partial response still proves the socket is up.
        return True


def _poll_daemon(
    send_request: Callable, sleep: Callable, want_reachable: bool, attempts: int, delay: float
) -> bool:
    """Poll until the daemon reaches the desired reachability, or give up.
    Returns True if the desired state was observed within the budget."""
    for _ in range(max(1, attempts)):
        if _daemon_reachable(send_request) == want_reachable:
            return True
        sleep(delay)
    return False


def cmd_daemon_start(run: Deps = None, send_request: Deps = None, sleep: Deps = None) -> tuple[dict, int]:
    run = run or subprocess.run
    send_request = send_request or ipc.send_request
    sleep = sleep or time.sleep

    program_arguments, working_dir = _daemon_launch_config()
    expected_plist = _render_daemon_plist(program_arguments, working_dir)
    current_plist = _read_plist_text()

    shared.state_dir().mkdir(parents=True, exist_ok=True)
    shared.DAEMON_PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Staleness fix: (re)generate the plist whenever what's on disk differs from
    # what THIS binary expects — not only when the file is entirely absent. A
    # plist written by a previous install hardcodes a version-specific Cellar
    # path that no longer exists after `brew upgrade`.
    stale = current_plist != expected_plist
    if stale:
        # Overwriting the file alone does NOT make launchd pick up the change:
        # if the label is still registered, a subsequent `load` exits 0 while
        # doing nothing (empirically confirmed). Unload the old registration
        # first (harmless no-op if it was never loaded), then write + load.
        if current_plist is not None:
            run(
                ["launchctl", "unload", str(shared.DAEMON_PLIST_PATH)],
                capture_output=True,
                text=True,
                check=False,
            )
        shared.DAEMON_PLIST_PATH.write_text(expected_plist)

    load_result = run(
        ["launchctl", "load", str(shared.DAEMON_PLIST_PATH)],
        capture_output=True,
        text=True,
        check=False,
    )

    # Success reporting fix: trust the daemon's actual socket, not launchctl's
    # exit code. `launchctl load` is known to exit 0 while the daemon never
    # comes up, so confirm reachability before claiming ok.
    reachable = _poll_daemon(
        send_request,
        sleep,
        want_reachable=True,
        attempts=shared.DAEMON_START_POLL_ATTEMPTS,
        delay=shared.DAEMON_START_POLL_DELAY,
    )

    if reachable:
        return {"ok": True, "regenerated_plist": stale}, shared.EXIT_OK

    launchctl_output = (load_result.stdout or load_result.stderr or "").strip()
    error = "daemon did not become reachable after launchctl load"
    if launchctl_output:
        error = f"{error}; launchctl said: {launchctl_output}"
    return (
        {"ok": False, "error": error, "regenerated_plist": stale},
        shared.EXIT_GENERAL_ERROR,
    )


def cmd_daemon_stop(run: Deps = None, send_request: Deps = None, sleep: Deps = None) -> tuple[dict, int]:
    run = run or subprocess.run
    send_request = send_request or ipc.send_request
    sleep = sleep or time.sleep

    result = run(
        ["launchctl", "unload", str(shared.DAEMON_PLIST_PATH)],
        capture_output=True,
        text=True,
        check=False,
    )

    # As with start, don't trust the unload exit code alone: confirm the daemon
    # is genuinely gone from its socket before reporting success.
    stopped = _poll_daemon(
        send_request,
        sleep,
        want_reachable=False,
        attempts=shared.DAEMON_STOP_POLL_ATTEMPTS,
        delay=shared.DAEMON_STOP_POLL_DELAY,
    )

    if stopped:
        return {"ok": True}, shared.EXIT_OK

    launchctl_output = (result.stdout or result.stderr or "").strip()
    error = "daemon still reachable after launchctl unload"
    if launchctl_output:
        error = f"{error}; launchctl said: {launchctl_output}"
    return {"ok": False, "error": error}, shared.EXIT_GENERAL_ERROR


def cmd_daemon_restart(run: Deps = None, send_request: Deps = None, sleep: Deps = None) -> tuple[dict, int]:
    run = run or subprocess.run
    cmd_daemon_stop(run=run, send_request=send_request, sleep=sleep)
    return cmd_daemon_start(run=run, send_request=send_request, sleep=sleep)


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
    owner_file = shared.HELPER_INSTALL_PATH.parent / f"{shared.HELPER_BUNDLE_ID}.owner"

    if getattr(sys, "frozen", False):
        cli_dir = Path(sys.executable).parent
        # In a Homebrew installation, sys.executable is <prefix>/bin/6ix9ine
        # the helper binary is in the same bin/ directory, and the plist is in the prefix/ directory.
        src_bin = cli_dir / "com.rjmorales.6ix9ine.helper"
        src_plist = cli_dir.parent / "com.rjmorales.6ix9ine.helper.plist"
        
        # Fallbacks for other compiled run layouts
        if not src_bin.exists():
            src_bin = cli_dir / "com.rjmorales.6ix9ine.helper"
        if not src_plist.exists():
            src_plist = cli_dir / "com.rjmorales.6ix9ine.helper.plist"
            if not src_plist.exists():
                src_plist = project_root / "plists" / f"{shared.HELPER_BUNDLE_ID}.plist"

        return "\n".join(
            [
                "set -e",
                f'mkdir -p "{shared.HELPER_INSTALL_PATH.parent}"',
                f'cp "{src_bin}" "{shared.HELPER_INSTALL_PATH}"',
                f'cp "{src_plist}" "{shared.HELPER_PLIST_PATH}"',
                f'chmod 755 "{shared.HELPER_INSTALL_PATH}"',
                f'echo "{owner_uid}" > "{owner_file}"',
                f'chown -R root:wheel "{shared.HELPER_INSTALL_PATH}" "{shared.HELPER_PLIST_PATH}" "{owner_file}"',
                f'chmod 644 "{shared.HELPER_PLIST_PATH}"',
                f'launchctl bootstrap system "{shared.HELPER_PLIST_PATH}" || launchctl load "{shared.HELPER_PLIST_PATH}"',
            ]
        )

    install_dir = f"{shared.HELPER_INSTALL_PATH}.d"
    src_files = ["helper.py", "shared.py", "ipc.py", "thermal_monitor.py"]
    copy_cmds = "\n".join(f'cp "{project_root / "bin" / name}" "{install_dir}/{name}"' for name in src_files)
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

    # Hook entrypoints bypass the normal print-JSON dispatch entirely: they must
    # emit NOTHING on stdout and ALWAYS return 0 (see cmd_hook_acquire).
    if args.command == "hook-acquire":
        return cmd_hook_acquire(args)
    if args.command == "hook-release":
        return cmd_hook_release(args)

    dispatch = {
        "acquire": cmd_acquire,
        "release": cmd_release,
        "hold": cmd_hold,
        "track": cmd_track,
        "status": cmd_status,
        "thermal": cmd_thermal_status,
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
