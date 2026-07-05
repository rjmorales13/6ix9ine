from __future__ import annotations

import asyncio
import json

import pytest

import shared
import tui
import tui_theme
import tui_wordmark


SESSION_KEY = "a3f8c2e1-77aa-4b0e-9c31-08d2f4e6b5aa"


def make_state(**overrides):
    state = {
        "status": "ACTIVE",
        "sleep_blocked": True,
        "lid": "open",
        "thermal": {},
        "active_sessions": {
            SESSION_KEY: {
                "agent": "claude",
                "reason": "refactor tui.py into the new status view",
                "timestamp": 1000.0,
                "pid": None,
                "held_for": "3m 20s",
            }
        },
        "holds": [{"id": "hold-4fa2", "reason": "overnight download", "expires_in": "12m 30s"}],
    }
    state.update(overrides)
    return state


# ------------------------------------------------------------ monitor rows


def test_build_monitor_rows_sessions_then_holds():
    rows = tui.build_monitor_rows(make_state(), now=1200.0)
    assert [row.is_hold for row in rows] == [False, True]
    session, hold = rows
    assert session.key == SESSION_KEY
    assert session.label == "🤖 claude"
    assert session.uuid_short == SESSION_KEY[:8]
    assert session.held_seconds == pytest.approx(200.0)
    assert session.held_text == "3m 20s"
    assert hold.label == "⏱ hold"
    assert hold.held_text == "12m 30s left"
    assert hold.held_seconds is None


def test_build_monitor_rows_missing_pid_renders_dash():
    rows = tui.build_monitor_rows(make_state(), now=1200.0)
    assert rows[0].pid_display == "—"


def test_build_monitor_rows_real_pid_passes_through():
    state = make_state()
    state["active_sessions"][SESSION_KEY]["pid"] = 4242
    rows = tui.build_monitor_rows(state, now=1200.0)
    assert rows[0].pid_display == "4242"


def test_build_monitor_rows_sessions_sorted_oldest_first():
    state = make_state()
    state["active_sessions"]["newer"] = {"agent": "opencode", "reason": "", "timestamp": 5000.0}
    rows = tui.build_monitor_rows(state, now=6000.0)
    assert [row.key for row in rows if not row.is_hold] == [SESSION_KEY, "newer"]


def test_build_monitor_rows_empty_when_idle():
    assert tui.build_monitor_rows({"active_sessions": {}, "holds": []}) == []


def test_build_monitor_rows_tolerates_daemon_down_shape():
    assert tui.build_monitor_rows({}) == []


def test_build_monitor_rows_coerces_null_fields_from_live_daemon():
    state = make_state()
    state["active_sessions"][SESSION_KEY].update(reason=None, agent=None, timestamp=None)
    state["holds"] = [{"id": "hold-1", "reason": None, "expires_in": None}]
    rows = tui.build_monitor_rows(state, now=1200.0)
    session, hold = rows
    assert session.reason == ""
    assert session.label == "❓ "  # unknown agent, but never None
    assert hold.reason == ""
    assert hold.held_text == "? left"
    for row in rows:  # none of this may crash rich.Text
        tui.styled_monitor_cells(row)


def test_build_monitor_rows_skips_duplicate_keys():
    state = make_state()
    state["holds"].append({"id": SESSION_KEY, "reason": "colliding hold", "expires_in": "1m"})
    rows = tui.build_monitor_rows(state, now=1200.0)
    assert [row.key for row in rows].count(SESSION_KEY) == 1


# ------------------------------------------------------------ styled cells


def test_styled_monitor_cells_session_colors():
    row = tui.build_monitor_rows(make_state(), now=1200.0)[0]
    label, uuid_cell, pid, held, reason = tui.styled_monitor_cells(row)
    assert tui_theme.session_color(row.key) in str(label.style)
    assert tui_theme.HELD_GREEN in str(held.style)
    assert pid.plain == "—"


def test_styled_monitor_cells_fire_suffix_after_an_hour():
    state = make_state(holds=[])
    rows = tui.build_monitor_rows(state, now=1000.0 + 3700)
    _, _, _, held, _ = tui.styled_monitor_cells(rows[0])
    assert "🔥" in held.plain
    assert tui_theme.HELD_HOT in str(held.style)
    assert "bold" in str(held.style)


