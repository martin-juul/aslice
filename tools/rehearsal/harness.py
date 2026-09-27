"""Launch actual executables and record inputs, platform effects and outcomes."""
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

from .coverage import ROOT, report
from .model import Model, atomic_json
from .server import Server


class Workspace:
    def __init__(self, path):
        self.root = Path(path).absolute()
        self.lock = None

    def __enter__(self):
        # Refuse links before resolving them, including Windows junctions.
        def linked(path):
            return path.is_symlink() or getattr(path, "is_junction", lambda: False)()
        if any(linked(path) for path in (self.root, *self.root.parents)):
            raise ValueError("workspace path contains a link or junction")
        self.root.mkdir(parents=True, exist_ok=True)
        marker = self.root / "rehearsal.json"
        if not marker.exists() and any(self.root.iterdir()):
            raise ValueError("workspace must be empty or initialized by rehearsal")
        if any(linked(path) for path in self.root.rglob("*")):
            raise ValueError("workspace contains a link or junction")
        if any(path.is_file() and path.stat().st_nlink != 1 for path in self.root.rglob("*")):
            raise ValueError("workspace contains a hardlinked file")
        self.lock = (self.root / ".lease").open("a+b")
        try:
            if self.lock.tell() == 0:
                self.lock.write(b"0")
                self.lock.flush()
            self.lock.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if marker.exists():
                if json.loads(marker.read_text()) != {"version": 1}:
                    raise ValueError("unsupported rehearsal workspace")
            else:
                atomic_json(marker, {"version": 1})
            for name in ("os", "application", "inputs", "evidence", "sessions"):
                (self.root / name).mkdir(exist_ok=True)
        except BaseException:
            self.lock.close()
            raise
        return self.root

    def __exit__(self, *_):
        self.lock.close()


