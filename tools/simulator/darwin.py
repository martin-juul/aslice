"""Persistent storage for the Darwin compatibility environment."""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import uuid

from .model import atomic_json
from .requirements import load_json

BACKEND = "Darwin compatibility environment"
DARLING_COMMIT = "60ba801decee7a00782f74f6be4c8ffb013f79ff"
GATES = (
    "unchanged-cli",
    "cocoa-input",
    "document-persistence",
    "lldb-parent-child",
    "guest-isolation",
    "lifecycle-recovery",
    "aslice-compatibility",
)


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def name(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,47}", value):
        raise ValueError(
            "names must be 1-48 lowercase letters, digits or hyphens, starting with a letter"
        )
    # Avoid Windows device names, including names which also match the grammar.
    if value in {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{i}" for i in range(10)),
        *(f"lpt{i}" for i in range(10)),
    }:
        raise ValueError("reserved machine name")
    return value


def no_links(path):
    path = Path(path).absolute()
    for entry in (path, *path.parents):
        if entry.is_symlink() or getattr(entry, "is_junction", lambda: False)():
            raise ValueError(f"link or junction refused: {entry}")
    return path


def checked_copy(source, destination, expected=None):
    """Publish only a complete, fsynced, identity-checked copy."""
    temporary = destination.with_name(destination.name + ".partial")
    with source.open("rb") as src, temporary.open("xb") as dst:
        shutil.copyfileobj(src, dst, 1024 * 1024)
        dst.flush()
        os.fsync(dst.fileno())
    actual = sha256(temporary)
    if expected is not None and actual != expected:
        raise ValueError(
            "copied artifact hash mismatch; partial copy retained for diagnosis"
        )
    os.replace(temporary, destination)
    return actual


