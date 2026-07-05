from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, FrozenSet, Iterable, List, Optional, Set, Tuple

import psutil
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import DataTable, Footer, Static
from textual.widgets.data_table import CellDoesNotExist

import ipc
import shared
import tui_theme
import tui_wordmark

AUXILIARY_PROCESS_NAMES: FrozenSet[str] = frozenset({"ollama", "dockerd", "com.docker.backend"})

# Everything ipc.send_request can realistically raise: ConnectionError (a
# subclass of OSError) on connect, socket.timeout (also OSError) on a slow
# daemon, ProtocolError on malformed responses. The TUI must survive all.
IPC_ERRORS = (OSError, ipc.ProtocolError)

REASON_STYLE = "#aab2bd"
HOLD_HELD_STYLE = "#8b93a0"
WATCHING_LINE = "watching: 🤖 claude · 🧰 opencode · ⌘ codex"


# --------------------------------------------------------------------------
# persisted ignore-filter for auxiliary processes
# --------------------------------------------------------------------------


def load_filter(path: Optional[Path] = None) -> Set[str]:
    path = path or shared.filter_file_path()
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return set()
    return set(data.get("ignored", []))


def save_filter(ignored: Set[str], path: Optional[Path] = None) -> None:
    path = path or shared.filter_file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"ignored": sorted(ignored)}, indent=2))
    except OSError:
        pass  # an unwritable filter file must not crash a key action


# --------------------------------------------------------------------------
# pure state → row shaping (unit tested, no Textual involved)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class MonitorRow:
    key: str
    label: str
    uuid_short: str
    pid_display: str
    held_text: str
    held_seconds: Optional[float]
    reason: str
    is_hold: bool


def build_monitor_rows(state: dict, now: Optional[float] = None) -> List[MonitorRow]:
    """Sessions first (longest-held at the top), then timed holds, quieter.

    Defensive at the boundary: a live daemon may send null fields, and row
    keys must be unique for the DataTable, so duplicates are skipped.
    """
    now = now if now is not None else time.time()
    rows: List[MonitorRow] = []
    seen: Set[str] = set()
    sessions = state.get("active_sessions", {}) or {}
    for key, session in sorted(sessions.items(), key=lambda kv: kv[1].get("timestamp") or 0.0):
        if key in seen:
            continue
        seen.add(key)
        held_seconds = max(0.0, now - float(session.get("timestamp") or now))
        pid = session.get("pid")
        rows.append(
            MonitorRow(
                key=key,
                label=tui_theme.agent_label(session.get("agent") or ""),
                uuid_short=key[:8],
                pid_display=str(pid) if pid else "—",
                held_text=shared.format_duration(held_seconds),
                held_seconds=held_seconds,
                reason=session.get("reason") or "",
                is_hold=False,
            )
        )
    for hold in sorted(state.get("holds", []) or [], key=lambda h: h.get("id") or ""):
        hold_id = hold.get("id") or ""
        if not hold_id or hold_id in seen:
            continue
        seen.add(hold_id)
        rows.append(
            MonitorRow(
                key=hold_id,
                label="⏱ hold",
                uuid_short=hold_id[:8],
                pid_display="—",
                held_text=f"{hold.get('expires_in') or '?'} left",
                held_seconds=None,
                reason=hold.get("reason") or "",
                is_hold=True,
            )
        )
    return rows


def styled_monitor_cells(row: MonitorRow) -> Tuple[Text, Text, Text, Text, Text]:
    if row.is_hold:
        return (
            Text(row.label, style=tui_theme.HOLD_TEXT),
            Text(row.uuid_short, style=tui_theme.HOLD_TEXT),
            Text(row.pid_display, style=tui_theme.TEXT_FAINT),
            Text(row.held_text, style=HOLD_HELD_STYLE),
            Text(row.reason, style=tui_theme.HOLD_TEXT),
        )
    tier = tui_theme.held_tier(row.held_seconds or 0.0)
    held_style = f"bold {tier.color}" if tier.bold else tier.color
    held_text = f"{row.held_text} 🔥" if tier.fire else row.held_text
    return (
        Text(row.label, style=f"bold {tui_theme.session_color(row.key)}"),
        Text(row.uuid_short, style=tui_theme.TEXT_DIM),
        Text(row.pid_display, style=tui_theme.TEXT_FAINT if row.pid_display == "—" else tui_theme.TEXT),
        Text(held_text, style=held_style),
        Text(row.reason, style=REASON_STYLE),
    )


def build_auxiliary_rows(processes: Iterable[dict], ignored: Set[str]) -> List[Tuple[str, str, str, str, str]]:
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


