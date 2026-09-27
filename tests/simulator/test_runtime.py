"""Real controller security/lifetime tests; these do not claim Darling compatibility."""

import importlib.util
import asyncio
import base64
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.simulator import controller, vm
from tools.simulator.darwin import Machines
from tools.simulator.model import atomic_json


class SourceInventoryTests(unittest.TestCase):
    def test_installed_tools_do_not_change_source_evidence(self):
        from tools.simulator import harness, requirements

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for filename in ("CMakeLists.txt", "CMakePresets.json", "vcpkg.json"):
                (root / filename).write_text("fixture")
            web = root / "tools/simulator/web"
            web.mkdir(parents=True)
            (web / "app.js").write_text("original source")
            with patch.object(harness, "ROOT", root), patch.object(
                harness.shutil, "which", return_value=None
            ):
                before = harness.source_identity()
                package = web / "node_modules/development-tool"
                package.mkdir(parents=True)
                (package / "README.md").write_text("installed dependency")
                self.assertEqual(before, harness.source_identity())
                self.assertEqual(requirements.inventory(root), {})
                (web / "app.js").write_text("changed source")
                self.assertNotEqual(before, harness.source_identity())


@unittest.skipUnless(importlib.util.find_spec("aiohttp"), "aiohttp unavailable")
class GuestResponseTests(unittest.IsolatedAsyncioTestCase):
    async def test_fragmented_guest_response(self):
        from aiohttp import web

        async def respond(request):
            response = web.StreamResponse()
            await response.prepare(request)
            for part in (b'{"value":', b'"fragmented"', b"}"):
                await response.write(part)
                await asyncio.sleep(0.02)
            await response.write_eof()
            return response

        application = web.Application()
        application.router.add_post("/v1", respond)
        runner = web.AppRunner(application)
        await runner.setup()
        self.addAsyncCleanup(runner.cleanup)
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        with tempfile.TemporaryDirectory() as temporary:
            client = controller.Controller(temporary)

            async def tunnel(machine):
                return {"agent_port": port, "token": "guest-only-test-token"}

            client.tunnel = tunnel
            self.assertEqual(
                await client.guest("probe", {"action": "health"}),
                {"value": "fragmented"},
            )


class QemuCommandTests(unittest.TestCase):
    def test_isolation_and_explicit_software_emulation(self):
        config = {
            "name": "test",
            "uuid": "test-id",
            "disk": "/path/with,comma and space/disk.qcow2",
            "acceleration": "tcg",
            "cpus": 4,
            "memory_mib": 8192,
            "ssh_port": 43210,
            "network": False,
        }
        command = vm.qemu_command(config)
        self.assertIn("stdio", command)
        self.assertNotIn("-virtfs", command)
        self.assertNotIn("-fsdev", command)
        self.assertNotIn("-vnc", command)
        self.assertNotIn("-usb", command)
        self.assertEqual(command[command.index("-accel") + 1], "tcg")
        blocks = [command[i + 1] for i, arg in enumerate(command) if arg == "-blockdev"]
        self.assertEqual(json.loads(blocks[0])["file"]["filename"], config["disk"])
        networks = [command[i + 1] for i, arg in enumerate(command) if arg == "-netdev"]
        self.assertTrue(all("restrict=on" in net for net in networks))
        self.assertIn("hostfwd=tcp:127.0.0.1:43210-:22", networks[0])


