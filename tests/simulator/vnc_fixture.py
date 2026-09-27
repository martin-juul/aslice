"""Minimal RFB 3.8 peer for browser transport tests, not guest GUI evidence."""

import struct
import asyncio
from concurrent.futures import Future
from contextlib import contextmanager
from threading import Thread

from aiohttp import web


@contextmanager
def display_server(directory, machine):
    """Use a real WebSocket; browser API shims must not alter a mock socket."""
    ready = Future()
    peers = []

    async def run():
        stopped = asyncio.Event()

        async def index(request):
            return web.FileResponse(directory / "index.html")

        async def action(request):
            return web.json_response({"machines": [machine]})

        async def display(request):
            socket = web.WebSocketResponse()
            await socket.prepare(request)
            peer = VncFixture()
            peers.append(peer)
            await socket.send_bytes(peer.output.pop(0))
            async for message in socket:
                if message.type == web.WSMsgType.BINARY:
                    peer.receive(message.data)
                    while peer.output:
                        await socket.send_bytes(peer.output.pop(0))
            return socket

        app = web.Application()
        app.router.add_get("/", index)
        app.router.add_static("/static/", directory)
        app.router.add_post("/v1/action", action)
        app.router.add_get("/v1/vnc/sample", display)
        runner = web.AppRunner(app)
        await runner.setup()
        try:
            site = web.TCPSite(runner, "127.0.0.1", 0)
            await site.start()
            port = site._server.sockets[0].getsockname()[1]
            ready.set_result(
                (f"http://127.0.0.1:{port}", asyncio.get_running_loop(), stopped)
            )
            await stopped.wait()
        finally:
            await runner.cleanup()

    def worker():
        try:
            asyncio.run(run())
        except Exception as error:
            if not ready.done():
                ready.set_exception(error)
            else:
                raise

    thread = Thread(target=worker, daemon=True)
    thread.start()
    url, loop, stopped = ready.result(timeout=10)
    try:
        yield url, peers
    finally:
        loop.call_soon_threadsafe(stopped.set)
        thread.join(timeout=10)
        if thread.is_alive():
            raise RuntimeError("VNC browser fixture did not stop")


class VncFixture:
    def __init__(self):
        self.buffer = bytearray()
        self.stage = "version"
        self.sent_frame = False
        self.inputs = []
        self.output = [b"RFB 003.008\n"]

    def receive(self, message):
        self.buffer.extend(message)
        while self.buffer:
            if self.stage == "version":
                if len(self.buffer) < 12:
                    return
                del self.buffer[:12]
                self.output.append(b"\x01\x01")
                self.stage = "security"
            elif self.stage == "security":
                assert self.buffer.pop(0) == 1
                self.output.append(b"\x00\x00\x00\x00")
                self.stage = "initialization"
            elif self.stage == "initialization":
                self.buffer.pop(0)
                name = b"Browser fixture"
                self.output.append(
                    struct.pack(
                        "!HHBBBBHHHBBB3xI",
                        64,
                        32,
                        32,
                        24,
                        0,
                        1,
                        255,
                        255,
                        255,
                        16,
                        8,
                        0,
                        len(name),
                    )
                    + name
                )
                self.stage = "messages"
            else:
                kind = self.buffer[0]
                if kind == 2:
                    if len(self.buffer) < 4:
                        return
                    size = 4 + 4 * int.from_bytes(self.buffer[2:4], "big")
                else:
                    size = {0: 20, 3: 10, 4: 8, 5: 6}[kind]
                if len(self.buffer) < size:
                    return
                payload = bytes(self.buffer[:size])
                del self.buffer[:size]
                if kind == 0:
                    # The client selects little-endian RGB before requesting pixels.
                    assert payload[4:] == struct.pack(
                        "!BBBBHHHBBB3x", 32, 24, 0, 1, 255, 255, 255, 0, 8, 16
                    )
                if kind in (4, 5):
                    self.inputs.append(payload)
                if kind == 3 and not self.sent_frame:
                    self.sent_frame = True
                    self.output.append(
                        struct.pack("!BBHHHHHi", 0, 0, 1, 0, 0, 64, 32, 0)
                        + bytes([0x33, 0x66, 0x99, 0]) * 64 * 32
                    )
