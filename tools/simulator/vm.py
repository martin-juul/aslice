"""QEMU supervisors survive controller restarts and own one machine each."""

import ctypes
from concurrent.futures import ThreadPoolExecutor
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import queue
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import uuid

from .model import atomic_json


class Lease:
    def __init__(self, path):
        self.path = Path(path)
        self.stream = None

    def __enter__(self):
        self.stream = self.path.open("a+b")
        try:
            if self.stream.tell() == 0:
                self.stream.write(b"0")
                self.stream.flush()
            self.stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.stream.close()
            self.stream = None
            raise
        return self

    def __exit__(self, *_):
        self.stream.close()
        self.stream = None


def owned(directory):
    try:
        with Lease(Path(directory) / ".vm-lease"):
            return False
    except OSError:
        return True


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def private(path):
    """Keep host authority out of guest-readable artifacts and other host users."""
    path = Path(path)
    if os.name == "nt":
        import getpass

        subprocess.run(
            [
                "icacls",
                str(path),
                "/inheritance:r",
                "/grant:r",
                getpass.getuser() + (":(OI)(CI)F" if path.is_dir() else ":F"),
            ],
            check=True,
            capture_output=True,
        )
    else:
        path.chmod(0o700 if path.is_dir() else 0o600)


def detached(args, log):
    options = {
        "stdin": subprocess.DEVNULL,
        "stdout": log,
        "stderr": log,
        "close_fds": True,
    }
    if os.name == "nt":
        options["creationflags"] = (
            subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        options["start_new_session"] = True
    return subprocess.Popen(args, **options)


def qemu_command(config):
    # JSON blockdev options preserve commas and spaces in Windows/Linux paths.
    block = {
        "driver": "qcow2",
        "node-name": "disk",
        "file": {"driver": "file", "filename": config["disk"]},
    }
    command = [
        config.get("qemu", "qemu-system-x86_64"),
        "-name",
        "aslice-" + config["name"],
        "-uuid",
        config["uuid"],
        "-machine",
        "q35",
        "-accel",
        config["acceleration"],
        "-cpu",
        {"tcg": "max", "kvm": "host", "whpx": "Nehalem"}[config["acceleration"]],
        "-smp",
        str(config["cpus"]),
        "-m",
        str(config["memory_mib"]),
        "-nodefaults",
        "-display",
        "none",
        "-monitor",
        "none",
        "-qmp",
        "stdio",
        "-blockdev",
        json.dumps(block),
        "-device",
        "virtio-blk-pci,drive=disk",
        "-chardev",
        "ringbuf,id=serial,size=1048576",
        "-serial",
        "chardev:serial",
        "-netdev",
        f'user,id=management,restrict=on,net=10.0.2.0/24,hostfwd=tcp:127.0.0.1:{config["ssh_port"]}-:22',
        "-device",
        "virtio-net-pci,netdev=management,mac=52:54:00:12:34:01",
        "-netdev",
        "user,id=applications,net=10.0.3.0/24,restrict="
        + ("off" if config["network"] else "on"),
        "-device",
        "virtio-net-pci,netdev=applications,id=appnic,mac=52:54:00:12:34:02",
    ]
    if config.get("seed"):
        seed = {
            "driver": "raw",
            "node-name": "seed",
            "read-only": True,
            "file": {"driver": "file", "filename": config["seed"]},
        }
        command += [
            "-blockdev",
            json.dumps(seed),
            "-device",
            "virtio-blk-pci,drive=seed",
        ]
    # No host mounts, passthrough devices, display clipboard, VNC listener or
    # unauthenticated QMP socket. Application display is tunneled guest X11.
    return command


def parent_death(parent):
    # Called by the dedicated, still single-threaded supervisor before exec.
    if (
        os.getppid() != parent
        or ctypes.CDLL(None).prctl(1, 9) != 0
        or os.getppid() != parent
    ):
        os._exit(125)


def ssh_tunnel(directory, ssh_port):
    control = Path(directory) / "control"
    agent_port, vnc_port = port(), port()
    public = (control / "ssh-host.pub").read_text().strip().split()
    known = control / "known_hosts"
    known.write_text(f"[127.0.0.1]:{ssh_port} {public[0]} {public[1]}\n")
    command = [
        "ssh",
        "-F",
        os.devnull,
        "-N",
        "-T",
        "-p",
        str(ssh_port),
        "-i",
        str(control / "ssh-client"),
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "UserKnownHostsFile=" + str(known),
        "-o",
        "GlobalKnownHostsFile=" + os.devnull,
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "ConnectTimeout=5",
        "-o",
        "ServerAliveInterval=10",
        "-o",
        "ServerAliveCountMax=2",
        "-L",
        f"127.0.0.1:{agent_port}:127.0.0.1:9971",
        "-L",
        f"127.0.0.1:{vnc_port}:127.0.0.1:5900",
        "aslice-control@127.0.0.1",
    ]
    parent = os.getpid()
    options = (
        {"preexec_fn": lambda: parent_death(parent)}
        if os.name != "nt"
        else {"creationflags": subprocess.CREATE_NO_WINDOW}
    )
    with (control / "ssh.log").open("wb") as log:
        process = subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=log, stderr=log, **options
        )
    return process, {"agent_port": agent_port, "vnc_port": vnc_port}


