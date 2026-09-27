"""CLI client for the same versioned API used by the console."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
import webbrowser

from . import controller


def add_live_commands(actions, commands):
    provision = actions.add_parser("provision")
    provision.add_argument("name")
    provision.add_argument(
        "--acceleration", choices=("auto", "whpx", "kvm", "tcg"), default="auto"
    )
    provision.add_argument("--cloud-image", type=Path)
    for verb in ("provision-status", "provision-finalize", "provision-stop"):
        parser = actions.add_parser(verb)
        parser.add_argument("name")
    start = actions.add_parser("start")
    start.add_argument("name")
    start.add_argument(
        "--acceleration", choices=("auto", "whpx", "kvm", "tcg"), default="auto"
    )
    start.add_argument("--network", action="store_true")
    stop = actions.add_parser("stop")
    stop.add_argument("name")
    stop.add_argument("--force", action="store_true")
    stop.add_argument("--timeout", type=int, default=30)
    for verb in ("exec", "shell"):
        parser = actions.add_parser(verb)
        parser.add_argument("name")
        parser.add_argument("--mode", choices=("darwin", "linux"), default="darwin")
        parser.add_argument("--admin", action="store_true")
        parser.add_argument("--detach", action="store_true")
        parser.add_argument("argv", nargs=argparse.REMAINDER)
    for verb in ("inspect", "serial", "health"):
        parser = actions.add_parser(verb)
        parser.add_argument("name")
    network = actions.add_parser("network")
    network.add_argument("name")
    network.add_argument("state", choices=("up", "down"))
    for verb in ("import", "export"):
        parser = actions.add_parser(verb)
        parser.add_argument("name")
        parser.add_argument("source")
        parser.add_argument("destination")
        if verb == "import":
            parser.add_argument("--executable", action="store_true")
    debug = actions.add_parser("debug")
    debug.add_argument("name")
    debug.add_argument("--program")
    debug.add_argument("--attach", type=int)
    debug.add_argument("--core")
    debug.add_argument("--lldb")
    debug.add_argument("--mode", choices=("darwin", "linux"), default="darwin")
    debug.add_argument("--detach", action="store_true")
    session = actions.add_parser("session")
    session.add_argument("name")
    session.add_argument("session")
    session.add_argument("--close", choices=("detach", "terminate"))
    fault = actions.add_parser("fault")
    fault.add_argument("name")
    fault.add_argument(
        "kind", choices=("process", "service", "disk-full", "disk-clear")
    )
    fault.add_argument("--pid", type=int)
    fault.add_argument("--start")
    fault.add_argument("--service")
    fault.add_argument("--mib", type=int, default=64)
    for verb in ("diagnostics", "scenario"):
        parser = actions.add_parser(verb)
        parser.add_argument("name")
        parser.add_argument("--output", type=Path, required=True)
        if verb == "scenario":
            parser.add_argument("--file", type=Path, required=True)
    timeline = actions.add_parser("timeline")
    timeline.add_argument("--name")
    timeline.add_argument("--query", default="")
    console = commands.add_parser("console")
    console.add_argument("--root", type=Path, default=Path("build/darwin-machines"))
    console.add_argument("--no-browser", action="store_true")


def console(args):
    root = controller.ensure(args.root)
    endpoint = json.loads((root / ".controller/endpoint.json").read_text())
    url = f'http://127.0.0.1:{endpoint["port"]}/#{endpoint["token"]}'
    print(url)
    if not args.no_browser:
        webbrowser.open(url)
    return 0


def terminal(root, machine, session, interactive=True):
    stop = threading.Event()

    def input_loop():
        try:
            while not stop.is_set():
                data = os.read(sys.stdin.fileno(), 1024)
                if not data:
                    return
                controller.request(
                    root,
                    "session-write",
                    name=machine,
                    session=session,
                    data=base64.b64encode(data).decode(),
                )
        except (OSError, ValueError):
            pass

    if interactive:
        threading.Thread(target=input_loop, daemon=True).start()
    cursor = 0
    try:
        while True:
            result = controller.request(
                root, "session-read", name=machine, session=session, cursor=cursor
            )
            if result["truncated"]:
                sys.stderr.write("\n[earlier output truncated]\n")
            sys.stdout.buffer.write(base64.b64decode(result["data"]))
            sys.stdout.buffer.flush()
            cursor = result["cursor"]
            if result["exit_code"] is not None:
                return result["exit_code"]
            time.sleep(0.15)
    except KeyboardInterrupt:
        print(
            f"\nDetached; session {session} remains running. Use machine session to reconnect.",
            file=sys.stderr,
        )
        return 130
    finally:
        stop.set()


def transfer(root, args):
    if args.machine_action == "import":
        source = Path(args.source)
        if source.stat().st_size > 64 * 1024 * 1024:
            raise ValueError("import exceeds 64 MiB")
        with source.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        result = controller.request(
            root,
            "import-begin",
            name=args.name,
            path=args.destination,
            size=source.stat().st_size,
            sha256=digest,
            executable=args.executable,
        )
        ident, offset = result["transfer"], 0
        try:
            with source.open("rb") as stream:
                while data := stream.read(262144):
                    result = controller.request(
                        root,
                        "import-chunk",
                        name=args.name,
                        transfer=ident,
                        offset=offset,
                        data=base64.b64encode(data).decode(),
                    )
                    offset = result["offset"]
            return controller.request(
                root, "import-commit", name=args.name, transfer=ident
            )
        except BaseException:
            try:
                controller.request(root, "import-abort", name=args.name, transfer=ident)
            except (OSError, ValueError):
                pass
            raise
    destination = Path(args.destination).absolute()
    if destination.exists():
        raise ValueError("export destination already exists")
    temporary = destination.with_name(destination.name + ".partial")
    offset, expected, size = 0, None, None
    with temporary.open("xb") as stream:
        while True:
            result = controller.request(
                root, "export", name=args.name, path=args.source, offset=offset
            )
            if expected is None:
                expected, size = result["sha256"], result["size"]
            if (
                result["sha256"] != expected
                or result["size"] != size
                or size > 64 * 1024 * 1024
            ):
                raise ValueError("guest export identity changed or exceeds limit")
            block = base64.b64decode(result["data"], validate=True)
            if not block and offset != size:
                raise ValueError("incomplete guest export")
            stream.write(block)
            offset += len(block)
            if offset == size:
                break
            if offset > size:
                raise ValueError("guest export exceeds declared size")
        stream.flush()
        os.fsync(stream.fileno())
    with temporary.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
            raise ValueError("export hash mismatch")
    # Exclusive publication, also safe against a racing local destination creator.
    os.link(temporary, destination)
    temporary.unlink()
    return {"path": str(destination), "sha256": expected, "size": size}


def dispatch(args):
    root = controller.ensure(args.root)
    action = args.machine_action
    body = {
        key: str(value.resolve()) if isinstance(value, Path) else value
        for key, value in vars(args).items()
        if key not in ("action", "machine_action", "root")
    }
    if action in ("import", "export"):
        result = transfer(root, args)
    elif action == "session":
        if args.close:
            result = controller.request(
                root,
                "session-close",
                name=args.name,
                session=args.session,
                disposition=args.close,
            )
        else:
            return terminal(root, args.name, args.session)
    else:
        if action == "network":
            body["up"] = args.state == "up"
        if action in ("exec", "shell"):
            body["argv"] = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
            if not body["argv"]:
                body["argv"] = ["/bin/bash", "-l"]
        if action == "scenario":
            data = json.loads(args.file.read_text())
            body.update(steps=data["steps"], previous=data.get("results", []))
        result = controller.request(root, action, **body)
        if action in ("exec", "shell", "debug") and not args.detach:
            return terminal(root, args.name, result["id"], interactive=action != "exec")
        if action == "diagnostics":
            with args.output.open("xb") as stream:
                stream.write(base64.b64decode(result.pop("archive")))
            result["path"] = str(args.output)
        elif action == "scenario":
            args.output.write_text(json.dumps(result, indent=2) + "\n")
        elif action == "serial":
            sys.stdout.buffer.write(base64.b64decode(result["result"]))
            return 0
    print(json.dumps(result, indent=2))
    return 0