def styled_aux_cells(row: Tuple[str, ...]) -> Tuple[Text, ...]:
    return tuple(Text(cell, style=tui_theme.TEXT_FAINT) for cell in row)


def build_topline(state: dict) -> Text:
    text = Text()
    text.append("status view", style="bold #e8e6e1")
    text.append("  ")
    status = state.get("status", "IDLE")
    fg, bg = tui_theme.CHIP_ACTIVE if status == "ACTIVE" else tui_theme.CHIP_IDLE
    text.append(f" {status} ", style=f"bold {fg} on {bg}")
    text.append("  ")
    if state.get("sleep_blocked", False):
        fg, bg = tui_theme.CHIP_BLOCKED
        text.append(" SLEEP BLOCKED ", style=f"bold {fg} on {bg}")
    else:
        fg, bg = tui_theme.CHIP_SLEEP_OK
        text.append(" 💤 SLEEP AVAILABLE ", style=f"bold {fg} on {bg}")
    return text


def build_topline_meta(state: dict, clock: Optional[str] = None) -> Text:
    sessions = len(state.get("active_sessions", {}) or {})
    holds = len(state.get("holds", []) or [])
    lid = state.get("lid", "unknown")
    clock = clock or datetime.now().strftime("%H:%M:%S")
    return Text(
        f"{sessions} sessions · {holds} holds · lid {lid} · {clock}",
        style=tui_theme.TEXT_DIM,
    )


def sleep_blocked_since(state: dict) -> Optional[str]:
    """Approximate: sleep has been blocked at least since the oldest session."""
    if not state.get("sleep_blocked", False):
        return None
    timestamps = [
        float(s.get("timestamp", 0.0))
        for s in (state.get("active_sessions", {}) or {}).values()
        if s.get("timestamp")
    ]
    if not timestamps:
        return None
    return datetime.fromtimestamp(min(timestamps)).strftime("%H:%M:%S")


def build_inspector_text(
    row: Optional[MonitorRow], state: dict, full_key: Optional[str] = None
) -> Text:
    text = Text()

    def kv(k: str, v: str, style: str = tui_theme.TEXT) -> None:
        text.append(f"{k:<10}", style=tui_theme.TEXT_DIM)
        text.append(v, style=style)
        text.append("\n")

    if row is None:
        text.append("nothing holding sleep\n", style=tui_theme.TEXT_DIM)
    elif row.is_hold:
        kv("hold", row.key, tui_theme.HOLD_TEXT)
        kv("expires", row.held_text)
        kv("reason", row.reason or "—")
    else:
        kv("agent", row.label, f"bold {tui_theme.session_color(row.key)}")
        kv("uuid", full_key or row.key)
        kv("pid", row.pid_display)
        tier = tui_theme.held_tier(row.held_seconds or 0.0)
        kv("held", row.held_text, tier.color)
        kv("reason", row.reason or "—")

    since = sleep_blocked_since(state)
    if state.get("sleep_blocked", False):
        fg, _ = tui_theme.CHIP_BLOCKED
        kv("sleep", f"BLOCKED{f' since ≈{since}' if since else ''}", f"bold {fg}")
    else:
        fg, _ = tui_theme.CHIP_SLEEP_OK
        kv("sleep", "💤 available", fg)
    lid = state.get("lid", "unknown")
    kv("lid", str(lid), tui_theme.CHIP_ACTIVE[0] if lid == "open" else tui_theme.TEXT)
    thermal = state.get("thermal", {}) or {}
    temp = thermal.get("current_temp")
    if temp is not None:
        kv("thermal", f"{temp}°C", tui_theme.TEXT)
    else:
        kv("thermal", "n/a", tui_theme.TEXT_FAINT)
    return text


def build_hello_lines(daemon_connected: bool, helper_ok: Optional[bool] = None) -> Tuple[Text, Text]:
    line1 = Text()
    line1.append("status view", style=tui_theme.TEXT_DIM)
    if daemon_connected:
        line1.append(" · daemon connected", style=tui_theme.TEXT_DIM)
    else:
        line1.append(" · daemon offline", style=f"bold {tui_theme.CHIP_BLOCKED[0]}")
    if helper_ok is True:
        line1.append(" · helper ok", style=tui_theme.TEXT_DIM)
    elif helper_ok is False:
        line1.append(" · helper unreachable", style=f"bold {tui_theme.CHIP_BLOCKED[0]}")
    return line1, Text(WATCHING_LINE, style=tui_theme.TEXT_DIM)


# --------------------------------------------------------------------------
# process discovery + hard kill (unchanged behavior)
# --------------------------------------------------------------------------