class QMP:
    def __init__(self, process, logger):
        self.process, self.logger = process, logger
        self.replies = queue.Queue()
        self.lock = threading.Lock()
        threading.Thread(target=self.read, daemon=True).start()
        greeting = self.replies.get(timeout=10)
        if "QMP" not in greeting:
            raise ValueError("QEMU did not send a QMP greeting")
        self.command("qmp_capabilities")

    def read(self):
        while True:
            line = self.process.stdout.readline(2 * 1024 * 1024)
            if not line:
                self.replies.put({"error": {"desc": "QEMU connection closed"}})
                break
            try:
                message = json.loads(line)
                if "event" in message:
                    self.logger.info(json.dumps(message))
                else:
                    self.replies.put(message)
            except ValueError:
                self.logger.error("invalid QMP message")

    def command(self, execute, arguments=None):
        with self.lock:
            ident = uuid.uuid4().hex
            self.process.stdin.write(
                (
                    json.dumps(
                        {"execute": execute, "arguments": arguments or {}, "id": ident}
                    )
                    + "\n"
                ).encode()
            )
            self.process.stdin.flush()
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                message = self.replies.get(
                    timeout=max(0.01, deadline - time.monotonic())
                )
                if message.get("id") not in (None, ident):
                    continue
                if "error" in message:
                    raise ValueError(message["error"]["desc"])
                return message.get("return")
            raise TimeoutError("QMP response deadline exceeded")


