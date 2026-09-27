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
from .credentials import Credentials


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
        self.watchers = []
        self.terminated = {}
        self.connections = {}
        self.closed = False
        super().__init__(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.serve_forever, daemon=True)
        self.thread.start()

    def issue(self, identity, capabilities, credentials=None):
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", identity):
            raise ValueError("invalid process identity")
        token = secrets.token_hex(32)
        principal = Credentials.parse(credentials)
        with self.model.mutex:
            with self.guard:
                if self.closed or identity in self.registrations:
                    raise ValueError("process identity already issued or server closed")
                self.registrations[identity] = threading.Event()
                self.credentials[identity] = (token, frozenset(capabilities))
                self.model.process_credentials[identity] = principal
                self.model.issued_processes.add(identity)
        sequence = max((int(key.split(":")[1]) for key in self.model.state["outcomes"]
                        if key.startswith(identity + ":")), default=0)
        return {"version": 1, "sequence": sequence, "host": "127.0.0.1", "port": self.server_address[1],
                "identity": identity, "token": token}

    def close(self):
        with self.guard:
            if self.closed:
                return
            self.closed = True
            self.credentials.clear()
            processes = list(self.processes.values())
            for ready in self.registrations.values():
                ready.set()
            for connection in self.connections:
                self.disconnect_transport(connection)
        # Harness teardown is distinct from killing one modeled process. Do not
        # leave child processes or watcher threads alive after releasing a workspace.
        for process in processes:
            if process.poll() is None:
                process.kill()
        for watcher in self.watchers:
            watcher.join()
        self.shutdown()
        self.server_close()
        self.thread.join()
        for identity in self.registrations:
            self.model.process_exited(identity)

    def expect_process(self, identity):
        with self.guard:
            if self.closed or identity not in self.registrations or identity in self.processes:
                raise ValueError("process must have an unused issued identity")

    def inherit_channel(self, first, second, capacity=65536):
        # Harness-only setup, never an application RPC. Issue both process
        # identities first and provision their handles before launching either.
        with self.model.mutex:
            with self.guard:
                if (self.closed or any(owner not in self.credentials or owner in self.processes
                                       for owner in (first, second))):
                    raise ValueError("channel inheritance requires two unlaunched process identities")
                if any("channel" not in self.credentials[owner][1] for owner in (first, second)):
                    raise ValueError("channel inheritance requires channel capabilities")
                return self.model.channels.inherit(first, second, capacity)

    def attach_process(self, identity, process):
        with self.guard:
            if self.closed or identity not in self.registrations or identity in self.processes:
                raise ValueError("process must have an unused issued identity")
            self.processes[identity] = process
            watcher = threading.Thread(target=self.watch_process, args=(identity, process))
            self.watchers.append(watcher)
            watcher.start()
            self.registrations[identity].set()

    @staticmethod
    def disconnect_transport(connection):
        try:
            connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def watch_process(self, identity, process):
        process.wait()
        # Resource lifetime follows the owning process, not its IPC connection.
        self.model.process_exited(identity)
        with self.guard:
            self.credentials.pop(identity, None)
            for connection, owner in self.connections.items():
                if owner == identity:
                    self.disconnect_transport(connection)

    def stop(self, identity, kind):
        identities = list(self.registrations) if kind == "power_loss" else [identity]
        for owner in identities:
            ready = self.registrations.get(owner)
            if ready is not None and ready.wait(5):
                process = self.processes.get(owner)
                if process is None:
                    continue
                if process.poll() is None:
                    self.terminated[owner] = kind
                    process.kill()
        if kind == "power_loss":
            with self.guard:
                self.credentials.clear()
                for connection in self.connections:
                    self.disconnect_transport(connection)


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(10)
        self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        identity = None
        try:
            hello = receive(self.request)
            if (set(hello) != {"version", "operation", "identity", "token"}
                    or type(hello["version"]) is not int or hello["version"] != 1 or hello["operation"] != "hello"
                    or not isinstance(hello["identity"], str) or not isinstance(hello["token"], str)):
                return
            with self.server.guard:
                grant = self.server.credentials.get(hello["identity"])
                if grant is None or not hmac.compare_digest(grant[0], hello["token"]):
                    return
                ready = self.server.registrations[hello["identity"]]
            if not ready.wait(5):
                return
            with self.server.guard:
                process = self.server.processes.get(hello["identity"])
                if (self.server.closed or process is None or process.poll() is not None
                        or self.server.credentials.get(hello["identity"]) != grant):
                    return
                identity = hello["identity"]
                del self.server.credentials[identity]
                self.server.connections[self.request] = identity
            send(self.request, {"version": 1, "authenticated": True})
            while True:
                request = receive(self.request)
                # Serialize state changes and their evidence in the same order.
                with self.server.model.mutex:
                    if process.poll() is not None:
                        return
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
                    self.server.connections.pop(self.request, None)
