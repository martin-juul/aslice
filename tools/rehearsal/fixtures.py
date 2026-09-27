"""Harness-owned test inputs; never application decisions or recovery records."""
import copy
from pathlib import PurePosixPath

from .coverage import ROOT
from .model import canonical


def seed_input(model, target, content):
    path = canonical(target)
    if not path.startswith("/inputs/") or "/" in path[len("/inputs/"):]:
        raise ValueError("fixture inputs must be direct children of /inputs")
    if "/inputs" not in model.state["paths"]:
        inode = str(model.state["next_inode"])
        model.state["next_inode"] += 1
        node = model.node("directory", 0o500)
        model.state["paths"]["/inputs"] = inode
        model.state["nodes"][inode] = node
        model.state["durable_nodes"][inode] = copy.deepcopy(node)
        model.state["durable_dirs"]["1"]["inputs"] = inode
        model.state["durable_dirs"][inode] = {}
        model.state["names"]["/inputs"] = "inputs"
    parent = model.state["paths"]["/inputs"]
    inode = model.state["paths"].get(path)
    if inode is None:
        inode = str(model.state["next_inode"])
        model.state["next_inode"] += 1
    node = {**model.node("file", 0o400), "hex": content.hex()}
    model.state["paths"][path] = inode
    model.state["nodes"][inode] = node
    model.state["durable_nodes"][inode] = copy.deepcopy(node)
    name = PurePosixPath(path).name
    model.state["names"][path] = PurePosixPath(target).name
    model.state["durable_dirs"][parent][name] = inode
    model.state["durable_names"].setdefault(parent, {})[name] = PurePosixPath(target).name
    model.save()


def seed_catalogs(model):
    for version in (1, 2):
        name = f"catalog-v{version}.json"
        seed_input(model, "/inputs/" + name, (ROOT / "tests/fixtures/prototype" / name).read_bytes())
