"""Check supplied corpus identities. Ingestion never establishes compatibility."""

import struct
from pathlib import Path, PurePosixPath

from .darwin import no_links, sha256
from .requirements import load_json

ROLES = {"cli", "cocoa", "document", "debugger"}
LIMIT = 512 * 1024 * 1024


def macho_uuid(path, filetype=2):
    """Read thin Intel Mach-O headers/UUIDs, including a dSYM's DWARF file.

    Universal files are deliberately refused. Supply a thin upstream artifact
    or build thin on a Mac; never rewrite an executable to pass execution gates.
    """
    with Path(path).open("rb") as stream:
        header = stream.read(32)
        if len(header) != 32:
            raise ValueError("truncated Mach-O header")
        magic, cpu, _, kind, count, size, _, _ = struct.unpack("<8I", header)
        if magic != 0xFEEDFACF or cpu != 0x01000007 or kind != filetype:
            raise ValueError(
                "expected a thin x86-64 Mach-O executable or matching dSYM"
            )
        if size > 16 * 1024 * 1024 or count > size // 8:
            raise ValueError("invalid Mach-O load command bounds")
        commands = stream.read(size)
        if len(commands) != size:
            raise ValueError("truncated Mach-O load commands")
    offset, identity = 0, None
    for _ in range(count):
        if offset + 8 > size:
            raise ValueError("truncated Mach-O command")
        command, length = struct.unpack_from("<2I", commands, offset)
        if length < 8 or length % 8 or offset + length > size:
            raise ValueError("invalid Mach-O command size")
        if command == 0x1B:
            if length != 24 or identity is not None:
                raise ValueError("invalid or duplicate Mach-O UUID")
            identity = commands[offset + 8 : offset + 24].hex()
        offset += length
    if offset != size or identity is None:
        raise ValueError("missing Mach-O UUID or inconsistent command table")
    return identity


def artifact(root, record):
    if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
        raise ValueError("artifact requires path and sha256")
    relative = record["path"]
    if (
        not isinstance(relative, str)
        or not relative
        or "\\" in relative
        or ":" in relative
        or PurePosixPath(relative).is_absolute()
        or any(p in ("", ".", "..") for p in relative.split("/"))
    ):
        raise ValueError("artifact must be a relative corpus path")
    path = no_links(root / relative)
    if not path.is_file() or path.stat().st_size > LIMIT:
        raise ValueError("artifact missing or larger than 512 MiB")
    if sha256(path) != record["sha256"]:
        raise ValueError(f"artifact hash mismatch: {relative}")
    return path


def verify(path):
    path = no_links(path)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("corpus manifest exceeds 1 MiB")
    corpus = load_json(path)
    if (
        not isinstance(corpus, dict)
        or set(corpus) != {"version", "entries"}
        or type(corpus["version"]) is not int
        or corpus["version"] != 1
    ):
        raise ValueError("unsupported corpus manifest")
    if not isinstance(corpus["entries"], list) or len(corpus["entries"]) > 32:
        raise ValueError("invalid corpus entries")
    roles, entries = set(), []
    for entry in corpus["entries"]:
        if not isinstance(entry, dict) or set(entry) != {
            "role",
            "binary",
            "source",
            "license",
            "symbols",
            "build",
            "expected",
        }:
            raise ValueError("invalid corpus entry")
        role = entry["role"]
        if not isinstance(role, str) or role not in ROLES or role in roles:
            raise ValueError("unknown or duplicate corpus role")
        roles.add(role)
        binary = artifact(path.parent, entry["binary"])
        artifact(path.parent, entry["source"])
        artifact(path.parent, entry["license"])
        identity = macho_uuid(binary)
        symbols = entry["symbols"]
        if symbols is not None:
            if macho_uuid(artifact(path.parent, symbols), filetype=10) != identity:
                raise ValueError("debug symbols do not match executable UUID")
        elif role == "debugger":
            raise ValueError("debugger corpus requires matching symbols")
        build = entry["build"]
        if not isinstance(build, dict) or set(build) != {
            "host",
            "compiler",
            "sdk",
            "command",
        }:
            raise ValueError(
                "build provenance requires host, compiler, sdk and command"
            )
        if any(
            not isinstance(value, str) or not value.strip() for value in build.values()
        ):
            raise ValueError("empty build provenance")
        if build["host"] not in ("macOS", "Darling"):
            raise ValueError("unknown build host; declare macOS or Darling")
        if not isinstance(entry["expected"], str) or not entry["expected"].strip():
            raise ValueError("expected behavior is required")
        entries.append(
            {
                "role": role,
                "binary_sha256": entry["binary"]["sha256"],
                "uuid": identity,
                "declared_build": build,
                "compatibility_candidate": build["host"] == "macOS",
                "provenance_verified": False,
                "execution": "pending",
            }
        )
    return {
        "version": 1,
        "manifest_sha256": sha256(path),
        "entries": entries,
        "missing_roles": sorted(ROLES - roles),
        "complete": False,
        "reason": "identity checks only; build provenance and CLI/GUI/debugger execution remain unverified",
    }