def test_styled_monitor_cells_holds_are_quiet():
    hold_row = tui.build_monitor_rows(make_state(), now=1200.0)[1]
    label, _, _, _, reason = tui.styled_monitor_cells(hold_row)
    assert tui_theme.HOLD_TEXT in str(label.style)
    assert tui_theme.HOLD_TEXT in str(reason.style)


# ------------------------------------------------------------ header texts


def test_build_topline_blocked_chip():
    text = tui.build_topline(make_state()).plain
    assert "status view" in text
    assert "SLEEP BLOCKED" in text
    assert "ACTIVE" in text


def test_build_topline_sleep_available_chip():
    text = tui.build_topline(make_state(sleep_blocked=False, status="IDLE")).plain
    assert "💤 SLEEP AVAILABLE" in text


def test_build_topline_idle_chip_is_not_green():
    text = tui.build_topline(make_state(sleep_blocked=False, status="IDLE"))
    styles = " ".join(str(span.style) for span in text.spans)
    assert tui_theme.CHIP_IDLE[0] in styles
    assert tui_theme.CHIP_ACTIVE[0] not in styles


def test_build_topline_meta_counts():
    meta = tui.build_topline_meta(make_state(), clock="14:32:08").plain
    assert meta == "1 sessions · 1 holds · lid open · 14:32:08"


def test_build_hello_lines_reports_daemon_state():
    connected, _ = tui.build_hello_lines(True)
    offline, _ = tui.build_hello_lines(False)
    assert "daemon connected" in connected.plain
    assert "daemon offline" in offline.plain


def test_build_hello_lines_reports_helper_state():
    ok, _ = tui.build_hello_lines(True, helper_ok=True)
    down, _ = tui.build_hello_lines(True, helper_ok=False)
    unknown, _ = tui.build_hello_lines(True, helper_ok=None)
    assert "helper ok" in ok.plain
    assert "helper unreachable" in down.plain
    assert "helper" not in unknown.plain


# -------------------------------------------------------------- inspector


def test_inspector_shows_session_detail():
    state = make_state()
    row = tui.build_monitor_rows(state, now=1200.0)[0]
    text = tui.build_inspector_text(row, state, full_key=SESSION_KEY).plain
    assert SESSION_KEY in text
    assert "🤖 claude" in text
    assert "BLOCKED" in text
    assert "lid" in text and "open" in text
    assert "n/a" in text  # thermal unavailable


def test_inspector_shows_real_temperature_plainly():
    state = make_state(thermal={"current_temp": 63.5})
    row = tui.build_monitor_rows(state, now=1200.0)[0]
    text = tui.build_inspector_text(row, state, full_key=SESSION_KEY).plain
    assert "63.5°C" in text
    assert "n/a" not in text


def test_inspector_empty_state():
    text = tui.build_inspector_text(None, make_state(sleep_blocked=False)).plain
    assert "nothing holding sleep" in text
    assert "💤 available" in text


def test_inspector_hold_detail():
    state = make_state()
    hold_row = tui.build_monitor_rows(state, now=1200.0)[1]
    text = tui.build_inspector_text(hold_row, state).plain
    assert "hold-4fa2" in text
    assert "12m 30s left" in text


def test_sleep_blocked_since_uses_oldest_session():
    state = make_state()
    state["active_sessions"]["older"] = {"agent": "manual", "reason": "", "timestamp": 500.0}
    assert tui.sleep_blocked_since(state) is not None
    assert tui.sleep_blocked_since(make_state(sleep_blocked=False)) is None


# ------------------------------------------------- auxiliary rows + filter


def test_build_auxiliary_rows_formats_cpu_and_memory():
    processes = [{"name": "ollama", "pid": 9876, "status": "sleeping", "cpu_percent": 0.0, "memory_gb": 2.14}]
    rows = tui.build_auxiliary_rows(processes, ignored=set())
    assert rows == [("ollama", "9876", "sleeping", "0.0%", "2.14 GB")]


