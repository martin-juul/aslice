"""Build the checked corpus on a Mac with its native SDK; never download an SDK."""

import argparse
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.simulator.darwin import sha256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != "Darwin":
        parser.error(
            "requires a Mac and its native SDK; Darling-built artifacts do not establish compatibility"
        )
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).parent
    for path in (
        source / "cli.c",
        source / "cocoa.m",
        source / "execve_empty_environment.c",
        ROOT / "LICENSE",
    ):
        shutil.copyfile(path, output / path.name)
    compiler = subprocess.check_output(
        ["xcrun", "clang", "--version"], text=True
    ).strip()
    sdk = subprocess.check_output(["xcrun", "--show-sdk-path"], text=True).strip()
    sdk_version = subprocess.check_output(
        ["xcrun", "--show-sdk-version"], text=True
    ).strip()

    def record(path):
        return {"path": path.relative_to(output).as_posix(), "sha256": sha256(path)}

    def compile_probe(binary, source_name, options=()):
        command = [
            "xcrun",
            "clang",
            "-arch",
            "x86_64",
            "-mmacosx-version-min=10.11",
            "-O0",
            "-g",
            "-isysroot",
            sdk,
            str(output / source_name),
            "-o",
            str(binary),
            *options,
        ]
        subprocess.run(command, check=True)
        subprocess.run(["xcrun", "dsymutil", str(binary)], check=True)
        return command

    entries = []
    for role in ("cli", "cocoa", "document", "debugger"):
        source_name = "cli.c" if role in ("cli", "debugger") else "cocoa.m"
        binary = output / role
        options = []
        if source_name == "cocoa.m":
            options = [
                "-fobjc-arc",
                "-framework",
                "Cocoa",
                "-DDOCUMENT=" + str(int(role == "document")),
            ]
        command = compile_probe(binary, source_name, options)
        symbols = output / (role + ".dSYM") / "Contents/Resources/DWARF" / role
        expected = {
            "cli": "Exit 0; child=41 then parent=42; corpus.txt contains persistent corpus followed by newline.",
            "cocoa": "Visible window; keyboard input, Apply button and Apply menu copy the unique input to the result.",
            "document": "Visible open/save dialogs; save unique text; restart machine; open the same document and verify text.",
            "debugger": "LLDB launch and attach; source-map; parent_marker and exec child_marker breakpoints; step, threads, stack, value inspection.",
        }[role]
        entries.append(
            {
                "role": role,
                "source": record(output / source_name),
                "binary": record(binary),
                "license": record(output / "LICENSE"),
                "symbols": record(symbols),
                "expected": expected,
                "build": {
                    "host": "macOS",
                    "compiler": compiler,
                    "sdk": sdk_version,
                    "command": json.dumps(command),
                },
            }
        )
    (output / "corpus.json").write_text(
        json.dumps({"version": 1, "entries": entries}, indent=2) + "\n"
    )

    binary = output / "execve-empty-environment"
    command = compile_probe(binary, "execve_empty_environment.c")
    reproduction = {
        "source": record(output / "execve_empty_environment.c"),
        "binary": record(binary),
        "license": record(output / "LICENSE"),
        "symbols": record(
            output / (binary.name + ".dSYM") / "Contents/Resources/DWARF" / binary.name
        ),
        "expected": "Exit 0 and print empty-environment followed by a newline.",
        "build": {
            "host": "macOS",
            "compiler": compiler,
            "sdk": sdk_version,
            "command": json.dumps(command),
        },
    }
    (output / "runtime-reproductions.json").write_text(
        json.dumps({"version": 1, "entries": [reproduction]}, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