def request(directory, action, **arguments):
    config = json.loads((Path(directory) / "control" / "supervisor.json").read_text())
    body = json.dumps({"action": action, **arguments}).encode()
    req = urllib.request.Request(
        f'http://127.0.0.1:{config["port"]}/v1/control',
        data=body,
        headers={
            "Authorization": "Bearer " + config["token"],
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        result = json.load(response)
    if "error" in result:
        raise ValueError(result["error"])
    return result


def start(store, machine, acceleration="auto", network=False):
    from .darwin import preflight
    from .provision import machine_seed

    directory = store.directory(machine)
    if owned(directory):
        raise ValueError("machine already has a live supervisor")
    data = store.stopped(machine)
    probe = preflight(acceleration)
    if probe["blockers"]:
        raise ValueError("; ".join(probe["blockers"]))
    control = directory / "control"
    control.mkdir(exist_ok=True)
    private(control)
    machine_seed(directory)
    launch = {
        "name": machine,
        "uuid": str(uuid.uuid4()),
        "disk": str(directory / data["disk"]),
        "seed": str(control / "seed.iso"),
        "acceleration": probe["accelerator"],
        "network": bool(network),
        "cpus": data["cpus"],
        "memory_mib": data["memory_mib"],
        "ssh_port": port(),
        "qemu": probe["tools"]["qemu-system-x86_64"],
        "token": secrets.token_urlsafe(32),
    }
    with store.operation("start", machine) as operation:
        launch["operation"] = operation
        atomic_json(control / "launch.json", launch)
        private(control / "launch.json")
        data.update(state="starting", network=bool(network), last_operation=operation)
        atomic_json(directory / "machine.json", data)
        with (control / "supervisor-start.log").open("wb") as log:
            process = detached(
                [sys.executable, "-m", "tools.simulator.vm", str(directory)], log
            )
        # Retain the store lease until the supervisor has claimed its machine
        # lease and published the matching launch. A second controller must not
        # interpret the fork/startup interval as an abandoned operation.
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            if owned(directory) and (directory / "vm-state.json").exists():
                state = json.loads((directory / "vm-state.json").read_text())
                if state.get("operation") == operation and state["state"] == "running":
                    break
            time.sleep(0.05)
        else:
            process.kill()
            process.wait(timeout=10)
        if not owned(directory) or process.poll() is not None:
            data.update(state="stopped", last_exit="startup failed or uncertain")
            atomic_json(directory / "machine.json", data)
            raise ValueError(
                "QEMU startup failed; inspect machine evidence/qemu.log and control/supervisor-start.log"
            )
        return {
            "state": "running",
            "supervisor_pid": process.pid,
            "operation": operation,
            "accelerator": probe["accelerator"],
            "software_emulation": probe["software_emulation"],
        }


def supervise(directory):
    directory = Path(directory).resolve()
    control = directory / "control"
    with Lease(directory / ".vm-lease"):
        config = json.loads((control / "launch.json").read_text())
        logger = logging.getLogger("qemu")
        logger.setLevel(logging.INFO)
        logger.addHandler(
            RotatingFileHandler(
                directory / "evidence" / "qemu.log", maxBytes=2**20, backupCount=3
            )
        )
        # Wrapper binds QEMU lifetime to this supervisor on both host platforms.
        if os.name == "nt":
            from .vm_child import lifetime_job

            job = lifetime_job()
        args = qemu_command(config)
        parent = os.getpid()
        options = (
            {"preexec_fn": lambda: parent_death(parent)}
            if os.name != "nt"
            else {"creationflags": subprocess.CREATE_NO_WINDOW}
        )
        child = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **options,
        )

        def stderr():
            for line in iter(lambda: child.stderr.readline(8192), b""):
                logger.info(line.decode("utf-8", "replace").rstrip())

        threading.Thread(target=stderr, daemon=True).start()
        tunnels = []
        tunnel_lock = threading.Lock()
        # Linux parent-death signals follow the thread that created the child.
        # HTTP request threads exit after a response; this worker stays alive
        # until the supervisor closes all its forwarding processes.
        tunnel_worker = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="ssh-owner"
        )
        try:
            qmp = QMP(child, logger)

            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *_):
                    pass

                def do_POST(self):
                    if not hmac.compare_digest(
                        self.headers.get("Authorization", ""),
                        "Bearer " + config["token"],
                    ):
                        self.send_error(403)
                        return
                    try:
                        size = int(self.headers.get("Content-Length", "0"))
                        if self.path != "/v1/control" or not 0 < size <= 8192:
                            raise ValueError("invalid supervisor request")
                        body = json.loads(self.rfile.read(size))
                        action = body["action"]
                        if action == "status":
                            result = qmp.command("query-status")
                        elif action == "stop":
                            result = qmp.command("system_powerdown")
                        elif action == "force":
                            result = qmp.command("quit")
                        elif action == "network":
                            result = qmp.command(
                                "set_link", {"name": "appnic", "up": bool(body["up"])}
                            )
                        elif action == "serial":
                            result = qmp.command(
                                "ringbuf-read",
                                {
                                    "device": "serial",
                                    "size": 1048576,
                                    "format": "base64",
                                },
                            )
                        elif action == "tunnel":
                            with tunnel_lock:
                                if not tunnels or tunnels[-1][0].poll() is not None:
                                    tunnels.append(
                                        tunnel_worker.submit(
                                            ssh_tunnel, directory, config["ssh_port"]
                                        ).result()
                                    )
                                result = tunnels[-1][1]
                        else:
                            raise ValueError("unsupported supervisor action")
                        encoded = json.dumps(
                            {"result": result, "operation": config["operation"]}
                        ).encode()
                    except (ValueError, KeyError, OSError, queue.Empty) as error:
                        encoded = json.dumps({"error": str(error)}).encode()
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)

            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            atomic_json(
                control / "supervisor.json",
                {
                    "port": server.server_port,
                    "token": config["token"],
                    "pid": os.getpid(),
                    "operation": config["operation"],
                },
            )
            private(control / "supervisor.json")
            atomic_json(
                directory / "vm-state.json",
                {
                    "state": "running",
                    "operation": config["operation"],
                    "ssh_port": config["ssh_port"],
                    "pid": child.pid,
                    "accelerator": config["acceleration"],
                },
            )
            threading.Thread(target=server.serve_forever, daemon=True).start()
            code = child.wait()
            atomic_json(
                directory / "vm-state.json",
                {
                    "state": "stopped",
                    "exit_code": code,
                    "operation": config["operation"],
                },
            )
            server.shutdown()
            server.server_close()
        finally:
            for tunnel, _ in tunnels:
                if tunnel.poll() is None:
                    tunnel.terminate()
                    tunnel.wait(timeout=5)
            tunnel_worker.shutdown(wait=True)
            if child.poll() is None:
                child.kill()
                child.wait()


if __name__ == "__main__":
    supervise(sys.argv[1])
