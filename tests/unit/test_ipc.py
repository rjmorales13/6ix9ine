from __future__ import annotations

import socket
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

import ipc


@pytest.fixture
def short_sock_path():
    # AF_UNIX paths are capped at ~104 bytes on macOS; pytest's tmp_path
    # fixture nests under a long /private/var/folders/... prefix that
    # regularly blows this limit, so use a short /tmp path instead.
    sock_path = Path(tempfile.gettempdir()) / f"6ix9ine-test-{uuid.uuid4().hex[:8]}.sock"
    yield sock_path
    sock_path.unlink(missing_ok=True)


def test_encode_message_appends_single_newline():
    assert ipc.encode_message({"cmd": "STATUS"}) == b'{"cmd": "STATUS"}\n'


def test_decode_message_parses_json_line():
    assert ipc.decode_message(b'{"ok": true, "count": 2}') == {"ok": True, "count": 2}


def test_decode_message_rejects_malformed_json():
    with pytest.raises(ipc.ProtocolError):
        ipc.decode_message(b"not json")


def test_get_peer_pid_returns_none_on_non_darwin(monkeypatch):
    monkeypatch.setattr(ipc.sys, "platform", "linux")
    a, b = socket.socketpair()
    try:
        assert ipc.get_peer_pid(a) is None
    finally:
        a.close()
        b.close()


@pytest.mark.skipif(sys.platform != "darwin", reason="LOCAL_PEERPID is macOS-specific")
def test_get_peer_pid_returns_this_process_pid_over_socketpair():
    import os

    a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        pid = ipc.get_peer_pid(a)
        assert pid == os.getpid()
    finally:
        a.close()
        b.close()


@pytest.mark.asyncio
async def test_line_json_server_round_trips_request_and_response(short_sock_path):
    sock_path = short_sock_path

    async def handler(request, peer_pid):
        return {"ok": True, "echo": request.get("cmd")}

    server = ipc.LineJSONServer(sock_path, handler)
    await server.start()
    try:
        response = await ipc.send_request_async(sock_path, {"cmd": "STATUS"})
        assert response == {"ok": True, "echo": "STATUS"}
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_line_json_server_returns_error_payload_when_handler_raises(short_sock_path):
    sock_path = short_sock_path

    async def handler(request, peer_pid):
        raise RuntimeError("boom")

    server = ipc.LineJSONServer(sock_path, handler)
    await server.start()
    try:
        response = await ipc.send_request_async(sock_path, {"cmd": "STATUS"})
        assert response["ok"] is False
        assert "boom" in response["error"]
    finally:
        await server.stop()


def test_send_request_raises_connection_error_when_socket_missing(tmp_path):
    sock_path = tmp_path / "missing.sock"
    with pytest.raises(ConnectionError):
        ipc.send_request(sock_path, {"cmd": "STATUS"}, timeout=0.5)
