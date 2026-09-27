"""Guest-only control service. Bind loopback; access exclusively through SSH.

No host authority or secrets belong here. Root inside the VM may control this
service, but cannot obtain controller/supervisor credentials from it.
"""

import base64
from collections import deque
import fcntl
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import signal
import stat
import struct
import subprocess
import sys
import termios
import threading
import time
import uuid

LIMIT = 2 * 1024 * 1024
TRANSFER_LIMIT = 64 * 1024 * 1024
HOME = Path("/home/aslice")
IMPORTS = HOME / ".darling/Users/aslice/Imports"
SPOOL = Path("/var/lib/aslice-agent/transfers")
SESSIONS = {}
TRANSFERS = {}
EVENTS = deque(maxlen=2000)
LOCK = threading.RLock()


def event(kind, **fields):
    record = {"time": time.time(), "kind": kind, **fields}
    with LOCK:
        EVENTS.append(record)
    return record


def tail(path, limit=8192):
    if not path.exists():
        return None
    with path.open("rb") as stream:
        stream.seek(max(0, path.stat().st_size - limit))
        return stream.read(limit).decode("utf8", "replace")


def argv(value):
    if (
        not isinstance(value, list)
        or not value
        or len(value) > 256
        or any(
            not isinstance(item, str) or "\x00" in item or len(item) > 32768
            for item in value
        )
    ):
        raise ValueError("expected a bounded argument array")
    return value


class Session:
    def __init__(self, command, account="aslice", mode="darwin", kind="terminal"):
        user = pwd.getpwnam(account)
        command = argv(command)
        if mode == "darwin":
            command = ["/usr/local/bin/darling", "shell", *command]
        elif mode != "linux":
            raise ValueError("execution mode must be darwin or linux")
        self.id = uuid.uuid4().hex
        self.kind, self.mode = kind, mode
        self.master, slave = os.openpty()
        self.data = bytearray()
        self.offset = 0
        self.exit_code = None
        self.lock = threading.Lock()
        self.created = time.time()
        env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": user.pw_dir,
            "USER": account,
            "LOGNAME": account,
            "TERM": "xterm-256color",
            "DISPLAY": ":0",
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "DPREFIX": str(HOME / ".darling"),
            "LANG": "C.UTF-8",
        }
        try:
            self.process = subprocess.Popen(
                [sys.executable, __file__, "--pty", json.dumps(command)],
                stdin=slave,
                stdout=slave,
                stderr=slave,
                start_new_session=True,
                user=user.pw_uid,
                group=user.pw_gid,
                extra_groups=[],
                cwd=user.pw_dir,
                env=env,
            )
        except BaseException:
            os.close(self.master)
            raise
        finally:
            os.close(slave)
        threading.Thread(target=self.capture, daemon=True).start()
        event(
            "process-start",
            session=self.id,
            pid=self.process.pid,
            mode=mode,
            argv=command,
        )

    def capture(self):
        try:
            while True:
                block = os.read(self.master, 65536)
                if not block:
                    break
                with self.lock:
                    self.data.extend(block)
                    excess = max(0, len(self.data) - LIMIT)
                    if excess:
                        del self.data[:excess]
                        self.offset += excess
        except OSError:
            pass
        finally:
            code = self.process.wait()
            with self.lock:
                self.exit_code = code
            event("process-exit", session=self.id, pid=self.process.pid, exit_code=code)

    def read(self, cursor):
        with self.lock:
            start = max(0, min(len(self.data), cursor - self.offset))
            return {
                "id": self.id,
                "pid": self.process.pid,
                "mode": self.mode,
                "kind": self.kind,
                "data": base64.b64encode(self.data[start:]).decode(),
                "cursor": self.offset + len(self.data),
                "truncated": cursor < self.offset,
                "exit_code": self.exit_code,
            }


def safe_file(relative):
    if (
        not isinstance(relative, str)
        or "\\" in relative
        or PurePosixPath(relative).is_absolute()
        or any(part in ("", ".", "..") for part in relative.split("/"))
    ):
        raise ValueError("transfer path must be relative to Imports")
    user = pwd.getpwnam("aslice")
    missing = []
    current = IMPORTS
    while not current.exists():
        missing.append(current)
        current = current.parent
    if current.is_symlink():
        raise ValueError("transfer root contains a link")
    for directory in reversed(missing):
        directory.mkdir(mode=0o755)
        os.chown(directory, user.pw_uid, user.pw_gid)
    path = IMPORTS / relative
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError("transfer links are refused")
        if parent == IMPORTS:
            break
    return path