def test_build_auxiliary_rows_skips_ignored_processes():
    processes = [
        {"name": "ollama", "pid": 1, "status": "sleeping", "cpu_percent": 0.0, "memory_gb": 1.0},
        {"name": "dockerd", "pid": 2, "status": "running", "cpu_percent": 1.2, "memory_gb": 0.85},
    ]
    rows = tui.build_auxiliary_rows(processes, ignored={"ollama"})
    assert [row[0] for row in rows] == ["dockerd"]


def test_save_and_load_filter_round_trip(tmp_path):
    filter_path = tmp_path / "filter.json"
    tui.save_filter({"ollama", "dockerd"}, path=filter_path)
    assert tui.load_filter(path=filter_path) == {"ollama", "dockerd"}


def test_load_filter_returns_empty_set_when_missing(tmp_path):
    assert tui.load_filter(path=tmp_path / "missing.json") == set()


def test_load_filter_returns_empty_set_on_corrupt_file(tmp_path):
    filter_path = tmp_path / "filter.json"
    filter_path.write_text("not json")
    assert tui.load_filter(path=filter_path) == set()


def test_save_filter_tolerates_unwritable_path(tmp_path):
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("file, not directory")
    tui.save_filter({"ollama"}, path=blocker / "filter.json")  # must not raise


# ------------------------------------------------------------- hard kill


def test_perform_hard_kill_wipes_state_file_and_calls_both_sockets(tmp_path):
    state_file = tmp_path / "state.json"
    state_file.write_text("{}")
    calls = []

    def fake_send_request(sock_path, payload, timeout=5.0):
        calls.append((str(sock_path), payload))
        return {"ok": True}

    result = tui.perform_hard_kill(send_request=fake_send_request, state_file=state_file)

    assert result["ok"] is True
    assert not state_file.exists()
    assert {"cmd": "KILL_ALL"} in [payload for _, payload in calls]
    assert {"method": "set_sleep_blocked", "params": {"blocked": False}} in [payload for _, payload in calls]


def test_perform_hard_kill_tolerates_daemon_and_helper_being_down(tmp_path):
    state_file = tmp_path / "state.json"
    state_file.write_text("{}")

    def fake_send_request(sock_path, payload, timeout=5.0):
        raise ConnectionError("nothing running")

    result = tui.perform_hard_kill(send_request=fake_send_request, state_file=state_file)

    assert result["ok"] is True
    assert not state_file.exists()


# ------------------------------------------------------------- CLI entry


def test_build_parser_kill_flag():
    args = tui.build_parser().parse_args(["--kill"])
    assert args.kill is True


def test_build_parser_defaults_kill_false():
    args = tui.build_parser().parse_args([])
    assert args.kill is False


def test_main_kill_flag_invokes_hard_kill_and_returns_ok(monkeypatch, tmp_path, capsys):
    state_file = tmp_path / "state.json"
    state_file.write_text("{}")
    monkeypatch.setattr(shared, "state_file_path", lambda: state_file)

    def fake_send_request(sock_path, payload, timeout=5.0):
        return {"ok": True}

    monkeypatch.setattr(tui.ipc, "send_request", fake_send_request)

    exit_code = tui.main(["--kill"])

    assert exit_code == shared.EXIT_OK
    printed = json.loads(capsys.readouterr().out)
    assert printed["ok"] is True


# ---------------------------------------------------- Textual pilot smoke


def plain_of(widget) -> str:
    content = widget.content
    return content.plain if hasattr(content, "plain") else str(content)


def make_app(monkeypatch, state=None, send=None):
    monkeypatch.setattr(tui, "load_filter", lambda: set())

    def fake_send(sock, payload, timeout=5.0):
        if send is not None:
            return send(sock, payload)
        return state if state is not None else make_state()

    def fake_discover():
        return [{"name": "ollama", "pid": 1, "status": "running", "cpu_percent": 1.0, "memory_gb": 0.5}]

    return tui.SixNineApp(send_request=fake_send, discover=fake_discover)


def test_app_mounts_with_monitor_and_aux_tables(monkeypatch):
    app = make_app(monkeypatch)

    async def go():
        async with app.run_test(size=(110, 40)):
            monitor = app.query_one("#monitor")
            assert monitor.row_count == 2  # one session + one hold
            assert len(monitor.columns) == 5
            assert "1 active" in str(monitor.border_title)
            aux = app.query_one("#auxiliary")
            assert aux.row_count == 1
            wordmark = app.query_one("#wordmark")
            assert "\n" in plain_of(wordmark)  # full banner on tall terminal

    asyncio.run(go())


