from __future__ import annotations

import asyncio
import json
import socket
import struct
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

# macOS <sys/un.h> local-domain socket options, used to authenticate the
# peer process on a Unix domain socket without a real Mach XPC service.
_SOL_LOCAL = 0
_LOCAL_PEERPID = 0x2

Handler = Callable[[dict, Optional[int]], Awaitable[dict]]


class ProtocolError(Exception):
    pass


def encode_message(payload: dict) -> bytes:
    return (json.dumps(payload) + "\n").encode("utf-8")


def decode_message(data: bytes) -> dict:
    try:
        return json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ProtocolError(f"malformed message: {exc}") from exc


def get_peer_pid(sock: socket.socket) -> Optional[int]:
    """Return the PID of the process on the other end of a UDS connection.

    Real Mach XPC caller verification needs the Security framework, which
    has no usable pure-Python binding. LOCAL_PEERPID gives us the same
    practical guarantee (kernel-verified peer PID) over a plain Unix
    domain socket.
    """
    if sys.platform != "darwin":
        return None
    try:
        raw = sock.getsockopt(_SOL_LOCAL, _LOCAL_PEERPID, struct.calcsize("i"))
    except OSError:
        return None
    return struct.unpack("i", raw)[0]


def send_request(sock_path: Path, payload: dict, timeout: float = 5.0) -> dict:
    """Synchronous client used by the CLI's latency-sensitive hot path."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(str(sock_path))
    except OSError as exc:
        sock.close()
        raise ConnectionError(str(exc)) from exc

    try:
        sock.sendall(encode_message(payload))
        sock.shutdown(socket.SHUT_WR)
        chunks: list[bytes] = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            if b"\n" in chunk:
                break
        data = b"".join(chunks)
        if not data:
            raise ConnectionError("connection closed with no response")
        line = data.split(b"\n", 1)[0]
        return decode_message(line)
    finally:
        sock.close()


async def send_request_async(sock_path: Path, payload: dict, timeout: float = 5.0) -> dict:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(path=str(sock_path)), timeout=timeout
        )
    except (OSError, asyncio.TimeoutError) as exc:
        raise ConnectionError(str(exc)) from exc

    try:
        writer.write(encode_message(payload))
        await writer.drain()
        line = await asyncio.wait_for(reader.readline(), timeout=timeout)
        if not line:
            raise ConnectionError("connection closed with no response")
        return decode_message(line)
    finally:
        writer.close()


class LineJSONServer:
    """Newline-delimited JSON UDS server: one request, one response, per connection."""

    def __init__(self, sock_path: Path, handler: Handler):
        self._sock_path = Path(sock_path)
        self._handler = handler
        self._server: Optional[asyncio.AbstractServer] = None

    async def start(self) -> None:
        self._sock_path.parent.mkdir(parents=True, exist_ok=True)
        if self._sock_path.exists():
            self._sock_path.unlink()
        self._server = await asyncio.start_unix_server(
            self._handle_connection, path=str(self._sock_path)
        )

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        if self._sock_path.exists():
            self._sock_path.unlink()

    async def serve_forever(self) -> None:
        assert self._server is not None, "call start() first"
        async with self._server:
            await self._server.serve_forever()

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            line = await reader.readline()
            if not line:
                return

            peer_pid = self._peer_pid(writer)
            try:
                request = decode_message(line)
                response = await self._handler(request, peer_pid)
            except ProtocolError as exc:
                response = {"ok": False, "error": str(exc)}
            except Exception as exc:  # handler bugs must not take the server down
                response = {"ok": False, "error": str(exc)}

            writer.write(encode_message(response))
            await writer.drain()
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass

    @staticmethod
    def _peer_pid(writer: asyncio.StreamWriter) -> Optional[int]:
        raw_sock = writer.get_extra_info("socket")
        if raw_sock is None:
            return None
        try:
            return get_peer_pid(raw_sock)
        except OSError:
            return None
