"""OS state only: no application SQL, package policy, or recovery decisions.

Initial model: one volume, no symlink traversal, NFD/casefold approximation.
File data and directory entry durability are independent. This is not APFS.
"""
import copy
import json
import os
from pathlib import PurePosixPath
import threading
import unicodedata


class Refusal(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def canonical(path):
    if (not isinstance(path, str) or not path.startswith("/") or "\x00" in path
            or "\\" in path or (path != "/" and any(
                part in ("", ".", "..") for part in path[1:].split("/")))):
        raise Refusal("path", "expected canonical absolute target path")
    return unicodedata.normalize("NFD", path).casefold()


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + ".new")
    with temporary.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(value, output, sort_keys=True, ensure_ascii=True, allow_nan=False)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


class Model:
    def __init__(self, workspace, seed=0):
        self.path = workspace / "os" / "state.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.mutex = threading.RLock()
        self.locks = {}
        self.handles = {}
        self.masks = {}
        self.next_handle = 1
        self.stop_kind = None
        if self.path.exists():
            self.state = json.loads(self.path.read_text(encoding="utf-8"))
            if self.state.get("version") != 1:
                raise ValueError("unsupported simulator state")
        else:
            nodes = {"1": self.node("directory", 0o755, uid=0),
                     "2": self.node("directory", 0o700)}
            self.state = {"version": 1, "seed": seed, "next_inode": 3, "tick": 0,
                          "paths": {"/": "1", "/work": "2"}, "nodes": nodes,
                          "durable_nodes": copy.deepcopy(nodes),
                          "durable_dirs": {"1": {"work": "2"}, "2": {}},
                          "outcomes": {}, "faults": [], "quota": 8 * 1024 * 1024,
                          "target": {"os": "10.11", "cpu": "x86_64-v1",
                                     "volume": "rehearsal-volume-1",
                                     "filesystem": "nfd-casefold-approximation",
                                     "execution": "simulated", "apple_execution": False}}
            self.save()
        self.state.setdefault("names", {path: PurePosixPath(path).name for path in self.state["paths"]})
        self.state.setdefault("durable_names", {})

    @staticmethod
    def node(kind, mode, uid=501):
        return {"kind": kind, "mode": mode, "uid": uid, "gid": 20, "xattrs": {}, "acl": []}

    def save(self):
        atomic_json(self.path, self.state)

    def power_loss(self):
        paths = {"/": "1"}
        names = {"/": ""}
        nodes = copy.deepcopy(self.state["durable_nodes"])
        def visit(path, inode, seen):
            if inode in seen:
                raise Refusal("corrupt", "durable directory cycle")
            for name, child in self.state["durable_dirs"].get(inode, {}).items():
                destination = path.rstrip("/") + "/" + name
                paths[destination] = child
                names[destination] = self.state["durable_names"].get(inode, {}).get(name, name)
                if child not in nodes:
                    old = self.state["nodes"][child]
                    nodes[child] = self.node(old["kind"], old["mode"], old["uid"])
                    if old["kind"] == "file":
                        nodes[child]["hex"] = ""
                if nodes[child]["kind"] == "directory":
                    visit(destination, child, seen | {inode})
        visit("/", "1", set())
        self.state["paths"], self.state["nodes"] = paths, nodes
        self.state["names"] = names
        self.locks.clear()
        self.handles.clear()
        self.masks.clear()
        self.save()

    def disconnect(self, identity):
        with self.mutex:
            self.locks = {path: owner for path, owner in self.locks.items() if owner != identity}
            self.handles = {handle: value for handle, value in self.handles.items() if value["owner"] != identity}
            self.masks.pop(identity, None)

    def lookup(self, path):
        walked = ""
        for part in PurePosixPath(path).parts[1:-1]:
            walked += "/" + part
            inode = self.state["paths"].get(walked)
            if inode is None:
                raise Refusal("not-found", "parent does not exist")
            parent = self.state["nodes"][inode]
            if parent["kind"] != "directory":
                raise Refusal("not-directory", "symlink traversal refused")
            if not parent["mode"] & (0o100 if parent["uid"] == 501 else 0o001):
                raise Refusal("permission", "parent is not searchable")
        inode = self.state["paths"].get(path)
        if inode is None:
            raise Refusal("not-found", "target does not exist")
        return inode, self.state["nodes"][inode]

    def writable(self, path):
        if not path.startswith("/work/"):
            raise Refusal("protected", "target is outside the writable volume subtree")
        _, parent = self.lookup(str(PurePosixPath(path).parent))
        if parent["kind"] != "directory" or parent["uid"] != 501 or parent["mode"] & 0o300 != 0o300:
            raise Refusal("permission", "parent does not permit mutation")

    def filesystem(self, identity, operation, args):
        if operation in ("write_handle", "read_handle", "flush_handle", "close"):
            handle = self.handles.get(args.get("handle"))
            if handle is None or handle["owner"] != identity:
                raise Refusal("handle", "invalid or foreign file handle")
            inode, path = handle["inode"], handle["path"]
            node = self.state["nodes"][inode]
            if operation == "close":
                del self.handles[args["handle"]]
                return None, [{"operation": "close", "inode": inode}]
            if operation == "read_handle":
                if handle["access"] != "read":
                    raise Refusal("permission", "handle does not permit reading")
                return self.read_bytes(node, args), []
            if handle["access"] != "write":
                raise Refusal("permission", "handle does not permit writing or flushing")
            if operation == "flush_handle":
                self.state["durable_nodes"][inode] = copy.deepcopy(node)
                return None, [{"operation": "flush_file", "path": path, "inode": inode, "durable": True}]
            return self.write_bytes(node, path, args)
        path = canonical(args["path"])
        if operation == "stat":
            inode, node = self.lookup(path)
            metadata = {key: copy.deepcopy(value) for key, value in node.items() if key != "hex"}
            return {"inode": inode, "size": len(node.get("hex", "")) // 2, **metadata,
                    "links": sum(value == inode for value in self.state["paths"].values())}, []
        if operation == "list":
            _, node = self.lookup(path)
            if node["kind"] != "directory":
                raise Refusal("not-directory", "cannot list this node")
            if not node["mode"] & (0o400 if node["uid"] == 501 else 0o004):
                raise Refusal("permission", "directory is not readable")
            return sorted(self.state["names"].get(child, PurePosixPath(child).name) for child in self.state["paths"]
                          if child != path and str(PurePosixPath(child).parent) == path), []
        if operation in ("read", "open_read"):
            inode, node = self.lookup(path)
            if node["kind"] != "file" or node["uid"] != 501 or not node["mode"] & 0o400:
                raise Refusal("permission", "file cannot be read")
            if operation == "open_read":
                handle = str(self.next_handle)
                self.next_handle += 1
                self.handles[handle] = {"owner": identity, "inode": inode, "path": path, "access": "read"}
                return {"handle": handle, "size": len(node["hex"]) // 2, "mode": node["mode"],
                        "links": sum(value == inode for value in self.state["paths"].values())}, [{"operation": "open_read", "inode": inode}]
            return self.read_bytes(node, args), []
        if operation in ("mkdir", "create", "open_new", "symlink"):
            self.writable(path)
            if path in self.state["paths"]:
                raise Refusal("exists", "target name or normalized alias already exists")
            mode = args.get("mode", 0o700 if operation == "mkdir" else 0o600)
            if type(mode) is not int or not 0 <= mode <= 0o777:
                raise Refusal("mode", "unsupported mode")
            kind = {"mkdir": "directory", "create": "file", "open_new": "file", "symlink": "symlink"}[operation]
            node = self.node(kind, mode & ~self.masks.get(identity, 0))
            if kind == "file":
                node["hex"] = ""
            if operation == "symlink":
                target = args["target"]
                if not isinstance(target, str) or not target or "\x00" in target:
                    raise Refusal("path", "invalid symlink target")
                node["target"] = target
            inode = str(self.state["next_inode"])
            self.state["next_inode"] += 1
            self.state["paths"][path], self.state["nodes"][inode] = inode, node
            self.state["names"][path] = PurePosixPath(args["path"]).name
            if operation == "open_new":
                handle = str(self.next_handle)
                self.next_handle += 1
                self.handles[handle] = {"owner": identity, "inode": inode, "path": path, "access": "write"}
                return {"inode": inode, "handle": handle}, [{"operation": "create", "path": path}]
            return {"inode": inode}, [{"operation": operation, "path": path}]
        if operation == "write":
            if not path.startswith("/work/"):
                raise Refusal("protected", "target is outside the writable volume subtree")
            _, node = self.lookup(path)
            if node["kind"] != "file" or node["uid"] != 501 or not node["mode"] & 0o200:
                raise Refusal("permission", "file cannot be written")
            return self.write_bytes(node, path, args)
        if operation == "chmod":
            if not path.startswith("/work/"):
                raise Refusal("protected", "target is outside the writable volume subtree")
            _, node = self.lookup(path)
            mode = args["mode"]
            if node["uid"] != 501 or node["kind"] == "symlink" or type(mode) is not int or not 0 <= mode <= 0o777:
                raise Refusal("permission", "mode change refused")
            node["mode"] = mode
            return None, [{"operation": "chmod", "path": path, "mode": mode}]
        if operation == "readlink":
            _, node = self.lookup(path)
            if node["kind"] != "symlink":
                raise Refusal("kind", "not a symbolic link")
            return {"target": node["target"]}, []
        if operation == "rename":
            destination = canonical(args["destination"])
            self.writable(path)
            self.writable(destination)
            inode, node = self.lookup(path)
            if destination.startswith(path + "/"):
                raise Refusal("path", "cannot move a directory into itself")
            if path == destination:
                self.state["names"][path] = PurePosixPath(args["destination"]).name
                return None, []
            replaced = self.state["paths"].get(destination)
            if replaced is not None:
                old = self.state["nodes"][replaced]
                if (node["kind"] == "directory") != (old["kind"] == "directory"):
                    raise Refusal("kind", "rename replacement kind mismatch")
                if any(child.startswith(destination + "/") for child in self.state["paths"]):
                    raise Refusal("not-empty", "replacement directory is not empty")
            moved = {key: value for key, value in self.state["paths"].items() if key == path or key.startswith(path + "/")}
            names = {key: self.state["names"].pop(key, PurePosixPath(key).name) for key in moved}
            for key in moved:
                del self.state["paths"][key]
            for key, value in moved.items():
                target = destination + key[len(path):]
                self.state["paths"][target] = value
                self.state["names"][target] = names[key]
            self.state["names"][destination] = PurePosixPath(args["destination"]).name
            return None, [{"operation": "rename", "source": path, "destination": destination, "inode": inode}]
        if operation in ("flush_file", "flush_directory"):
            inode, node = self.lookup(path)
            if node["kind"] != ("file" if operation == "flush_file" else "directory"):
                raise Refusal("kind", "flush kind mismatch")
            self.state["durable_nodes"][inode] = copy.deepcopy(node)
            if operation == "flush_directory":
                self.state["durable_dirs"][inode] = {
                    PurePosixPath(child).name: value for child, value in self.state["paths"].items()
                    if child != path and str(PurePosixPath(child).parent) == path}
                self.state["durable_names"][inode] = {
                    PurePosixPath(child).name: self.state["names"].get(child, PurePosixPath(child).name)
                    for child in self.state["paths"] if child != path and str(PurePosixPath(child).parent) == path}
                for child in self.state["durable_dirs"][inode].values():
                    if self.state["nodes"][child]["kind"] == "symlink":
                        self.state["durable_nodes"][child] = copy.deepcopy(self.state["nodes"][child])
            return None, [{"operation": operation, "path": path, "durable": True}]
        if operation == "unlink":
            self.writable(path)
            _, node = self.lookup(path)
            if node["kind"] == "directory" and any(
                    child.startswith(path + "/") for child in self.state["paths"]):
                raise Refusal("not-empty", "directory is not empty")
            del self.state["paths"][path]
            self.state["names"].pop(path, None)
            return None, [{"operation": operation, "path": path}]
        if operation in ("lock", "unlock"):
            inode, node = self.lookup(path)
            if node["kind"] != "file":
                raise Refusal("kind", "lock requires a regular file")
            if operation == "lock" and (node["uid"] != 501 or node["mode"] & 0o600 != 0o600):
                raise Refusal("permission", "lock file is not readable and writable by this process")
            if self.locks.get(inode) not in (None, identity):
                raise Refusal("busy", "lock held by another process")
            if operation == "lock":
                self.locks[inode] = identity
            else:
                self.locks.pop(inode, None)
            return None, [{"operation": operation, "path": path}]
        raise Refusal("unsupported", "filesystem operation is not modeled")

    def read_bytes(self, node, args):
        offset, length = args.get("offset", 0), args.get("length", len(node["hex"]) // 2)
        if type(offset) is not int or type(length) is not int or offset < 0 or length < 0:
            raise Refusal("offset", "invalid read bounds")
        maximum = self.state.get("maximum_read", length)
        if type(maximum) is not int or maximum < 0:
            raise Refusal("read", "invalid short-read limit")
        return {"hex": node["hex"][offset * 2:(offset + min(length, maximum)) * 2]}

    def write_bytes(self, node, path, args):
        data = bytes.fromhex(args["hex"])
        limit = self.state.get("maximum_write", len(data))
        if type(limit) is not int or (data and limit <= 0):
            raise Refusal("arguments", "invalid modeled write limit")
        data = data[:limit]
        offset = args.get("offset", 0)
        if type(offset) is not int or not 0 <= offset <= self.state["quota"]:
            raise Refusal("offset", "invalid write offset")
        old = bytes.fromhex(node["hex"])
        live = set(self.state["paths"].values()) | {handle["inode"] for handle in self.handles.values()}
        used = sum(len(self.state["nodes"][inode].get("hex", "")) // 2 for inode in live)
        size = max(len(old), offset + len(data))
        if used - len(old) + size > self.state["quota"]:
            raise Refusal("no-space", "simulated volume quota exhausted")
        contents = bytearray(old.ljust(size, b"\x00"))
        contents[offset:offset + len(data)] = data
        node["hex"] = contents.hex()
        return {"written": len(data)}, [{"operation": "write", "path": path, "bytes": len(data)}]

    def execute(self, identity, capabilities, request):
        with self.mutex:
            if (set(request) != {"version", "id", "capability", "operation", "arguments", "preconditions"}
                    or request["version"] != 1 or type(request["id"]) is not int
                    or not 0 < request["id"] < 2**53 or not isinstance(request["arguments"], dict)
                    or not isinstance(request["preconditions"], dict)
                    or not isinstance(request["capability"], str) or not isinstance(request["operation"], str)):
                raise Refusal("protocol", "invalid request envelope")
            key = identity + ":" + str(request["id"])
            if key in self.state["outcomes"]:
                raise Refusal("duplicate", "request ID already used; query outcome instead of retrying")
            self.state["tick"] += 1
            tick = self.state["tick"]
            fault = next((item for item in self.state["faults"] if not item.get("fired") and
                          (item.get("tick") == tick or (request["capability"] == "process" and
                           request["operation"] == "checkpoint" and item.get("checkpoint") == request["arguments"].get("name")))), None)
            if fault:
                fault["fired"] = True
            self.stop_kind = None
            response = {"version": 1, "id": request["id"], "result": None, "effects": [],
                        "receipt": {"identity": identity, "tick": tick}, "failure": None}
            try:
                capability, operation = request["capability"], request["operation"]
                if capability not in capabilities:
                    raise Refusal("capability", "process lacks requested capability")
                if request["preconditions"]:
                    raise Refusal("unsupported", "preconditions not yet modeled")
                if fault and fault["kind"] == "before":
                    raise Refusal("injected", "failure before operation")
                if capability == "filesystem":
                    response["result"], response["effects"] = self.filesystem(identity, operation, request["arguments"])
                elif capability == "machine" and operation == "observe":
                    response["result"] = copy.deepcopy(self.state["target"])
                elif capability == "clock" and operation == "observe":
                    response["result"] = {"tick": tick}
                elif capability == "process" and operation == "observe":
                    response["result"] = {"uid": 501, "gid": 20, "identity": identity}
                elif capability == "process" and operation == "umask":
                    mask = request["arguments"]["mask"]
                    if type(mask) is not int or not 0 <= mask <= 0o777:
                        raise Refusal("mode", "invalid umask")
                    self.masks[identity] = mask
                    response["result"] = {"mask": mask}
                elif capability == "process" and operation == "checkpoint":
                    response["result"] = {"name": request["arguments"]["name"]}
                elif capability == "outcome" and operation == "lookup":
                    response["result"] = copy.deepcopy(self.state["outcomes"].get(
                        identity + ":" + str(request["arguments"]["id"])))
                else:
                    raise Refusal("unsupported", "platform capability is not modeled")
                if fault and fault["kind"] == "after":
                    raise Refusal("injected", "failure after effect")
            except (Refusal, KeyError, TypeError, ValueError) as error:
                response["failure"] = {"code": getattr(error, "code", "arguments"), "message": str(error)}
            self.state["outcomes"][key] = copy.deepcopy(response)
            self.save()
            if fault and fault["kind"] == "power_loss":
                self.power_loss()
            if fault and fault["kind"] in ("lost_ack", "power_loss", "terminate"):
                self.stop_kind = fault["kind"]
            return response, self.stop_kind is not None