def image_info(path, executable="qemu-img"):
    result = subprocess.run(
        [executable, "info", "--output=json", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    info = json.loads(result.stdout)
    if not isinstance(info, dict):
        raise ValueError("invalid QEMU image information")
    # Do not request --backing-chain: that would open external backing paths
    # before we have had an opportunity to refuse them.
    if info.get("backing-filename") or info.get("full-backing-filename"):
        raise ValueError("base must be a standalone image without backing files")
    if info.get("format") not in ("raw", "qcow2"):
        raise ValueError("base must use raw or qcow2 format")
    if info.get("encrypted") or "data-file" in json.dumps(info):
        raise ValueError("encrypted images and external data files are unsupported")
    if type(info.get("virtual-size")) is not int or info["virtual-size"] <= 0:
        raise ValueError("invalid base virtual size")
    return info


def runtime_identity(path):
    """Require immutable inputs, without treating declarations as execution proof."""
    if Path(path).stat().st_size > 1024 * 1024:
        raise ValueError("runtime identity exceeds 1 MiB")
    data = load_json(path)
    expected = {
        "version",
        "guest",
        "darling_commit",
        "submodules",
        "artifacts",
        "build",
    }
    if (
        not isinstance(data, dict)
        or set(data) != expected
        or type(data["version"]) is not int
        or data["version"] != 1
    ):
        raise ValueError("unsupported runtime identity")
    if (
        data["guest"] != "ubuntu-26.04-x86_64"
        or data["darling_commit"] != DARLING_COMMIT
    ):
        raise ValueError(
            "runtime must identify the pinned Darling revision and Ubuntu 26.04 x86-64"
        )
    for field in ("submodules", "artifacts", "build"):
        if not isinstance(data[field], dict) or not data[field]:
            raise ValueError(f"runtime identity requires {field}")
    for key, value in data["submodules"].items():
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
            raise ValueError(f"invalid submodule commit: {key}")
    for key, value in data["artifacts"].items():
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"invalid artifact digest: {key}")
    for field in ("compiler", "packages", "command", "source_tree"):
        if (
            not isinstance(data["build"].get(field), str)
            or not data["build"][field].strip()
        ):
            raise ValueError(f"runtime build identity requires {field}")
    return data


def preflight(acceleration="auto"):
    system = platform.system()
    selected = (
        {"Windows": "whpx", "Linux": "kvm"}.get(system)
        if acceleration == "auto"
        else acceleration
    )
    blockers = []
    if system not in ("Windows", "Linux"):
        blockers.append("only Windows and Linux hosts are supported")
    paths = {
        tool: shutil.which(tool) for tool in ("qemu-system-x86_64", "qemu-img", "ssh")
    }
    for tool, path in paths.items():
        if not path:
            blockers.append(f"missing executable: {tool}")
    available = []
    if paths["qemu-system-x86_64"]:
        try:
            probe = subprocess.run(
                [paths["qemu-system-x86_64"], "-accel", "help"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            available = probe.stdout.splitlines()[1:]
            available = [item.strip() for item in available]
            if selected not in available:
                blockers.append(f"QEMU does not advertise accelerator: {selected}")
        except (OSError, subprocess.SubprocessError) as error:
            blockers.append(f"QEMU accelerator probe failed: {error}")
    if selected == "kvm" and (
        system != "Linux" or not os.access("/dev/kvm", os.R_OK | os.W_OK)
    ):
        blockers.append("KVM device is unavailable or inaccessible")
    if selected == "whpx" and system != "Windows":
        blockers.append("WHPX requires a Windows host")
    return {
        "version": 1,
        "backend": BACKEND,
        "host": {
            "system": system,
            "release": platform.release(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python": platform.python_version(),
        },
        "tools": paths,
        "accelerator": selected,
        "advertised_accelerators": available,
        "software_emulation": selected == "tcg",
        "boot_verified": False,
        "darling_commit": DARLING_COMMIT,
        "infrastructure_ready": not blockers,
        "blockers": blockers,
        "complete": False,
        "gates": {gate: "pending: no VM execution evidence" for gate in GATES},
    }


class Machines:
    """Exclusive host-owned store of stopped images. No live snapshot semantics.

    One OS lease serializes writers and is released on process death. Each
    mutation journals intent before publishing metadata. Interrupted operations
    retain staging files and report uncertainty; they never trigger a launch.
    """

    def __init__(self, root, qemu_img="qemu-img"):
        self.root = no_links(root)
        self.qemu_img = qemu_img
        self.lease = None

    def __enter__(self):
        self.root.mkdir(parents=True, exist_ok=True)
        marker = self.root / "darwin-store.json"
        if not marker.exists() and any(self.root.iterdir()):
            raise ValueError(
                "machine store must be empty or initialized by this backend"
            )
        for entry in self.root.rglob("*"):
            no_links(entry)
            if entry.is_file() and entry.stat().st_nlink != 1:
                raise ValueError("hardlinked store file refused")
        self.lease = (self.root / ".lease").open("a+b")
        try:
            if self.lease.tell() == 0:
                self.lease.write(b"0")
                self.lease.flush()
            self.lease.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.lease.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            identity = {"version": 1, "backend": BACKEND}
            if marker.exists():
                if load_json(marker) != identity:
                    raise ValueError("unsupported machine store")
            else:
                atomic_json(marker, identity)
            for directory in ("machines", "bases", "operations", "trash"):
                (self.root / directory).mkdir(exist_ok=True)
            for operation in (self.root / "operations").glob("*.json"):
                record = load_json(operation)
                if record["outcome"] == "pending":
                    record["outcome"] = (
                        "interrupted; inspect retained state before retry"
                    )
                    atomic_json(operation, record)
        except BaseException:
            self.lease.close()
            self.lease = None
            raise
        return self

    def __exit__(self, *_):
        self.lease.close()
        self.lease = None

    @contextmanager
    def operation(self, action, machine):
        ident = uuid.uuid4().hex
        path = self.root / "operations" / (ident + ".json")
        record = {
            "version": 1,
            "id": ident,
            "action": action,
            "machine": machine,
            "time": datetime.now(timezone.utc).isoformat(),
            "outcome": "pending",
        }
        atomic_json(path, record)
        try:
            yield ident
        except BaseException as error:
            record.update(
                outcome="failed or uncertain; retained state requires inspection",
                error=str(error),
            )
            atomic_json(path, record)
            raise
        record["outcome"] = "acknowledged"
        atomic_json(path, record)

    def directory(self, machine):
        if self.lease is None:
            raise ValueError("machine store requires an ownership lease")
        return self.root / "machines" / name(machine)

    def read(self, machine):
        directory = self.directory(machine)
        data = load_json(directory / "machine.json")
        if data.get("backend") != BACKEND or data.get("version") != 1:
            raise ValueError("unsupported machine metadata")
        if not re.fullmatch(r"disk-[0-9a-f]{32}\.qcow2", data.get("disk", "")):
            raise ValueError("invalid active disk identity")
        if not re.fullmatch(r"[0-9a-f]{64}", data.get("base", "")):
            raise ValueError("invalid base identity")
        return data

    def stopped(self, machine):
        data = self.read(machine)
        from .vm import owned

        if owned(self.directory(machine)):
            raise ValueError(
                "operation requires a stopped machine; supervisor owns the disk"
            )
        if data.get("state") != "stopped":
            raise ValueError(
                "operation requires a stopped machine; live disk snapshots are unsupported"
            )
        base = self.root / "bases" / data["base"]
        if sha256(base / "image") != data["base"]:
            raise ValueError("base image identity mismatch")
        if sha256(base / "runtime.json") != data["runtime_sha256"]:
            raise ValueError("runtime identity mismatch")
        return data

    def create(self, machine, image, runtime, cpus=4, memory_mib=8192, disk_gib=64):
        target = self.directory(machine)
        if target.exists():
            raise ValueError("machine already exists (possibly interrupted creation)")
        if (
            type(cpus) is not int
            or not 1 <= cpus <= 256
            or type(memory_mib) is not int
            or not 512 <= memory_mib <= 1048576
            or type(disk_gib) is not int
            or not 1 <= disk_gib <= 16384
        ):
            raise ValueError("invalid machine resource limits")
        identity = runtime_identity(runtime)
        image = no_links(image)
        info = image_info(image, self.qemu_img)
        if info["virtual-size"] > disk_gib * 1024**3:
            raise ValueError("requested disk is smaller than base image")
        digest = sha256(image)
        with self.operation("create", machine) as operation:
            base = self.root / "bases" / digest
            if not base.exists():
                staging = self.root / "bases" / (digest + "." + operation)
                staging.mkdir()
                checked_copy(image, staging / "image", digest)
                atomic_json(staging / "runtime.json", identity)
                os.replace(staging, base)
            elif (
                sha256(base / "image") != digest
                or load_json(base / "runtime.json") != identity
            ):
                raise ValueError("base identity collision or changed artifact")
            target.mkdir()
            (target / "snapshots").mkdir()
            (target / "evidence").mkdir()
            disk = "disk-" + operation + ".qcow2"
            subprocess.run(
                [
                    self.qemu_img,
                    "create",
                    "-q",
                    "-f",
                    "qcow2",
                    "-F",
                    info["format"],
                    "-b",
                    str(base / "image"),
                    str(target / disk),
                    f"{disk_gib}G",
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )
            data = {
                "version": 1,
                "backend": BACKEND,
                "name": machine,
                "state": "stopped",
                "base": digest,
                "runtime_sha256": sha256(base / "runtime.json"),
                "disk": disk,
                "cpus": cpus,
                "memory_mib": memory_mib,
                "disk_gib": disk_gib,
                "network": False,
                "host_mounts": [],
                "runtime_validated": False,
                "capabilities": {gate: "pending" for gate in GATES},
                "last_operation": operation,
            }
            atomic_json(target / "machine.json", data)
        return data

    def status(self, machine=None):
        if machine:
            return self.read(machine)
        result = []
        for directory in sorted((self.root / "machines").iterdir()):
            try:
                result.append(self.read(directory.name))
            except (OSError, ValueError, KeyError) as error:
                result.append(
                    {"name": directory.name, "state": "incomplete", "error": str(error)}
                )
        return {
            "version": 1,
            "backend": BACKEND,
            "machines": result,
            "operations": [
                load_json(p) for p in sorted((self.root / "operations").glob("*.json"))
            ],
        }

    def clone(self, machine, destination):
        data = self.stopped(machine)
        target = self.directory(destination)
        if target.exists():
            raise ValueError("destination already exists")
        with self.operation("clone", machine) as operation:
            target.mkdir()
            (target / "snapshots").mkdir()
            (target / "evidence").mkdir()
            disk = "disk-" + operation + ".qcow2"
            checked_copy(self.directory(machine) / data["disk"], target / disk)
            data.update(name=destination, disk=disk, last_operation=operation)
            atomic_json(target / "machine.json", data)
        return data

    def snapshot(self, machine, snapshot, restore=False):
        data = self.stopped(machine)
        directory = self.directory(machine)
        target = directory / "snapshots" / name(snapshot)
        if restore:
            saved = load_json(target / "snapshot.json")
            if (
                saved["base"] != data["base"]
                or saved["runtime_sha256"] != data["runtime_sha256"]
            ):
                raise ValueError("snapshot image/runtime identities do not match")
            with self.operation("restore", machine) as operation:
                disk = "disk-" + operation + ".qcow2"
                checked_copy(
                    target / "disk.qcow2", directory / disk, saved["disk_sha256"]
                )
                # Retain the previous disk even after atomic activation.
                data.update(
                    disk=disk, last_operation=operation, previous_disk=data["disk"]
                )
                atomic_json(directory / "machine.json", data)
            return data
        if target.exists():
            raise ValueError("snapshot already exists (possibly interrupted creation)")
        with self.operation("snapshot", machine) as operation:
            target.mkdir()
            digest = checked_copy(directory / data["disk"], target / "disk.qcow2")
            saved = {
                "version": 1,
                "base": data["base"],
                "runtime_sha256": data["runtime_sha256"],
                "disk_sha256": digest,
                "operation": operation,
            }
            atomic_json(target / "snapshot.json", saved)
        return saved

    def delete(self, machine):
        self.stopped(machine)
        with self.operation("delete", machine) as operation:
            destination = self.root / "trash" / (machine + "-" + operation)
            os.replace(self.directory(machine), destination)
        return {"name": machine, "state": "deleted", "retained_at": str(destination)}


def add_commands(commands):
    machine = commands.add_parser(
        "machine", help="manage persistent Darwin compatibility machines"
    )
    machine.add_argument("--root", type=Path, default=Path("build/darwin-machines"))
    actions = machine.add_subparsers(dest="machine_action", required=True)
    from .machine_cli import add_live_commands

    add_live_commands(actions, commands)
    doctor = actions.add_parser("doctor")
    doctor.add_argument(
        "--acceleration", choices=("auto", "whpx", "kvm", "tcg"), default="auto"
    )
    doctor.add_argument("--output", type=Path)
    corpus = actions.add_parser("corpus")
    corpus.add_argument("manifest", type=Path)
    fetch = actions.add_parser(
        "fetch-corpus",
        help="download a pinned upstream CLI candidate; never execute it",
    )
    fetch.add_argument("--output", type=Path, required=True)
    create = actions.add_parser("create")
    create.add_argument("name")
    create.add_argument("--image", type=Path, required=True)
    create.add_argument("--runtime", type=Path, required=True)
    create.add_argument("--cpus", type=int, default=4)
    create.add_argument("--memory-mib", type=int, default=8192)
    create.add_argument("--disk-gib", type=int, default=64)
    status = actions.add_parser("status")
    status.add_argument("name", nargs="?")
    clone = actions.add_parser("clone")
    clone.add_argument("name")
    clone.add_argument("destination")
    delete = actions.add_parser("delete")
    delete.add_argument("name")
    snapshot = actions.add_parser("snapshot")
    snapshot.add_argument("operation", choices=("create", "restore"))
    snapshot.add_argument("name")
    snapshot.add_argument("snapshot")


def dispatch(args):
    if args.machine_action == "fetch-corpus":
        from .corpus_fetch import fetch

        print(json.dumps(fetch(args.output), indent=2))
        return 0
    if args.machine_action == "corpus":
        from .corpus import verify

        result = verify(args.manifest)
        print(json.dumps(result, indent=2))
        return 1 if result["missing_roles"] else 0
    if args.machine_action == "doctor":
        result = preflight(args.acceleration)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            atomic_json(args.output, result)
        print(json.dumps(result, indent=2))
        return 0 if result["infrastructure_ready"] else 1
    from .machine_cli import dispatch

    return dispatch(args)
