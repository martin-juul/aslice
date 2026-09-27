"""Linux guest agent contracts with real PTYs and bounded file transfers."""

import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if os.name == "posix":
    import pwd
    from tools.simulator import guest_agent as agent


@unittest.skipUnless(
    os.name == "posix" and getattr(os, "geteuid", lambda: -1)() == 0,
    "guest agent integration requires a disposable root Linux environment",
)
class GuestTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.user = pwd.getpwuid(os.getuid())
        self.addCleanup(patch.stopall)
        patch.object(agent, "HOME", self.root).start()
        patch.object(agent, "IMPORTS", self.root / "Imports").start()
        patch.object(agent, "SPOOL", self.root / "spool").start()
        patch.object(agent.pwd, "getpwnam", return_value=self.user).start()
        agent.SESSIONS.clear()
        agent.TRANSFERS.clear()
        agent.EVENTS.clear()

    def test_atomic_import_export_refusal_and_interruption(self):
        payload = b"\x00persistent\xff"
        digest = hashlib.sha256(payload).hexdigest()
        begin = agent.handle(
            {
                "action": "import-begin",
                "path": "dir/file",
                "size": len(payload),
                "sha256": digest,
            }
        )
        self.assertFalse((agent.IMPORTS / "dir/file").exists())
        with self.assertRaises(ValueError):
            agent.handle({"action": "import-commit", "transfer": begin["transfer"]})
        agent.handle(
            {
                "action": "import-chunk",
                "transfer": begin["transfer"],
                "offset": 0,
                "data": base64.b64encode(payload).decode(),
            }
        )
        agent.handle({"action": "import-commit", "transfer": begin["transfer"]})
        result = agent.handle({"action": "export", "path": "dir/file"})
        self.assertEqual(base64.b64decode(result["data"]), payload)
        self.assertEqual(result["sha256"], digest)
        for path in ("../escape", "/etc/passwd", "a/../b"):
            with self.assertRaises(ValueError):
                agent.handle({"action": "export", "path": path})
        (agent.IMPORTS / "link").symlink_to("/etc/passwd")
        with self.assertRaises(ValueError):
            agent.handle({"action": "export", "path": "link"})
        begin = agent.handle(
            {"action": "import-begin", "path": "partial", "size": 1, "sha256": "0" * 64}
        )
        agent.handle({"action": "import-abort", "transfer": begin["transfer"]})
        self.assertFalse((agent.IMPORTS / "partial").exists())

    def test_guest_terminal_input_resize_capture_and_truncation(self):
        result = agent.handle(
            {
                "action": "exec",
                "mode": "linux",
                "argv": [
                    sys.executable,
                    "-c",
                    "import os; print(input()); print(os.get_terminal_size())",
                ],
            }
        )
        ident = result["id"]
        agent.handle(
            {"action": "session-resize", "session": ident, "cols": 91, "rows": 23}
        )
        agent.handle(
            {
                "action": "session-write",
                "session": ident,
                "data": base64.b64encode(b"guest-input\n").decode(),
            }
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            result = agent.handle(
                {"action": "session-read", "session": ident, "cursor": 0}
            )
            if result["exit_code"] is not None:
                break
            time.sleep(0.05)
        output = base64.b64decode(result["data"])
        self.assertIn(b"guest-input", output)
        self.assertIn(b"columns=91, lines=23", output)
        agent.handle({"action": "session-close", "session": ident})
        result = agent.handle(
            {
                "action": "exec",
                "mode": "linux",
                "argv": [
                    sys.executable,
                    "-c",
                    f"import sys; sys.stdout.buffer.write(b'x'*{agent.LIMIT+4096})",
                ],
            }
        )
        ident = result["id"]
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            result = agent.handle(
                {"action": "session-read", "session": ident, "cursor": 0}
            )
            if result["exit_code"] is not None:
                break
            time.sleep(0.05)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(base64.b64decode(result["data"])), agent.LIMIT)
        agent.handle({"action": "session-close", "session": ident})

    def test_debugger_requires_explicit_disposition(self):
        result = agent.handle({"action": "debug", "mode": "linux", "lldb": "/bin/cat"})
        ident = result["id"]
        with self.assertRaisesRegex(ValueError, "detach or terminate"):
            agent.handle({"action": "session-close", "session": ident})
        session = agent.SESSIONS[ident]
        session.process.kill()
        session.process.wait(timeout=5)
        agent.handle(
            {"action": "session-close", "session": ident, "disposition": "terminate"}
        )

    def test_darwin_preserves_argument_boundaries(self):
        command = ["/Users/aslice/Imports/my program", "two words", "", "$(false)"]
        with patch.object(agent.subprocess, "Popen") as launch, patch.object(
            agent.threading.Thread, "start"
        ):
            launch.return_value.pid = 123
            session = agent.Session(command)
        self.addCleanup(os.close, session.master)
        child_arguments = json.loads(launch.call_args.args[0][-1])
        self.assertEqual(
            child_arguments,
            ["/usr/local/bin/darling", "shell", *command],
        )

    def test_exit_is_reported_after_final_output_is_drained(self):
        with patch.object(agent.threading.Thread, "start"):
            session = agent.Session(["/bin/echo", "final-output"], mode="linux")
        self.addCleanup(os.close, session.master)
        session.process.wait(timeout=5)
        self.assertIsNone(session.read(0)["exit_code"])
        session.capture()
        result = session.read(0)
        self.assertEqual(result["exit_code"], 0)
        self.assertIn(b"final-output", base64.b64decode(result["data"]))

    def test_process_identity_distinguishes_linux_and_runtime_pids(self):
        directory = self.root / "19553"
        directory.mkdir()
        # A process name may itself contain spaces and closing parentheses.
        fields = ["S", "100", *(["0"] * 17), "12345"]
        (directory / "stat").write_text("19553 (odd ) name) " + " ".join(fields))
        (directory / "cmdline").write_bytes(b"cocoa\0two words\0")
        for namespace, expected in (
            ("19553\t2077", 2077),
            ("19553\t4000\t2077", 2077),
            ("19553", None),
        ):
            with self.subTest(namespace=namespace):
                (directory / "status").write_text(
                    f"Name:\tcocoa\nNSpid:\t{namespace}\n"
                )
                identity = agent.process_identity(directory)
                self.assertEqual(identity["pid"], 19553)
                self.assertEqual(identity["ppid"], 100)
                self.assertEqual(identity["namespace_pid"], expected)
                self.assertEqual(identity["start"], "12345")
                self.assertEqual(identity["command"], "cocoa two words ")

    def test_active_launcher_does_not_hide_a_dead_runtime_server(self):
        directory = self.root / "13496"
        directory.mkdir()
        (directory / "comm").write_text("darlingserver\n")
        (directory / "status").write_text("NSpid:\t13496\n")
        (directory / "cmdline").write_bytes(b"darlingserver\0")
        with patch.object(agent.subprocess, "run") as command:
            command.return_value.returncode = 0
            command.return_value.stdout = (
                b"ActiveState=active\nSubState=running\nResult=success\n"
            )
            for process_state, expected in (
                ("S", "server-observed"),
                ("Z", "server-missing"),
            ):
                with self.subTest(state=process_state):
                    fields = [process_state, "1", *(["0"] * 17), "12345"]
                    (directory / "stat").write_text(
                        "13496 (darlingserver) " + " ".join(fields)
                    )
                    health = agent.runtime_health(self.root)
                    self.assertEqual(health["state"], expected)
            (directory / "comm").unlink()
            self.assertEqual(agent.runtime_health(self.root)["state"], "server-missing")
            command.return_value.returncode = 1
            self.assertEqual(agent.runtime_health(self.root)["state"], "unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
