"""Exercise the private manager endpoint with independently constructed frames."""
import copy
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import unittest

MANAGER = str(Path(sys.argv.pop(1)).resolve())
FIXTURE = Path(__file__).parent / "fixtures" / "artifact-manifest.json"
MODE = "--internal-manifest-inspection-v2"


class HelperProcessTests(unittest.TestCase):
    def test_private_mode_requires_inherited_channel(self):
        for arguments in ([], ["-1", "0"], ["999999999999999999999999", "0"]):
            result = subprocess.run([MANAGER, MODE, *arguments], capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 3)
            self.assertEqual(result.stdout, b"")

    @unittest.skipUnless(sys.platform == "linux", "Linux peer credential channel")
    def test_os_peer_identity_and_fixed_capabilities(self):
        manifest = json.loads(FIXTURE.read_text(encoding="utf-8"))
        canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        binding = {
            "caller": f"uid:{os.geteuid()}", "role": "extract",
            "instance_id": "a" * 32, "operation_id": "b" * 32,
            "session_id": "c" * 32,
            "plan_digest": "sha256:" + hashlib.sha256(canonical.encode()).hexdigest(),
            "capabilities": ["manifest.inspect"],
        }
        request = {"format": 2, "binding": binding, "sequence": 1,
                   "command": "manifest.inspect", "arguments": manifest}
        mutations = [
            ("caller", "uid:forged"), ("role", "link"),
            ("capabilities", ["manifest.inspect", "archive.extract"]),
            ("plan_digest", "sha256:" + "0" * 64),
        ]
        cases = [("valid", request, True)]
        for field, value in mutations:
            forged = copy.deepcopy(request)
            forged["binding"][field] = value
            cases.append((field, forged, False))
        for field, value in (("format", True), ("sequence", 2), ("command", "archive.extract")):
            forged = copy.deepcopy(request)
            forged[field] = value
            cases.append((field, forged, False))
        for name, message, accepted in cases:
            with self.subTest(name=name):
                payload = json.dumps(message, separators=(",", ":")).encode()
                status, output = self.exchange(struct.pack(">I", len(payload)) + payload)
                self.assertEqual(status, 0 if accepted else 3)
                if accepted:
                    length = struct.unpack(">I", output[:4])[0]
                    self.assertEqual(length, len(output) - 4)
                    response = json.loads(output[4:])
                    self.assertEqual(response["binding"], binding)
                    self.assertIsNone(response["failure"])
                    self.assertEqual(response["effects"], [])
                    self.assertEqual(len(response["observations"]), 1)
                else:
                    self.assertEqual(output, b"")

    @unittest.skipUnless(sys.platform == "linux", "Linux inherited channel")
    def test_truncated_oversized_frames_and_wrong_parent(self):
        for payload in (b"\0", struct.pack(">I", 1024 * 1024 + 1),
                        struct.pack(">I", 10) + b"{}"):
            status, response = self.exchange(payload)
            self.assertEqual((status, response), (3, b""))
        status, response = self.exchange(b"", parent=os.getpid() + 1)
        self.assertEqual((status, response), (3, b""))

    def exchange(self, payload, parent=None):
        server, child = socket.socketpair()
        with server, child:
            server.settimeout(5)
            process = subprocess.Popen(
                [MANAGER, MODE, str(child.fileno()), str(os.getpid() if parent is None else parent)],
                pass_fds=(child.fileno(),), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            child.close()
            try:
                # Fragment writes independently of C++'s transport implementation.
                for offset in range(0, len(payload), 11):
                    server.sendall(payload[offset:offset + 11])
                server.shutdown(socket.SHUT_WR)
                output = bytearray()
                while chunk := server.recv(4096):
                    output.extend(chunk)
                stdout, stderr = process.communicate(timeout=5)
                self.assertEqual((stdout, stderr), (b"", b""))
                return process.returncode, bytes(output)
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
