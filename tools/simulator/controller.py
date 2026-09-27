"""Authenticated loopback API used by both the CLI and graphical console."""

import asyncio
import base64
from collections import deque
import hmac
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import threading
import urllib.request
import uuid
import zipfile

from .darwin import Machines, BACKEND, no_links, name
from .model import atomic_json
from . import vm

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "build/simulator-web"


def request(root, action, *, _timeout=180, **values):
    config = json.loads((Path(root) / ".controller/endpoint.json").read_text())
    req = urllib.request.Request(
        f'http://127.0.0.1:{config["port"]}/v1/action',
        data=json.dumps({"action": action, **values}).encode(),
        headers={
            "Authorization": "Bearer " + config["token"],
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_timeout) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        try:
            message = json.load(error).get("error", str(error))
        finally:
            error.close()
        raise ValueError(message) from error
    return result


def ensure(root):
    root = no_links(root)
    try:
        request(root, "ping", _timeout=2)
        return root
    except (OSError, ValueError):
        pass
    with Machines(root):
        directory = root / ".controller"
        directory.mkdir(exist_ok=True)
        vm.private(directory)
    # The controller's OS lease resolves simultaneous starts without duplicate
    # authority. A contender exits before binding/listening or spawning VMs.
    with (directory / "startup.log").open("ab") as log:
        child = vm.detached(
            [sys.executable, "-m", "tools.simulator.controller", str(root)], log
        )
    deadline = time.monotonic() + 15
    try:
        while time.monotonic() < deadline:
            try:
                request(root, "ping", _timeout=2)
                threading.Thread(target=child.wait, daemon=True).start()
                return root
            except (OSError, ValueError):
                time.sleep(0.1)
        raise ValueError("controller failed to start; inspect .controller/startup.log")
    except BaseException:
        # Only reap the process created by this attempt, never a saved PID.
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        raise


class Controller:
    def __init__(self, root):
        self.root = Path(root)
        self.token = secrets.token_urlsafe(32)
        self.lock = asyncio.Lock()
        self.tunnels = {}
        self.timeline = deque(maxlen=2000)
        self.baselines = {}
        self.builders = {}
        self.stopping = asyncio.Event()

    def directory(self, machine):
        return self.root / "machines" / name(machine)

    def event(self, kind, machine=None, **values):
        event = {
            "version": 1,
            "id": uuid.uuid4().hex,
            "time": time.time(),
            "kind": kind,
            "machine": machine,
            **values,
        }
        self.timeline.append(event)
        directory = self.root / ".controller"
        path = directory / "timeline.jsonl"
        if path.exists() and path.stat().st_size > 2**20:
            os.replace(path, directory / "timeline.previous.jsonl")
        with path.open("a", encoding="utf8") as stream:
            stream.write(json.dumps(event) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return event

    def status(self, machine=None):
        with Machines(self.root) as store:
            result = store.status(machine)
            entries = [result] if machine else result["machines"]
            for data in entries:
                directory = store.directory(data["name"])
                if vm.owned(directory):
                    try:
                        state = json.loads((directory / "vm-state.json").read_text())
                        data.update(
                            state=state["state"],
                            accelerator=state.get("accelerator"),
                            supervisor_alive=True,
                        )
                    except (OSError, ValueError):
                        data.update(state="starting", supervisor_alive=True)
                elif data["state"] in ("running", "starting", "stopping"):
                    # The supervisor lifetime job/PDEATHSIG has ended. Never
                    # signal a saved numeric PID: it may already be reused.
                    data.update(
                        state="stopped",
                        supervisor_alive=False,
                        last_exit="uncertain; supervisor lease released",
                    )
                    atomic_json(directory / "machine.json", data)
            return result

    async def tunnel(self, machine):
        directory = self.directory(machine)
        if not vm.owned(directory):
            raise ValueError("machine is not running")
        state = json.loads((directory / "vm-state.json").read_text())
        result = await asyncio.to_thread(vm.request, directory, "tunnel")
        current = {
            **result["result"],
            "token": (directory / "control/guest-token").read_text().strip(),
            "operation": state["operation"],
        }
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            try:
                reader, writer = await asyncio.open_connection(
                    "127.0.0.1", current["agent_port"]
                )
                writer.close()
                await writer.wait_closed()
                return current
            except OSError:
                await asyncio.sleep(0.05)
        raise ValueError("SSH tunnel did not become ready; inspect control/ssh.log")

    async def guest(self, machine, body):
        import aiohttp

        tunnel = await self.tunnel(machine)
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        ) as session:
            async with session.post(
                f'http://127.0.0.1:{tunnel["agent_port"]}/v1',
                json=body,
                headers={"Authorization": "Bearer " + tunnel["token"]},
            ) as response:
                raw = bytearray()
                async for block in response.content.iter_chunked(65536):
                    raw.extend(block)
                    if len(raw) > 8 * 1024 * 1024:
                        raise ValueError("guest response exceeds 8 MiB")
                result = json.loads(raw)
                if response.status != 200 or "error" in result:
                    raise ValueError(result.get("error", "guest error"))
                return result

    async def action(self, body):
        action, machine = body["action"], body.get("name")
        if action == "ping":
            return {"version": 1, "backend": BACKEND}
        if action == "controller-stop":
            # Supervisors own machines and sessions independently of this API.
            asyncio.get_running_loop().call_later(0.1, self.stopping.set)
            return {"stopping": True, "machines": "preserved"}
        if action.startswith("provision"):
            from . import provision

            directory = self.root / ".provisioning" / name(machine)
            if action == "provision":
                return await asyncio.to_thread(
                    provision.begin,
                    directory,
                    body.get("acceleration", "auto"),
                    body.get("cloud_image"),
                )
            if not directory.exists():
                raise ValueError("unknown provisioning builder")
            state = json.loads((directory / "preparation.json").read_text())
            if not vm.owned(directory):
                return state
            if machine not in self.builders:
                builder = Controller(self.root)
                builder.directory = lambda unused: directory
                self.builders[machine] = builder
            builder = self.builders[machine]
            if action == "provision-status":
                health = await builder.guest(machine, {"action": "health"})
                return {**state, "guest": health}
            if action == "provision-stop":
                return await asyncio.to_thread(vm.request, directory, "stop")
            if action == "provision-finalize":
                observed = await builder.guest(machine, {"action": "inspect"})
                if not observed.get("runtime"):
                    raise ValueError("guest build has no completed runtime identity")
                identity = json.loads(observed["runtime"])
                await asyncio.to_thread(vm.request, directory, "stop")
                deadline = time.monotonic() + 60
                while vm.owned(directory) and time.monotonic() < deadline:
                    await asyncio.sleep(0.2)
                if vm.owned(directory):
                    raise ValueError("builder has not shut down; finalization refused")
                target = directory / "base.qcow2"
                if target.exists():
                    raise ValueError("base output already exists")
                await asyncio.to_thread(
                    subprocess.run,
                    [
                        "qemu-img",
                        "convert",
                        "-O",
                        "qcow2",
                        str(directory / "disk.qcow2"),
                        str(target),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=180,
                )
                atomic_json(directory / "runtime.json", identity)
                state.update(
                    state="ready",
                    image=str(target),
                    runtime=str(directory / "runtime.json"),
                )
                atomic_json(directory / "preparation.json", state)
                return state
            raise ValueError("unknown provisioning action")
        if action == "timeline":
            query = body.get("query", "").lower()
            return {
                "events": [
                    e
                    for e in self.timeline
                    if (not machine or e["machine"] == machine)
                    and query in json.dumps(e).lower()
                ]
            }
        if action == "status":
            return await asyncio.to_thread(self.status, machine)
        if action in ("create", "clone", "delete", "snapshot", "start"):
            async with self.lock:
                if action != "create":
                    await asyncio.to_thread(self.status, machine)

                def mutate():
                    with Machines(self.root) as store:
                        if action == "create":
                            return store.create(
                                machine,
                                Path(body["image"]),
                                Path(body["runtime"]),
                                body.get("cpus", 4),
                                body.get("memory_mib", 8192),
                                body.get("disk_gib", 64),
                            )
                        if action == "clone":
                            return store.clone(machine, body["destination"])
                        if action == "delete":
                            return store.delete(machine)
                        if action == "snapshot":
                            return store.snapshot(
                                machine,
                                body["snapshot"],
                                body.get("operation") == "restore",
                            )
                        return vm.start(
                            store,
                            machine,
                            body.get("acceleration", "auto"),
                            body.get("network", False),
                        )

                result = await asyncio.to_thread(mutate)
            self.event(action, machine, outcome="acknowledged", result=result)
            return result
        if action in ("stop", "serial", "network"):
            command = "force" if action == "stop" and body.get("force") else action
            result = await asyncio.to_thread(
                vm.request, self.directory(machine), command, up=body.get("up", False)
            )
            self.event(
                action,
                machine,
                outcome="acknowledged",
                observed=False,
                forced=bool(body.get("force")),
            )
            if action == "stop":
                deadline = time.monotonic() + min(60, int(body.get("timeout", 30)))
                while vm.owned(self.directory(machine)) and time.monotonic() < deadline:
                    await asyncio.sleep(0.2)
                return {
                    "request": result,
                    "status": await asyncio.to_thread(self.status, machine),
                    "observed": not vm.owned(self.directory(machine)),
                }
            return result
        if action == "diagnostics":
            state = await asyncio.to_thread(self.status, machine)
            output = io.BytesIO()
            with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("machine.json", json.dumps(state, indent=2))
                archive.writestr(
                    "timeline.json", json.dumps(list(self.timeline), indent=2)
                )
                for path in (self.directory(machine) / "evidence").glob("*.log*"):
                    archive.writestr("logs/" + path.name, path.read_bytes()[-(2**20) :])
                try:
                    archive.writestr(
                        "guest.json",
                        json.dumps(await self.guest(machine, {"action": "inspect"})),
                    )
                except (OSError, ValueError) as error:
                    archive.writestr("guest-error.txt", str(error))
            return {
                "archive": base64.b64encode(output.getvalue()).decode(),
                "format": "zip",
                "credentials_included": False,
            }
        if action == "inspect":
            result = await self.guest(machine, {"action": "inspect"})
            current = {item["path"]: item for item in result["files"]}
            previous = self.baselines.get(machine, {})
            result["changes"] = {
                "added": sorted(current.keys() - previous.keys()),
                "removed": sorted(previous.keys() - current.keys()),
                "modified": sorted(
                    key
                    for key in current.keys() & previous.keys()
                    if current[key] != previous[key]
                ),
                "baseline": "previous inspection in this controller; metadata comparison only",
            }
            self.baselines[machine] = current
            return result
        if action == "scenario":
            steps = body["steps"]
            if not isinstance(steps, list) or len(steps) > 100:
                raise ValueError("scenario exceeds 100 steps")
            results = []
            allowed = {
                "exec",
                "shell",
                "debug",
                "session-read",
                "session-write",
                "session-close",
                "inspect",
                "fault",
                "network",
            }
            for step in steps:
                if step.get("action") not in allowed:
                    raise ValueError("unsupported scenario action")
                results.append(await self.action({**step, "name": machine}))
            previous = body.get("previous", [])
            record = {
                "version": 1,
                "machine": machine,
                "steps": steps,
                "results": results,
                "deterministic": False,
                "differences": [
                    i
                    for i, result in enumerate(results)
                    if i >= len(previous) or result != previous[i]
                ],
            }
            path = (
                self.directory(machine)
                / "evidence"
                / ("scenario-" + uuid.uuid4().hex + ".json")
            )
            atomic_json(path, record)
            return record
        allowed = {
            "logs",
            "health",
            "exec",
            "shell",
            "debug",
            "session-read",
            "session-write",
            "session-resize",
            "session-close",
            "import-begin",
            "import-chunk",
            "import-commit",
            "import-abort",
            "export",
            "fault",
        }
        if action not in allowed:
            raise ValueError("unknown API action")
        result = await self.guest(machine, body)
        if action not in (
            "logs",
            "session-read",
            "session-write",
            "session-resize",
            "import-chunk",
            "export",
            "health",
        ):
            self.event(
                action,
                machine,
                outcome="acknowledged",
                session=result.get("id"),
                observed=result.get("observed", False),
            )
        return result


async def serve(root):
    from aiohttp import web, WSMsgType

    controller = Controller(root)
    control = Path(root) / ".controller"
    for path in (control / "timeline.previous.jsonl", control / "timeline.jsonl"):
        if path.exists():
            for line in path.read_text().splitlines():
                try:
                    controller.timeline.append(json.loads(line))
                except ValueError:
                    pass

    def authorized(request):
        supplied = request.headers.get("Authorization", "").removeprefix("Bearer ")
        if not supplied:
            supplied = request.cookies.get("aslice-control", "")
        return hmac.compare_digest(supplied, controller.token)

    @web.middleware
    async def security(request, handler):
        expected = f'127.0.0.1:{request.transport.get_extra_info("sockname")[1]}'
        if request.host != expected:
            raise web.HTTPForbidden(text="invalid Host")
        origin = request.headers.get("Origin")
        if origin and origin != "http://" + expected:
            raise web.HTTPForbidden(text="invalid Origin")
        if request.path.startswith("/v1/") and not authorized(request):
            raise web.HTTPForbidden(text="authentication required")
        try:
            response = await handler(request)
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            response = web.json_response({"error": str(error)}, status=400)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self' ws:; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'"
        )
        return response

    async def auth(request):
        response = web.json_response({"version": 1})
        response.set_cookie(
            "aslice-control",
            controller.token,
            httponly=True,
            samesite="Strict",
            path="/",
        )
        return response

    async def action(request):
        body = await request.json()
        quiet = body.get("action") in (
            "logs",
            "ping",
            "status",
            "timeline",
            "session-read",
            "session-write",
            "session-resize",
            "health",
            "export",
            "import-chunk",
        )
        if not quiet:
            controller.event(
                "request",
                body.get("name"),
                action=body.get("action"),
                outcome="requested",
            )
        try:
            result = await controller.action(body)
        except Exception as error:
            if not quiet:
                controller.event(
                    "request-error",
                    body.get("name"),
                    action=body.get("action"),
                    outcome="failed or uncertain",
                    error=str(error),
                )
            raise
        return web.json_response(result)

    async def vnc(request):
        tunnel = await controller.tunnel(request.match_info["machine"])
        reader, writer = await asyncio.open_connection("127.0.0.1", tunnel["vnc_port"])
        socket = web.WebSocketResponse(max_msg_size=2**20, heartbeat=20)
        await socket.prepare(request)

        async def upstream():
            while block := await reader.read(65536):
                await socket.send_bytes(block)
            await socket.close()

        task = asyncio.create_task(upstream())
        try:
            async for message in socket:
                if message.type == WSMsgType.BINARY:
                    writer.write(message.data)
                    await writer.drain()
        finally:
            task.cancel()
            writer.close()
            await writer.wait_closed()
        return socket

    async def index(request):
        if not all(
            (WEB / filename).is_file()
            for filename in ("index.html", "app.js", "app.css")
        ):
            raise web.HTTPServiceUnavailable(
                text="Console assets are missing. Run npm ci and npm run build in tools/simulator/web."
            )
        return web.FileResponse(WEB / "index.html")

    async def asset(request):
        path = (WEB / request.match_info["path"]).resolve()
        if not path.is_relative_to(WEB.resolve()) or not path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(path)

    app = web.Application(middlewares=[security], client_max_size=1024 * 1024)
    app.router.add_post("/v1/auth", auth)
    app.router.add_post("/v1/action", action)
    app.router.add_get("/v1/vnc/{machine}", vnc)
    app.router.add_get("/", index)
    app.router.add_get("/static/{path:.*}", asset)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    atomic_json(
        control / "endpoint.json",
        {"version": 1, "port": port, "token": controller.token, "pid": os.getpid()},
    )
    vm.private(control / "endpoint.json")
    try:
        await controller.stopping.wait()
    finally:
        await runner.cleanup()
        endpoint = control / "endpoint.json"
        if endpoint.exists() and json.loads(endpoint.read_text()).get("token") == controller.token:
            endpoint.unlink()


if __name__ == "__main__":
    root = Path(sys.argv[1]).resolve()
    os.chdir(ROOT)
    with vm.Lease(root / ".controller/lease"):
        asyncio.run(serve(root))