def transfer_parent(relative):
    """Walk Imports with directory descriptors; guest symlink races cannot redirect root IO."""
    path = safe_file(relative)
    user = pwd.getpwnam("aslice")
    fd = os.open(IMPORTS, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.relative_to(IMPORTS).parts[:-1]:
            try:
                os.mkdir(part, mode=0o755, dir_fd=fd)
                os.chown(
                    part, user.pw_uid, user.pw_gid, dir_fd=fd, follow_symlinks=False
                )
            except FileExistsError:
                pass
            child = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd
            )
            os.close(fd)
            fd = child
        return fd, path.name
    except BaseException:
        os.close(fd)
        raise


def process_identity(directory):
    """Read Linux identity and the innermost PID used by a nested runtime."""
    text = (directory / "stat").read_text()
    fields = text[text.rfind(")") + 2 :].split()
    namespace_pids = []
    for line in (directory / "status").read_text().splitlines():
        if line.startswith("NSpid:"):
            namespace_pids = [int(value) for value in line.split()[1:]]
            break
    return {
        "pid": int(directory.name),
        "ppid": int(fields[1]),
        "namespace_pid": namespace_pids[-1] if len(namespace_pids) > 1 else None,
        "state": fields[0],
        "start": fields[19],
        "command": (directory / "cmdline")
        .read_bytes()[:4096]
        .replace(b"\0", b" ")
        .decode("utf8", "replace"),
    }


def runtime_health(proc=Path("/proc")):
    """Distinguish an active launcher from an observed live Darling server."""
    try:
        result = subprocess.run(
            [
                "systemctl",
                "show",
                "aslice-runtime.service",
                "--property=ActiveState,SubState,Result",
            ],
            capture_output=True,
            timeout=3,
        )
        if result.returncode:
            raise ValueError("runtime service status unavailable")
        service = dict(
            line.split("=", 1)
            for line in result.stdout.decode("utf8", "replace").splitlines()
            if "=" in line
        )
        user = pwd.getpwnam("aslice")
        servers = []
        for directory in proc.glob("[0-9]*"):
            try:
                if directory.stat().st_uid != user.pw_uid:
                    continue
                if (directory / "comm").read_text().strip() != "darlingserver":
                    continue
                servers.append(process_identity(directory))
            except (OSError, IndexError, ValueError):
                continue
        live = any(server["state"] not in ("Z", "X") for server in servers)
        if service.get("ActiveState") == "active":
            state = "server-observed" if live else "server-missing"
        else:
            state = service.get("ActiveState", "unknown")
        return {
            "state": state,
            "service": service,
            "servers": servers,
            "note": "Process observation does not establish runtime responsiveness or compatibility.",
        }
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        return {"state": "unknown", "error": str(error)}


def inspect():
    processes = []
    for path in Path("/proc").glob("[0-9]*/stat"):
        try:
            processes.append(process_identity(path.parent))
        except (OSError, IndexError, ValueError):
            pass

    def command(args):
        result = subprocess.run(args, capture_output=True, timeout=8)
        return result.stdout[:LIMIT].decode("utf8", "replace")

    files = []
    for directory, names, filenames in os.walk(HOME / ".darling", followlinks=False):
        names[:] = [n for n in names if not (Path(directory) / n).is_symlink()]
        for filename in filenames:
            path = Path(directory) / filename
            try:
                item = path.lstat()
                files.append(
                    {
                        "path": str(path.relative_to(HOME / ".darling")),
                        "size": item.st_size,
                        "mtime_ns": item.st_mtime_ns,
                    }
                )
            except OSError:
                pass
            if len(files) >= 10000:
                break
        if len(files) >= 10000:
            break
    return {
        "processes": processes[:4096],
        "services": command(
            ["systemctl", "list-units", "--type=service", "--no-pager", "--plain"]
        ),
        "network": command(["ss", "-ntup"]),
        "files": files,
        "files_truncated": len(files) >= 10000,
        "events": list(EVENTS),
        "runtime": (
            Path("/opt/aslice/runtime.json").read_text()
            if Path("/opt/aslice/runtime.json").exists()
            else None
        ),
        "cpu": Path("/proc/cpuinfo").read_text()[:65536],
    }


