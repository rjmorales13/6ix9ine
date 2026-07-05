from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Iterable, Optional

import psutil
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, Static

import ipc
import shared

AUXILIARY_PROCESS_NAMES = {"ollama", "dockerd", "com.docker.backend"}


def load_filter(path: Optional[Path] = None) -> set:
    path = path or shared.filter_file_path()
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return set()
    return set(data.get("ignored", []))


def save_filter(ignored: set, path: Optional[Path] = None) -> None:
    path = path or shared.filter_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"ignored": sorted(ignored)}, indent=2))


def build_session_rows(state: dict) -> list:
    return [
        (key, session.get("agent", ""), session.get("reason", ""), session.get("held_for", ""))
        for key, session in state.get("active_sessions", {}).items()
    ]


def build_auxiliary_rows(processes: Iterable[dict], ignored: set) -> list:
    rows = []
    for proc in processes:
        name = proc.get("name", "")
        if name in ignored:
            continue
        rows.append(
            (
                name,
                str(proc.get("pid", "")),
                proc.get("status", ""),
                f"{proc.get('cpu_percent', 0.0):.1f}%",
                f"{proc.get('memory_gb', 0.0):.2f} GB",
            )
        )
    return rows


def discover_auxiliary_processes(names: set = AUXILIARY_PROCESS_NAMES) -> list:
    found = []
    for proc in psutil.process_iter(["pid", "name", "status", "memory_info"]):
        try:
            info = proc.info
            if info["name"] not in names:
                continue
            memory_info = info.get("memory_info")
            found.append(
                {
                    "name": info["name"],
                    "pid": info["pid"],
                    "status": info["status"],
                    "cpu_percent": proc.cpu_percent(interval=None),
                    "memory_gb": (memory_info.rss if memory_info else 0) / (1024**3),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return found


def perform_hard_kill(send_request: Optional[Callable] = None, state_file: Optional[Path] = None) -> dict:
    """t69 --kill: the hard kill switch. Wipe state, force sleep unblocked."""
    send_request = send_request or ipc.send_request
    state_file = state_file or shared.state_file_path()

    daemon_response = {"ok": False}
    try:
        daemon_response = send_request(shared.socket_path(), {"cmd": "KILL_ALL"})
    except ConnectionError:
        pass

    helper_response = {"ok": False}
    try:
        helper_response = send_request(
            shared.HELPER_SOCKET_PATH, {"method": "set_sleep_blocked", "params": {"blocked": False}}
        )
    except ConnectionError:
        pass

    if state_file.exists():
        state_file.unlink()

    return {"ok": True, "daemon": daemon_response, "helper": helper_response}


class SixNineApp(App):
    CSS = """
    #banner { padding: 1; text-style: bold; }
    #aux-label { padding: 1 1 0 1; text-style: bold; }
    """
    BINDINGS = [
        ("q", "quit_dashboard", "Quit"),
        ("k", "kill_selected", "Kill session"),
        ("x", "purge_all", "Purge all"),
        ("a", "ignore_process", "Ignore process"),
        ("r", "restore_processes", "Restore"),
    ]

    def __init__(
        self,
        send_request: Optional[Callable] = None,
        discover: Optional[Callable] = None,
        refresh_interval: float = 2.0,
    ) -> None:
        super().__init__()
        self._send_request = send_request or ipc.send_request
        self._discover = discover or discover_auxiliary_processes
        self._refresh_interval = refresh_interval
        self._ignored = load_filter()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="banner")
        yield DataTable(id="sessions")
        yield Static("AUXILIARY WORKLOADS", id="aux-label")
        yield DataTable(id="auxiliary")
        yield Footer()

    def on_mount(self) -> None:
        sessions_table = self.query_one("#sessions", DataTable)
        sessions_table.add_columns("Session", "Agent", "Reason", "Held For")
        aux_table = self.query_one("#auxiliary", DataTable)
        aux_table.add_columns("Process", "PID", "Status", "CPU", "Memory")
        self.set_interval(self._refresh_interval, self.refresh_data)
        self.refresh_data()

    def refresh_data(self) -> None:
        try:
            state = self._send_request(shared.socket_path(), {"cmd": "STATUS"})
        except ConnectionError:
            state = {"active_sessions": {}, "status": "IDLE", "sleep_blocked": False}

        banner = self.query_one("#banner", Static)
        banner.update(
            f"6ix9ine CORE - SLEEP PREVENTION REGISTRY  "
            f"[ {state.get('status', 'IDLE')} ]  sleep_blocked={state.get('sleep_blocked', False)}"
        )

        sessions_table = self.query_one("#sessions", DataTable)
        sessions_table.clear()
        for row in build_session_rows(state):
            sessions_table.add_row(*row, key=row[0])

        aux_table = self.query_one("#auxiliary", DataTable)
        aux_table.clear()
        for row in build_auxiliary_rows(self._discover(), self._ignored):
            aux_table.add_row(*row, key=row[0])

    def action_quit_dashboard(self) -> None:
        self.exit()

    def action_kill_selected(self) -> None:
        table = self.query_one("#sessions", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            return
        session_key = table.get_row_at(table.cursor_row)[0]
        try:
            self._send_request(shared.socket_path(), {"cmd": "RELEASE", "session": session_key})
        except ConnectionError:
            pass
        self.refresh_data()

    def action_purge_all(self) -> None:
        try:
            self._send_request(shared.socket_path(), {"cmd": "KILL_ALL"})
        except ConnectionError:
            pass
        self.refresh_data()

    def action_ignore_process(self) -> None:
        table = self.query_one("#auxiliary", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            return
        process_name = table.get_row_at(table.cursor_row)[0]
        self._ignored.add(process_name)
        save_filter(self._ignored)
        self.refresh_data()

    def action_restore_processes(self) -> None:
        self._ignored.clear()
        save_filter(self._ignored)
        self.refresh_data()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="t69")
    parser.add_argument("--kill", action="store_true")
    return parser


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.kill:
        result = perform_hard_kill()
        print(json.dumps(result, indent=2, default=str))
        return shared.EXIT_OK if result.get("ok") else shared.EXIT_GENERAL_ERROR
    SixNineApp().run()
    return shared.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
