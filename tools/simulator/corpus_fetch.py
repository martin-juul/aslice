"""Explicit provisioning download of a pinned redistributable CLI candidate.

No downloaded code is executed. General archive extraction is never used.
"""

import os
from pathlib import Path
import tarfile
import urllib.request

from .corpus import verify
from .darwin import no_links, sha256
from .model import atomic_json

RELEASE = "https://github.com/sharkdp/hyperfine/releases/download/v1.20.0/hyperfine-v1.20.0-x86_64-apple-darwin.tar.gz"
RELEASE_SHA256 = "f58d0b90993fadfa122a351428c469ce24afef3865f027f0e6e86f0830d088f1"
SOURCE = "https://codeload.github.com/sharkdp/hyperfine/tar.gz/975fe108c4ee7bd2600d10758207b44ca3dae738"
SOURCE_SHA256 = "ab62661c633a4461311381c532af8a35d55040a77487fd44fffb095965f2f265"
MAX_DOWNLOAD = 16 * 1024 * 1024


def download(url, digest, destination):
    temporary = destination.with_suffix(destination.suffix + ".partial")
    total = 0
    with urllib.request.urlopen(url, timeout=30) as response, temporary.open(
        "xb"
    ) as output:
        while True:
            block = response.read(64 * 1024)
            if not block:
                break
            total += len(block)
            if total > MAX_DOWNLOAD:
                raise ValueError("provisioning download exceeds 16 MiB")
            output.write(block)
        output.flush()
        os.fsync(output.fileno())
    if sha256(temporary) != digest:
        raise ValueError("provisioning download hash mismatch; partial file retained")
    os.replace(temporary, destination)


def fetch(output):
    output = no_links(output)
    output.mkdir(parents=True, exist_ok=False)
    release = output / "release.tar.gz"
    source = output / "source.tar.gz"
    download(RELEASE, RELEASE_SHA256, release)
    download(SOURCE, SOURCE_SHA256, source)
    with tarfile.open(release, "r:gz") as archive:
        for filename in ("hyperfine", "LICENSE-MIT", "LICENSE-APACHE"):
            member = archive.getmember(
                "hyperfine-v1.20.0-x86_64-apple-darwin/" + filename
            )
            if not member.isfile() or not 0 < member.size <= MAX_DOWNLOAD:
                raise ValueError("unexpected release artifact type or size")
            with archive.extractfile(member) as stream, (output / filename).open(
                "xb"
            ) as target:
                data = stream.read(MAX_DOWNLOAD + 1)
                if len(data) != member.size:
                    raise ValueError("release artifact length mismatch")
                target.write(data)
                target.flush()
                os.fsync(target.fileno())

    def record(filename):
        return {"path": filename, "sha256": sha256(output / filename)}

    entry = {
        "role": "cli",
        "binary": record("hyperfine"),
        "source": record("source.tar.gz"),
        "license": record("LICENSE-MIT"),
        "symbols": None,
        "build": {
            "host": "macOS",
            "compiler": "upstream stable Rust; exact version not captured in release archive",
            "sdk": "upstream macos-15 runner; exact SDK not captured in release archive",
            "command": "cargo build --locked --release --target=x86_64-apple-darwin",
        },
        "expected": "In a writable guest directory, run --warmup 0 --runs 1 --export-json result.json "
        "'printf corpus > child.txt'. Expect exit 0, a JSON result and child.txt containing corpus. "
        "Record observed subprocesses and filesystem effects; do not compare elapsed time deterministically.",
    }
    atomic_json(output / "corpus.json", {"version": 1, "entries": [entry]})
    atomic_json(
        output / "acquisition.json",
        {
            "version": 1,
            "release_url": RELEASE,
            "release_sha256": RELEASE_SHA256,
            "source_url": SOURCE,
            "source_sha256": SOURCE_SHA256,
            "build_provenance": "source archive .github/workflows/CICD.yml declares macos-15",
            "executed": False,
            "licenses": [record("LICENSE-MIT"), record("LICENSE-APACHE")],
        },
    )
    return verify(output / "corpus.json")