def discover_auxiliary_processes(names: FrozenSet[str] = AUXILIARY_PROCESS_NAMES) -> List[dict]:
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


def perform_hard_kill(
    send_request: Optional[Callable] = None, state_file: Optional[Path] = None
) -> Dict[str, Any]:
    """t69 --kill: the hard kill switch. Wipe state, force sleep unblocked."""
    send_request = send_request or ipc.send_request
    state_file = state_file or shared.state_file_path()

    daemon_response: Dict[str, Any] = {"ok": False}
    try:
        daemon_response = send_request(shared.socket_path(), {"cmd": "KILL_ALL"})
    except IPC_ERRORS:
        pass

    helper_response: Dict[str, Any] = {"ok": False}
    try:
        helper_response = send_request(
            shared.HELPER_SOCKET_PATH, {"method": "set_sleep_blocked", "params": {"blocked": False}}
        )
    except IPC_ERRORS:
        pass

    if state_file.exists():
        state_file.unlink()

    return {"ok": True, "daemon": daemon_response, "helper": helper_response}


# --------------------------------------------------------------------------
# the Textual app
# --------------------------------------------------------------------------

def idle_state() -> Dict[str, Any]:
    """Fresh idle-state dict (a factory so callers never share mutables)."""
    return {"active_sessions": {}, "holds": [], "status": "IDLE", "sleep_blocked": False}