def source_identity():
    revision, dirty = None, None
    if shutil.which("git"):
        probe = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True)
        if probe.returncode == 0:
            revision = probe.stdout.strip()
            status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True)
            dirty = bool(status.stdout) if status.returncode == 0 else None
    digest = hashlib.sha256()
    for directory in ("src", "tools/rehearsal", "tests", "docs/sqlite"):
        for path in sorted((ROOT / directory).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                digest.update(path.relative_to(ROOT).as_posix().encode())
                digest.update(b"\0")
                digest.update(hashlib.sha256(path.read_bytes()).digest())
    for relative in ("CMakeLists.txt", "CMakePresets.json", "vcpkg.json"):
        path = ROOT / relative
        digest.update(relative.encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return {"revision": revision, "dirty": dirty, "owned_source_sha256": digest.hexdigest()}


def launch(workspace, executable, command, seed=0, *, driver=False, script=None,
           baseline=None, identity=None, capabilities=None):
    executable = Path(executable).resolve(strict=True)
    if identity is not None and not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", identity):
        raise ValueError("invalid process identity")
    model = Model(workspace, seed)
    if baseline is not None:
        model.state = copy.deepcopy(baseline)
        model.save()
    before = copy.deepcopy(model.state)
    identity = identity or f"process-{model.state['tick'] + 1}"
    if capabilities is None:
        capabilities = ["machine", "filesystem", "clock", "outcome", "process"]
    server = Server(model)
    session = workspace / "sessions" / "connection.json"
    timed_out = False
    try:
        # The exclusive workspace lease proves no previous harness still owns it.
        session.unlink(missing_ok=True)
        with session.open("x", encoding="utf-8") as output:
            os.chmod(session, 0o600)
            json.dump(server.issue(identity, capabilities), output)
        arguments = [str(executable), "--session", str(session)]
        if driver:
            script_path = workspace / "inputs" / "platform-script.json"
            atomic_json(script_path, script)
            arguments += ["--script", str(script_path)]
        else:
            arguments += command
        server.expect_process(identity)
        environment = os.environ.copy()
        environment.pop("ASLICE_PROTOTYPE_FAILPOINT", None)
        process = subprocess.Popen(arguments, cwd=workspace, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment)
        server.attach_process(identity, process)
        try:
            stdout, stderr = process.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            stdout, stderr = process.communicate()
    finally:
        server.close()
        session.unlink(missing_ok=True)
    evidence = {"version": 1, "source": source_identity(),
                "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                "host": {"system": platform.system(), "machine": platform.machine()},
                "execution_mode": "cpp-platform-driver" if driver else "cpp-rehearsal",
                "qualification": "simulated", "target": model.state["target"],
                "seed": model.state["seed"], "identity": identity, "capabilities": capabilities,
                "command": command, "script": script, "initial_state": before,
                "final_state": copy.deepcopy(model.state), "requests": server.transcript,
                "stdout_hex": stdout.hex(), "stderr_hex": stderr.hex(),
                "exit_status": process.returncode,
                "termination_kind": "timeout" if timed_out else server.terminated.get(identity),
                "terminated_by_harness": timed_out or identity in server.terminated}
    trace = workspace / "evidence" / f"{identity}.json"
    suffix = 2
    while trace.exists():
        trace = workspace / "evidence" / f"{identity}-{suffix}.json"
        suffix += 1
    atomic_json(trace, evidence)
    return process.returncode, stdout, stderr, trace


def replay(workspace, executable, trace):
    recorded = json.loads(Path(trace).read_text(encoding="utf-8"))
    if recorded.get("version") != 1 or recorded.get("qualification") != "simulated":
        raise ValueError("not a version 1 simulated trace")
    if any((workspace / "evidence").iterdir()) or (workspace / "os/state.json").exists():
        raise ValueError("replay requires a fresh workspace")
    driver = recorded["execution_mode"] == "cpp-platform-driver"
    if not driver and recorded["execution_mode"] != "cpp-rehearsal":
        raise ValueError("unsupported execution mode")
    _, _, _, generated = launch(workspace, executable, recorded["command"],
                                driver=driver, script=recorded["script"],
                                baseline=recorded["initial_state"], identity=recorded["identity"],
                                capabilities=recorded["capabilities"])
    actual = json.loads(generated.read_text())
    differences = [field for field in ("requests", "final_state", "terminated_by_harness")
                   if recorded[field] != actual[field]]
    # OS process-kill exit codes differ between Windows and POSIX.
    expected_termination = recorded.get("termination_kind")
    if expected_termination != actual.get("termination_kind"):
        differences.append("termination_kind")
    if not expected_termination and recorded["exit_status"] != actual["exit_status"]:
        differences.append("exit_status")
    for stream in ("stdout_hex", "stderr_hex"):
        if bytes.fromhex(recorded[stream]).replace(b"\r\n", b"\n") != bytes.fromhex(actual[stream]).replace(b"\r\n", b"\n"):
            differences.append(stream)
    result = {"matched": not differences, "differences": differences,
              "recorded_executable_sha256": recorded["executable_sha256"],
              "replay_executable_sha256": actual["executable_sha256"]}
    atomic_json(workspace / "evidence/replay.json", result)
    return 1 if differences else 0


def run(workspace, executable, suite, seed, native_evidence=None):
    code, stdout, stderr, _ = launch(workspace, executable, ["version", "normalize", "v7.1"], seed)
    # Assert a semantic value independently; never substitute an expected answer.
    try:
        passed = code == 0 and json.loads(stdout) == {"version": "7.1.0"} and not stderr
    except (ValueError, UnicodeError):
        passed = False
    lifecycle = None
    if passed and suite in ("fixture", "full"):
        from .scenarios import fixture_lifecycle
        lifecycle = fixture_lifecycle(workspace, executable, seed, launch)
    coverage = report()
    atomic_json(workspace / "evidence/coverage.json", coverage)
    result = {"suite": suite, "foundation_passed": passed,
              "fixture_lifecycle": lifecycle,
              "scope": {"foundation": "version normalization through simulated platform",
                        "fixture": "unsigned fixture lifecycle through simulated platform",
                        "full": "release acceptance; incomplete requirements remain blocking"}[suite],
              "native_evidence": native_evidence,
              "development_valid": coverage["development_valid"],
              "complete": False, "mandatory_gaps": coverage["mandatory_gaps"]}
    atomic_json(workspace / "evidence/suite.json", result)
    print(json.dumps(result, indent=2))
    return 0 if coverage["development_valid"] and passed and (
        suite == "foundation" or (suite == "fixture" and lifecycle["passed"])) else 1
