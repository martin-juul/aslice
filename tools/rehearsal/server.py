"""Loopback service with single-use, capability-scoped process credentials."""
import copy
import hmac
import re
import secrets
import socket
import socketserver
import threading

from .model import Refusal
from .protocol import receive, send


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = False
    daemon_threads = False

    def __init__(self, model):
        self.model = model
        self.credentials = {}
        self.transcript = []
        self.guard = threading.Lock()
        self.processes = {}
        self.registrations = {}
        self.terminated = {}
        self.connections = set()
        super().__init__(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.serve_forever, daemon=True)
        self.thread.start()

    def issue(self, identity, capabilities):
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", identity):
            raise ValueError("invalid process identity")
        token = secrets.token_hex(32)
        with self.guard:
            self.credentials[identity] = (token, frozenset(capabilities))
        sequence = max((int(key.split(":")[1]) for key in self.model.state["outcomes"]
                        if key.startswith(identity + ":")), default=0)
        return {"version": 1, "sequence": sequence, "host": "127.0.0.1", "port": self.server_address[1],
                "identity": identity, "token": token}

    def close(self):
        self.shutdown()
        self.server_close()
        self.thread.join()

    def expect_process(self, identity):
        self.registrations[identity] = threading.Event()

    def attach_process(self, identity, process):
        self.processes[identity] = process
        self.registrations[identity].set()

    def stop(self, identity, kind):
        identities = list(self.registrations) if kind == "power_loss" else [identity]
        for owner in identities:
            ready = self.registrations.get(owner)
            if ready is not None and ready.wait(5):
                process = self.processes[owner]
                if process.poll() is None:
                    self.terminated[owner] = kind
                    process.kill()
        if kind == "power_loss":
            with self.guard:
                self.credentials.clear()
                for connection in self.connections:
                    try:
                        connection.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(10)
        self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        identity = None
        try:
            hello = receive(self.request)
            if (set(hello) != {"version", "operation", "identity", "token"}
                    or hello["version"] != 1 or hello["operation"] != "hello"
                    or not isinstance(hello["identity"], str) or not isinstance(hello["token"], str)):
                return
            with self.server.guard:
                grant = self.server.credentials.get(hello["identity"])
                if grant is None or not hmac.compare_digest(grant[0], hello["token"]):
                    return
                identity = hello["identity"]
                del self.server.credentials[identity]
                self.server.connections.add(self.request)
            send(self.request, {"version": 1, "authenticated": True})
            while True:
                request = receive(self.request)
                # Serialize state changes and their evidence in the same order.
                with self.server.model.mutex:
                    response, disconnect = self.server.model.execute(identity, grant[1], request)
                    self.server.transcript.append(copy.deepcopy(
                        {"identity": identity, "request": request, "response": response,
                         "acknowledged": not disconnect}))
                    stop_kind = self.server.model.stop_kind
                    if stop_kind in ("terminate", "power_loss"):
                        self.server.stop(identity, stop_kind)
                if disconnect:
                    return
                send(self.request, response)
        except (EOFError, OSError, ValueError, RecursionError, Refusal):
            return
        finally:
            if identity is not None:
                with self.server.guard:
                    self.server.connections.discard(self.request)
                self.server.model.disconnect(identity)