class SixNineApp(App):
    CSS = f"""
    Screen {{
        background: {tui_theme.BACKGROUND};
        color: {tui_theme.TEXT};
    }}
    #wordmark {{ height: auto; padding: 0 1; }}
    #hello1, #hello2 {{ height: 1; padding: 0 1; }}
    #topline-row {{ height: 1; padding: 0 1; margin-top: 1; }}
    #topline {{ width: auto; }}
    #topline-meta {{ width: 1fr; text-align: right; }}
    #monitor {{
        border: solid {tui_theme.BORDER};
        border-title-color: #8b93a0;
        height: 1fr;
        margin: 1 1 0 1;
    }}
    #bottom {{ height: 11; margin: 1 1 0 1; }}
    #inspector {{
        border: solid {tui_theme.BORDER};
        border-title-color: #8b93a0;
        width: 3fr;
        padding: 0 1;
    }}
    #auxiliary {{
        border: solid {tui_theme.BORDER_QUIET};
        border-title-color: {tui_theme.TEXT_DIM};
        width: 2fr;
        margin-left: 1;
    }}
    DataTable {{ background: {tui_theme.BACKGROUND}; }}
    DataTable > .datatable--header {{
        background: {tui_theme.BACKGROUND};
        color: {tui_theme.TEXT_DIM};
    }}
    DataTable > .datatable--cursor {{ background: #14181e; }}
    * {{
        scrollbar-background: {tui_theme.BACKGROUND};
        scrollbar-background-hover: {tui_theme.BACKGROUND};
        scrollbar-background-active: {tui_theme.BACKGROUND};
        scrollbar-color: {tui_theme.BORDER_QUIET};
        scrollbar-color-hover: {tui_theme.BORDER};
        scrollbar-color-active: {tui_theme.BORDER};
        scrollbar-corner-color: {tui_theme.BACKGROUND};
        scrollbar-size-vertical: 1;
        scrollbar-size-horizontal: 1;
    }}
    """

    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        ("q", "quit_dashboard", "quit"),
        ("k", "kill_selected", "kill"),
        ("x", "purge_all", "purge"),
        ("a", "ignore_process", "ignore"),
        ("r", "restore_processes", "restore"),
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
        self._rows: Dict[str, MonitorRow] = {}
        self._state: Dict[str, Any] = idle_state()
        self._connected = False
        self._helper_ok: Optional[bool] = None

    def compose(self) -> ComposeResult:
        yield Static(id="wordmark")
        yield Static(id="hello1")
        yield Static(id="hello2")
        with Horizontal(id="topline-row"):
            yield Static(id="topline")
            yield Static(id="topline-meta")
        yield DataTable(id="monitor")
        with Horizontal(id="bottom"):
            yield Static(id="inspector")
            yield DataTable(id="auxiliary")
        yield Footer()

    def on_mount(self) -> None:
        monitor = self.query_one("#monitor", DataTable)
        monitor.add_columns("AGENT", "UUID", "PID", "HELD", "REASON")
        monitor.cursor_type = "row"
        aux = self.query_one("#auxiliary", DataTable)
        aux.add_columns("PROCESS", "PID", "STATUS", "CPU", "MEM")
        aux.cursor_type = "row"
        aux.border_title = "module dash · auxiliary background processes running"
        self._render_wordmark()
        self.set_interval(self._refresh_interval, self.refresh_data)
        self.refresh_data()

    # ------------------------------------------------------------- header

    def _render_wordmark(self) -> None:
        wordmark = self.query_one("#wordmark", Static)
        if tui_wordmark.should_collapse(self.size.height):
            wordmark.update(tui_wordmark.render_collapsed())
        else:
            banner = tui_wordmark.render_banner()
            banner.append("  ")
            banner.append(tui_wordmark.TAGLINE, style=tui_wordmark.TAGLINE_COLOR)
            wordmark.update(banner)

    def on_resize(self, event: events.Resize) -> None:
        self._render_wordmark()

    # ------------------------------------------------------------ refresh

    def refresh_data(self) -> None:
        try:
            state = self._send_request(shared.socket_path(), {"cmd": "STATUS"})
            if not isinstance(state, dict):
                raise ipc.ProtocolError(f"expected dict, got {type(state).__name__}")
            self._state = state
            self._connected = True
        except IPC_ERRORS:
            self._state = idle_state()
            self._connected = False

        try:
            self._send_request(shared.HELPER_SOCKET_PATH, {"method": "ping"})
            self._helper_ok = True
        except IPC_ERRORS:
            self._helper_ok = False

        line1, line2 = build_hello_lines(self._connected, self._helper_ok)
        self.query_one("#hello1", Static).update(line1)
        self.query_one("#hello2", Static).update(line2)
        self.query_one("#topline", Static).update(build_topline(self._state))
        self.query_one("#topline-meta", Static).update(build_topline_meta(self._state))

        monitor = self.query_one("#monitor", DataTable)
        rows = build_monitor_rows(self._state)
        self._rows = {row.key: row for row in rows}
        previous_key = self._cursor_key(monitor)
        monitor.clear()
        for row in rows:
            monitor.add_row(*styled_monitor_cells(row), key=row.key)
        active = sum(1 for row in rows if not row.is_hold)
        monitor.border_title = f"dense monitor · {active} active"
        if previous_key and previous_key in self._rows:
            keys = [row.key for row in rows]
            monitor.move_cursor(row=keys.index(previous_key))

        aux = self.query_one("#auxiliary", DataTable)
        aux.clear()
        for row in build_auxiliary_rows(self._discover(), self._ignored):
            # key = "name#pid": several processes may share a name, and
            # DataTable raises DuplicateKey on repeated row keys.
            aux.add_row(*styled_aux_cells(row), key=f"{row[0]}#{row[1]}")

        self._update_inspector(monitor)

    def _cursor_key(self, table: DataTable) -> Optional[str]:
        if table.row_count == 0 or table.cursor_row is None:
            return None
        try:
            row_key, _ = table.coordinate_to_cell_key((table.cursor_row, 0))
        except CellDoesNotExist:
            return None
        return row_key.value if row_key else None

    def _update_inspector(self, monitor: Optional[DataTable] = None) -> None:
        monitor = monitor or self.query_one("#monitor", DataTable)
        inspector = self.query_one("#inspector", Static)
        key = self._cursor_key(monitor)
        row = self._rows.get(key) if key else None
        inspector.border_title = f"split inspector · {row.uuid_short}" if row else "split inspector"
        inspector.update(build_inspector_text(row, self._state, full_key=key))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "monitor":
            self._update_inspector(event.data_table)

    # ------------------------------------------------------------ actions

    def action_quit_dashboard(self) -> None:
        self.exit()

    def action_kill_selected(self) -> None:
        monitor = self.query_one("#monitor", DataTable)
        key = self._cursor_key(monitor)
        row = self._rows.get(key) if key else None
        if row is None or row.is_hold:
            return
        try:
            self._send_request(shared.socket_path(), {"cmd": "RELEASE", "session": key})
        except IPC_ERRORS:
            pass
        self.refresh_data()

    def action_purge_all(self) -> None:
        try:
            self._send_request(shared.socket_path(), {"cmd": "KILL_ALL"})
        except IPC_ERRORS:
            pass
        self.refresh_data()

    def action_ignore_process(self) -> None:
        aux = self.query_one("#auxiliary", DataTable)
        key = self._cursor_key(aux)
        if not key:
            return
        name = key.rsplit("#", 1)[0]  # aux row keys are "name#pid"
        self._ignored.add(name)
        save_filter(self._ignored)
        self.refresh_data()

    def action_restore_processes(self) -> None:
        self._ignored.clear()
        save_filter(self._ignored)
        self.refresh_data()


# --------------------------------------------------------------------------
# CLI entry
# --------------------------------------------------------------------------


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
