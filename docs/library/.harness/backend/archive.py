"""Preserve original responses and verify every stored byte."""

import hashlib
import json
from pathlib import Path
import re
import shutil

LIBRARY = Path(__file__).resolve().parents[2]


def collection(name):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError("Use a lowercase collection name separated by hyphens")
    return LIBRARY / name


def import_capture(source, name, title, entry_url):
    source = Path(source).resolve()
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get(entry_url, {}).get("status") != "captured":
        raise ValueError("The entry page has not been captured")
    destination = collection(name)
    previous_manifest = destination / "manifest.json"
    if previous_manifest.exists():
        previous = json.loads(previous_manifest.read_text(encoding="utf-8"))
        for url, old in previous.items():
            if old["status"] != "captured":
                continue
            new = manifest.get(url, {})
            if (
                new.get("status") != "captured"
                or new.get("sha256") != old["sha256"]
                or new.get("effective_url") != old.get("effective_url")
            ):
                raise ValueError(
                    "Use a new collection for a different source revision: " + url
                )
    originals = destination / "originals"
    originals.mkdir(parents=True, exist_ok=True)
    for entry in manifest.values():
        for field in ("body", "headers"):
            filename = entry.get(field)
            if not filename:
                continue
            if not re.fullmatch(r"[0-9a-f]{64}\.(body|headers)", filename):
                raise ValueError(f"Invalid original filename: {filename}")
            path = source / filename
            if (
                not path.exists()
                and field == "headers"
                and entry["status"] != "captured"
            ):
                continue
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"Missing original: {path}")
            if (
                field == "body"
                and hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]
            ):
                raise ValueError(f"Original changed during capture: {path}")
            shutil.copyfile(path, originals / filename)
    metadata = {"title": title, "entry_url": entry_url, "format_version": 1}
    (destination / "capture.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    lines = []
    for path in sorted(destination.rglob("*")):
        if path.is_file() and path != destination / "SHA256SUMS":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.relative_to(destination).as_posix()}")
    (destination / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    verify(destination)
    return destination


def verify(directory):
    directory = Path(directory).resolve()
    expected = set()
    for line in (directory / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, filename = line.split("  ", 1)
        path = directory / filename
        if path.is_symlink() or not path.resolve().is_relative_to(directory):
            raise ValueError(f"Invalid archive path: {filename}")
        if (
            filename in expected
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise ValueError(f"Checksum mismatch: {filename}")
        expected.add(filename)
    actual = {
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_file() and path != directory / "SHA256SUMS"
    }
    if actual != expected:
        raise ValueError("Archive file inventory differs from SHA256SUMS")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest.values():
        if entry.get("body"):
            body = directory / "originals" / entry["body"]
            if hashlib.sha256(body.read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError(f"Response digest mismatch: {entry['url']}")
    return len(expected)