def handle(body):
    action = body["action"]
    if action == "logs":
        if __package__:
            from .guest_logs import read
        else:
            from guest_logs import read
        return read(body.get("source", "asl"), pwd.getpwnam("aslice"), HOME)
    if action == "health":
        return {
            "version": 1,
            "darling": Path("/usr/local/bin/darling").exists(),
            "runtime_health": runtime_health(),
            "build_status": (
                Path("/opt/aslice/build-status").read_text()
                if Path("/opt/aslice/build-status").exists()
                else None
            ),
            "build_log": tail(Path("/opt/aslice/build.log")),
            "sessions": [session.read(2**63) for session in SESSIONS.values()],
        }
    if action in ("exec", "shell", "debug"):
        with LOCK:
            if len(SESSIONS) >= 64:
                raise ValueError(
                    "session limit reached; close a finished session first"
                )
            command = body.get("argv", ["/bin/bash", "-l"])
            if action == "debug":
                command = [
                    body.get("lldb")
                    or (
                        "/usr/bin/lldb"
                        if body.get("mode") == "linux"
                        else "/usr/local/libexec/aslice-lldb/lldb"
                    )
                ]
                if body.get("core"):
                    command += ["-c", body["core"]]
                if body.get("attach"):
                    command += ["-p", str(int(body["attach"]))]
                elif body.get("program"):
                    command += ["--", body["program"], *body.get("args", [])]
            session = Session(
                command,
                "aslice-admin" if body.get("admin") else "aslice",
                body.get("mode", "darwin"),
                action,
            )
            SESSIONS[session.id] = session
            return session.read(0)
    if action.startswith("session-"):
        session = SESSIONS[body["session"]]
        if action == "session-read":
            return session.read(max(0, int(body.get("cursor", 0))))
        if action == "session-write":
            data = base64.b64decode(body["data"], validate=True)
            if len(data) > 65536:
                raise ValueError("terminal input exceeds 64 KiB")
            os.write(session.master, data)
        elif action == "session-resize":
            rows, cols = int(body["rows"]), int(body["cols"])
            if not 1 <= rows <= 500 or not 1 <= cols <= 1000:
                raise ValueError("invalid terminal size")
            fcntl.ioctl(
                session.master,
                termios.TIOCSWINSZ,
                struct.pack("HHHH", rows, cols, 0, 0),
            )
        elif action == "session-close":
            disposition = body.get("disposition")
            if session.kind == "debug" and disposition not in ("detach", "terminate"):
                raise ValueError("debugger close requires detach or terminate")
            if session.process.poll() is None:
                if session.kind == "debug":
                    os.write(
                        session.master,
                        (
                            b"process detach\nquit\n"
                            if disposition == "detach"
                            else b"process kill\nquit\n"
                        ),
                    )
                    return {
                        "acknowledged": True,
                        "observed": False,
                        "note": "read debugger output to confirm disposition",
                    }
                os.killpg(session.process.pid, signal.SIGTERM)
                return {"acknowledged": True}
            os.close(session.master)
            del SESSIONS[session.id]
        else:
            raise ValueError("unknown session action")
        return {"acknowledged": True}
    if action == "inspect":
        return inspect()
    if action == "import-begin":
        with LOCK:
            if len(TRANSFERS) >= 8:
                raise ValueError("transfer limit reached")
            total = int(body["size"])
            if not 0 <= total <= TRANSFER_LIMIT or not re.fullmatch(
                "[0-9a-f]{64}", body["sha256"]
            ):
                raise ValueError("invalid transfer identity or size (maximum 64 MiB)")
            destination = safe_file(body["path"])
            if destination.exists():
                raise ValueError("destination already exists")
            ident = uuid.uuid4().hex
            spool = SPOOL
            spool.mkdir(mode=0o700, parents=True, exist_ok=True)
            temporary = spool / ident
            temporary.touch(mode=0o600, exist_ok=False)
            TRANSFERS[ident] = {
                "path": destination,
                "temporary": temporary,
                "size": total,
                "sha256": body["sha256"],
                "offset": 0,
                "executable": bool(body.get("executable")),
            }
            return {"transfer": ident, "offset": 0}
    if action.startswith("import-"):
        with LOCK:
            transfer = TRANSFERS[body["transfer"]]
            if action == "import-abort":
                transfer["temporary"].unlink(missing_ok=True)
                del TRANSFERS[body["transfer"]]
                return {"aborted": True}
            if action == "import-chunk":
                chunk = base64.b64decode(body["data"], validate=True)
                if (
                    len(chunk) > 262144
                    or body["offset"] != transfer["offset"]
                    or transfer["offset"] + len(chunk) > transfer["size"]
                ):
                    raise ValueError("invalid chunk size or offset")
                with transfer["temporary"].open("ab") as stream:
                    stream.write(chunk)
                transfer["offset"] += len(chunk)
                return {"offset": transfer["offset"]}
            if action != "import-commit":
                raise ValueError("unknown import action")
            with transfer["temporary"].open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
                os.fsync(stream.fileno())
            if digest != transfer["sha256"] or transfer["offset"] != transfer["size"]:
                raise ValueError("incomplete transfer or hash mismatch")
            # Recheck links after upload; guest apps must not redirect root writes.
            relative = str(transfer["path"].relative_to(IMPORTS))
            parent, filename = transfer_parent(relative)
            user = pwd.getpwnam("aslice")
            os.chown(transfer["temporary"], user.pw_uid, user.pw_gid)
            transfer["temporary"].chmod(0o755 if transfer["executable"] else 0o644)
            # link creates the name exclusively; unlike replace it never clobbers.
            try:
                os.link(
                    transfer["temporary"],
                    filename,
                    dst_dir_fd=parent,
                    follow_symlinks=False,
                )
                os.fsync(parent)
            finally:
                os.close(parent)
            transfer["temporary"].unlink()
            del TRANSFERS[body["transfer"]]
            return event("import", path=relative, sha256=digest, observed=True)
    if action == "export":
        parent, filename = transfer_parent(body["path"])
        try:
            fd = os.open(
                filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent
            )
        finally:
            os.close(parent)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            size = info.st_size
            if not stat.S_ISREG(info.st_mode) or size > TRANSFER_LIMIT:
                raise ValueError("export exceeds limit or is not a regular file")
            offset = int(body.get("offset", 0))
            if not 0 <= offset <= size:
                raise ValueError("invalid export offset")
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
            stream.seek(offset)
            data = stream.read(262144)
        return {
            "size": size,
            "sha256": digest,
            "offset": offset,
            "data": base64.b64encode(data).decode(),
        }
    if action == "fault":
        kind = body["kind"]
        placed = event("fault-request", fault=kind, operation=body.get("operation"))
        if kind == "process":
            pid = int(body["pid"])
            if pid <= 1 or pid == os.getpid():
                raise ValueError("refusing agent/init termination")
            text = Path(f"/proc/{pid}/stat").read_text()
            if text[text.rfind(")") + 2 :].split()[19] != str(body["start"]):
                raise ValueError("process identity changed")
            os.kill(pid, signal.SIGKILL)
        elif kind == "service":
            service = body["service"]
            if not re.fullmatch(r"[a-zA-Z0-9_.@-]+\.service", service):
                raise ValueError("invalid guest service name")
            subprocess.run(["systemctl", "stop", service], check=True, timeout=10)
        elif kind in ("disk-full", "disk-clear"):
            target = IMPORTS / "fault-disk"
            target.mkdir(exist_ok=True)
            if target.is_symlink():
                raise ValueError("fault directory is a link")
            if kind == "disk-clear":
                subprocess.run(["umount", str(target)], check=True, timeout=10)
            else:
                size = int(body.get("mib", 64))
                if not 16 <= size <= 512:
                    raise ValueError("fault disk must be 16-512 MiB")
                subprocess.run(
                    [
                        "mount",
                        "-t",
                        "tmpfs",
                        "-o",
                        f"size={size}m,mode=0777",
                        "aslice-fault",
                        str(target),
                    ],
                    check=True,
                    timeout=10,
                )
                with (target / "filler").open("wb") as stream:
                    os.posix_fallocate(stream.fileno(), 0, size * 1024 * 1024)
        else:
            raise ValueError("unsupported guest fault")
        return event("fault-acknowledged", fault=kind, request=placed, observed=False)
    raise ValueError("unknown guest action")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        token = Path("/etc/aslice-agent.token").read_text().strip()
        if not hmac.compare_digest(
            self.headers.get("Authorization", ""), "Bearer " + token
        ):
            self.send_error(403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if self.path != "/v1" or not 0 < length <= 1024 * 1024:
                raise ValueError("invalid request")
            result = handle(json.loads(self.rfile.read(length)))
            code = 200
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            result, code = {"error": str(error)}, 400
        encoded = json.dumps(result).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--pty"]:
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        command = argv(json.loads(sys.argv[2]))
        os.execvpe(command[0], command, os.environ)
    else:
        # Incomplete transfers never become application files after agent restart.
        # Retain their root-owned bytes for diagnosis; no stale IDs are resumable.
        ThreadingHTTPServer(("127.0.0.1", 9971), Handler).serve_forever()