@unittest.skipUnless(
    importlib.util.find_spec("aiohttp"),
    "install tools/simulator/runtime-requirements.txt for controller integration",
)
class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "store"
        with Machines(self.root):
            (self.root / ".controller").mkdir()
        self.process = subprocess.Popen(
            [sys.executable, "-m", "tools.simulator.controller", str(self.root)],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        self.addCleanup(self.cleanup)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                self.fail(self.process.stderr.read().decode())
            try:
                controller.request(self.root, "ping")
                break
            except (OSError, ValueError):
                time.sleep(0.05)
        else:
            self.fail("controller did not start")
        self.endpoint = json.loads(
            (self.root / ".controller/endpoint.json").read_text()
        )
        self.url = f'http://127.0.0.1:{self.endpoint["port"]}'

    def cleanup(self):
        if self.process.poll() is None:
            self.process.terminate()
        self.process.communicate(timeout=10)
        self.temporary.cleanup()

    def test_auth_host_origin_and_versioned_api(self):
        self.assertEqual(controller.request(self.root, "ping")["version"], 1)
        headers = {"Content-Type": "application/json"}

        def refused(extra):
            request = urllib.request.Request(
                self.url + "/v1/action",
                data=b'{"action":"status"}',
                headers={**headers, **extra},
            )
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(request)
            self.assertEqual(error.exception.code, 403)
            error.exception.close()

        refused({})
        refused({"Authorization": "Bearer wrong"})
        authorization = {"Authorization": "Bearer " + self.endpoint["token"]}
        refused({**authorization, "Origin": "https://untrusted.example"})
        refused({**authorization, "Host": "untrusted.example"})
        if (controller.WEB / "index.html").is_file():
            with urllib.request.urlopen(self.url + "/") as response:
                self.assertIn(b"Darwin compatibility", response.read())
                self.assertIn(
                    "frame-ancestors 'none'",
                    response.headers["Content-Security-Policy"],
                )
        else:
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(self.url + "/")
            self.assertEqual(error.exception.code, 503)
            self.assertIn(b"npm run build", error.exception.read())
            error.exception.close()
        self.assertEqual(controller.request(self.root, "status")["machines"], [])

    @unittest.skipUnless(
        importlib.util.find_spec("playwright"), "Playwright unavailable"
    )
    def test_built_console_loads_offline_and_keeps_display_input_clear(self):
        from playwright.sync_api import sync_playwright

        if not (controller.WEB / "index.html").is_file():
            self.skipTest("run npm ci and npm run build in tools/simulator/web")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1400})
            errors = []
            external = []
            page.on("pageerror", lambda error: errors.append(error.stack))

            def restrict_network(route):
                if route.request.url.startswith(self.url + "/"):
                    route.continue_()
                else:
                    external.append(route.request.url)
                    route.abort()

            page.route("**/*", restrict_network)
            page.goto(self.url + "/#" + self.endpoint["token"])
            page.wait_for_function(
                "() => document.querySelector('#notice').textContent.startsWith('Connected')"
            )
            page.locator("#terminal .xterm-screen").wait_for()
            for width in (1600, 1100, 700):
                with self.subTest(width=width):
                    page.set_viewport_size({"width": width, "height": 1400})
                    display = page.locator("#display")
                    display.scroll_into_view_if_needed()
                    self.assertTrue(display.evaluate("""element => {
                        const bounds = element.getBoundingClientRect();
                        for (const x of [5, 40, bounds.width / 2]) {
                            for (const y of [40, 80, 160]) {
                                const hit = document.elementFromPoint(bounds.x + x, bounds.y + y);
                                if (!element.contains(hit)) return false;
                            }
                        }
                        return true;
                    }"""))
            self.assertEqual(errors, [])
            self.assertEqual(external, [])
            browser.close()

    @unittest.skipUnless(
        importlib.util.find_spec("playwright"), "Playwright unavailable"
    )
    def test_console_terminal_addons(self):
        """Browser rendering against sample API data; not runtime acceptance."""
        from playwright.sync_api import sync_playwright, expect

        if not (controller.WEB / "index.html").is_file():
            self.skipTest("run npm ci and npm run build in tools/simulator/web")
        machine = {
            "name": "sample",
            "state": "running",
            "cpus": 4,
            "memory_mib": 8192,
            "disk_gib": 64,
            "base": "sample",
            "runtime_sha256": "sample",
            "capabilities": {},
        }
        session = {
            "id": "sample-session",
            "pid": 42,
            "kind": "terminal",
            "mode": "linux",
            "exit_code": None,
        }
        payload = (
            "Terminal addon proof: 漢字 😀\r\n"
            "\x1b]9;4;1;42\x07"
            '\x1bPq"1;1;10;6#0;2;100;0;0#0!10~\x1b\\'
        ).encode()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1400})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))

            def sample_action(route):
                body = route.request.post_data_json
                action = body["action"]
                if action == "status":
                    result = {"machines": [machine]}
                elif action == "shell":
                    result = session
                elif action == "health":
                    result = {"sessions": [session]}
                elif action == "session-read":
                    result = {
                        **session,
                        "cursor": len(payload),
                        "truncated": False,
                        "data": base64.b64encode(
                            payload if body["cursor"] == 0 else b""
                        ).decode(),
                    }
                else:
                    self.assertEqual(action, "session-resize")
                    result = {}
                route.fulfill(json=result)

            page.route("**/v1/action", sample_action)
            page.goto(self.url + "/#" + self.endpoint["token"])
            expect(page.locator("#notice")).to_contain_text("Connected")
            page.get_by_text("Terminal options", exact=True).click()
            page.locator("#terminal-webgl").uncheck()
            expect(page.locator("#terminal-renderer")).to_have_text("Standard renderer")
            page.locator("#terminal-images").check()
            expect(page.locator("#terminal-image-status")).to_contain_text(
                "Inline images enabled"
            )
            page.locator("#shell").click()
            expect(page.locator("#terminal-progress-label")).to_have_text(
                "Program reports progress: 42%"
            )
            expect(page.locator("#terminal")).to_contain_text("Terminal addon proof")
            page.wait_for_function("""() => {
                const canvases = document.querySelectorAll('#terminal canvas');
                return [...canvases].some(canvas => {
                    const context = canvas.getContext('2d');
                    if (!context) return false;
                    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
                    for (let i = 0; i < pixels.length; i += 4) {
                        if (pixels[i] > 200 && pixels[i + 1] < 30 && pixels[i + 2] < 30) return true;
                    }
                    return false;
                });
            }""")
            with page.expect_download() as received:
                page.locator("#terminal-export").click()
            snapshot = json.loads(
                Path(received.value.path()).read_text(encoding="utf-8")
            )
            self.assertEqual(snapshot["kind"], "terminal-display")
            self.assertEqual(snapshot["unicodeVersion"], "11")
            self.assertIn("漢字 😀", snapshot["data"])
            page.locator("#terminal-webgl").check()
            page.wait_for_function("""() => {
                const status = document.getElementById('terminal-renderer').textContent;
                return status === 'WebGL renderer' || status.includes('unavailable');
            }""")
            if page.locator("#terminal-renderer").inner_text() == "WebGL renderer":
                page.evaluate("""() => {
                    for (const canvas of document.querySelectorAll('#terminal canvas')) {
                        const context = canvas.getContext('webgl2');
                        context?.getExtension('WEBGL_lose_context')?.loseContext();
                    }
                }""")
                expect(page.locator("#terminal-renderer")).to_contain_text(
                    "GPU context lost", timeout=10000
                )
            page.locator("#terminal-images").uncheck()
            expect(page.locator("#terminal-image-status")).to_have_text(
                "Images disabled"
            )
            self.assertEqual(errors, [])
            browser.close()

    @unittest.skipUnless(
        importlib.util.find_spec("playwright"), "Playwright unavailable"
    )
    def test_legacy_browser_vnc_rendering_and_input(self):
        from playwright.sync_api import sync_playwright, expect
        from vnc_fixture import display_server

        if not (controller.WEB / "index.html").is_file():
            self.skipTest("build the console first")
        machine = {
            "name": "sample",
            "state": "running",
            "cpus": 4,
            "memory_mib": 8192,
            "disk_gib": 64,
            "base": "sample",
            "runtime_sha256": "sample",
            "capabilities": {},
        }
        with display_server(controller.WEB, machine) as (
            url,
            peers,
        ), sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1000})
            page.add_init_script(path=str(ROOT / "tests/simulator/legacy_browser.js"))
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url)
            expect(page.locator("#notice")).to_contain_text("Connected")
            page.locator("#display-connect").click()
            expect(page.locator("#display-status")).to_contain_text("Connected")
            page.wait_for_function("""() => {
                const canvas = document.querySelector('#display canvas');
                if (!canvas) return false;
                const pixel = canvas.getContext('2d').getImageData(1, 1, 1, 1).data;
                return pixel[0] === 0x33 && pixel[1] === 0x66 && pixel[2] === 0x99;
            }""")
            page.locator("#display canvas").click(position={"x": 10, "y": 10})
            page.keyboard.press("a")
            page.locator("#dark-appearance").click()
            page.locator("#display-disconnect").click()
            self.assertTrue(any(packet[0] == 4 for packet in peers[0].inputs))
            self.assertTrue(any(packet[0] == 5 for packet in peers[0].inputs))
            self.assertEqual(errors, [])
            browser.close()

    def test_concurrent_controller_cannot_replace_authority(self):
        peer = subprocess.Popen(
            [sys.executable, "-m", "tools.simulator.controller", str(self.root)],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        peer.communicate(timeout=10)
        self.assertNotEqual(peer.returncode, 0)
        self.assertEqual(
            json.loads((self.root / ".controller/endpoint.json").read_text()),
            self.endpoint,
        )
        self.assertEqual(controller.request(self.root, "ping")["version"], 1)

    def test_invalid_machine_and_requests_do_not_create_state(self):
        with self.assertRaises(ValueError):
            controller.request(self.root, "start", name="../escape")
        with self.assertRaises(ValueError):
            controller.request(self.root, "unknown")
        self.assertEqual(controller.request(self.root, "status")["machines"], [])


class SupervisorLifetimeTests(unittest.TestCase):
    def test_controller_independent_owner_and_supervisor_crash(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "control").mkdir()
            (directory / "evidence").mkdir()
            fake = directory / "fake_qemu.py"
            fake.write_text("""import json,sys,time
print(json.dumps({'QMP': {}}),flush=True)
for line in sys.stdin:
 r=json.loads(line)
 result={'status':'running'} if r['execute']=='query-status' else {}
 print(json.dumps({'return':result,'id':r['id']}),flush=True)
 if r['execute']=='quit': sys.exit(0)
while True: time.sleep(1)
""")
            atomic_json(
                directory / "control/launch.json",
                {
                    "token": "test-token",
                    "operation": "test-operation",
                    "ssh_port": 12345,
                    "acceleration": "tcg",
                },
            )
            script = """
import os
import subprocess
import sys
from tools.simulator import vm


def fake_tunnel(directory, port):
    parent = os.getpid()
    options = {}
    if os.name != 'nt':
        options['preexec_fn'] = lambda: vm.parent_death(parent)
    child = subprocess.Popen(
        [sys.executable, '-c', 'import time; time.sleep(60)'],
        **options,
    )
    return child, {'agent_port': child.pid, 'vnc_port': child.pid}


vm.ssh_tunnel = fake_tunnel
vm.qemu_command = lambda config: [sys.executable, sys.argv[2]]
vm.supervise(sys.argv[1])
"""
            process = subprocess.Popen(
                [sys.executable, "-c", script, str(directory), str(fake)],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            try:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        self.fail(process.stderr.read().decode())
                    try:
                        self.assertEqual(
                            vm.request(directory, "status")["result"]["status"],
                            "running",
                        )
                        break
                    except OSError:
                        time.sleep(0.05)
                else:
                    self.fail("supervisor did not start")
                self.assertTrue(vm.owned(directory))
                state = json.loads((directory / "vm-state.json").read_text())
                self.assertNotEqual(state["pid"], process.pid)
                first_tunnel = vm.request(directory, "tunnel")["result"]
                time.sleep(0.2)
                self.assertEqual(
                    vm.request(directory, "tunnel")["result"], first_tunnel
                )
                process.kill()
                process.communicate(timeout=10)
                deadline = time.monotonic() + 5
                while vm.owned(directory) and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertFalse(vm.owned(directory))
                # On Linux an orphan may briefly be a zombie; it must not run.
                if os.name != "nt":
                    stat = Path(f'/proc/{state["pid"]}/stat')
                    deadline = time.monotonic() + 5
                    while (
                        stat.exists()
                        and stat.read_text().split(") ")[1].split()[0] != "Z"
                        and time.monotonic() < deadline
                    ):
                        time.sleep(0.05)
                    self.assertTrue(
                        not stat.exists()
                        or stat.read_text().split(") ")[1].split()[0] == "Z"
                    )
                else:
                    import ctypes
                    from ctypes import wintypes

                    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                    kernel.OpenProcess.restype = wintypes.HANDLE
                    kernel.WaitForSingleObject.argtypes = [
                        wintypes.HANDLE,
                        wintypes.DWORD,
                    ]
                    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
                    handle = kernel.OpenProcess(0x100000, False, state["pid"])
                    if handle:
                        self.assertEqual(kernel.WaitForSingleObject(handle, 5000), 0)
                        kernel.CloseHandle(handle)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