def test_app_collapses_wordmark_on_short_terminal(monkeypatch):
    app = make_app(monkeypatch)

    async def go():
        async with app.run_test(size=(100, 24)):
            wordmark = app.query_one("#wordmark")
            plain = plain_of(wordmark)
            assert "\n" not in plain
            assert "6ix9ine" in plain

    asyncio.run(go())


def test_app_survives_daemon_down(monkeypatch):
    def boom(sock, payload):
        raise ConnectionError("daemon not running")

    app = make_app(monkeypatch, send=boom)

    async def go():
        async with app.run_test(size=(110, 40)):
            assert app.query_one("#monitor").row_count == 0
            topline = plain_of(app.query_one("#topline"))
            assert "💤 SLEEP AVAILABLE" in topline
            hello = plain_of(app.query_one("#hello1"))
            assert "daemon offline" in hello

    asyncio.run(go())


@pytest.mark.parametrize(
    "raiser",
    [
        pytest.param(lambda: (_ for _ in ()).throw(__import__("socket").timeout("slow daemon")), id="socket-timeout"),
        pytest.param(lambda: (_ for _ in ()).throw(__import__("ipc").ProtocolError("malformed")), id="protocol-error"),
    ],
)
def test_app_survives_slow_or_malformed_daemon(monkeypatch, raiser):
    # Regression for the Opus review HIGH: only ConnectionError was caught,
    # so socket.timeout / ProtocolError crashed the 2s refresh loop.
    def send(sock, payload):
        next(raiser())

    app = make_app(monkeypatch, send=send)

    async def go():
        async with app.run_test(size=(110, 40)):
            assert app.query_one("#monitor").row_count == 0
            assert "daemon offline" in plain_of(app.query_one("#hello1"))

    asyncio.run(go())


def test_app_survives_non_dict_status_response(monkeypatch):
    app = make_app(monkeypatch, send=lambda sock, payload: ["not", "a", "dict"])

    async def go():
        async with app.run_test(size=(110, 40)):
            assert app.query_one("#monitor").row_count == 0
            assert "💤 SLEEP AVAILABLE" in plain_of(app.query_one("#topline"))

    asyncio.run(go())


def test_app_survives_duplicate_auxiliary_process_names(monkeypatch):
    # Regression for the Opus review HIGH: two processes sharing a name
    # raised DuplicateKey inside the refresh timer.
    monkeypatch.setattr(tui, "load_filter", lambda: set())

    def dupes():
        return [
            {"name": "ollama", "pid": 1, "status": "running", "cpu_percent": 1.0, "memory_gb": 0.5},
            {"name": "ollama", "pid": 2, "status": "running", "cpu_percent": 2.0, "memory_gb": 0.7},
        ]

    app = tui.SixNineApp(send_request=lambda sock, payload, timeout=5.0: make_state(), discover=dupes)

    async def go():
        async with app.run_test(size=(110, 40)):
            assert app.query_one("#auxiliary").row_count == 2

    asyncio.run(go())


def test_helper_probe_reflected_in_hello_line(monkeypatch):
    def send(sock, payload):
        if payload.get("method") == "ping":
            raise ConnectionError("helper not installed")
        return make_state()

    app = make_app(monkeypatch, send=send)

    async def go():
        async with app.run_test(size=(110, 40)):
            assert "helper unreachable" in plain_of(app.query_one("#hello1"))

    asyncio.run(go())


def test_kill_action_skips_hold_rows(monkeypatch):
    calls = []
    state = make_state(active_sessions={})

    def send(sock, payload):
        calls.append(payload)
        return state

    app = make_app(monkeypatch, send=send)

    async def go():
        async with app.run_test(size=(110, 40)):
            monitor = app.query_one("#monitor")
            assert monitor.row_count == 1  # just the hold
            app.action_kill_selected()
            assert {"cmd": "RELEASE", "session": "hold-4fa2"} not in calls

    asyncio.run(go())
