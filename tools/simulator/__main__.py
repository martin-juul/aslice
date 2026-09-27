import argparse
import json
from pathlib import Path
import sys
import subprocess

from . import darwin
from .coverage import report
from .harness import Workspace, launch, replay, run
from .requirements import native_evidence


def main():
    parser = argparse.ArgumentParser(
        description="Modeled platform tests and persistent Darwin compatibility machines"
    )
    commands = parser.add_subparsers(dest="action", required=True)
    darwin.add_commands(commands)
    for name in ("run", "client", "replay"):
        command = commands.add_parser(name)
        command.add_argument("--workspace", type=Path, required=True)
        command.add_argument("--aslice", type=Path, required=True)
        if name == "run":
            command.add_argument(
                "--suite",
                choices=("foundation", "fixture", "helper", "full"),
                default="full",
            )
            command.add_argument("--seed", type=int, default=0)
            command.add_argument("--native-evidence", type=Path)
            command.add_argument("--helper-driver", type=Path)
        elif name == "client":
            command.add_argument("command", nargs=argparse.REMAINDER)
        else:
            command.add_argument("--trace", type=Path, required=True)
            command.add_argument("--helper-driver", type=Path)
    coverage = commands.add_parser("coverage")
    coverage.add_argument("--json", action="store_true")
    coverage.add_argument(
        "--gate", choices=("development", "release"), default="release"
    )
    coverage.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "console":
        from .machine_cli import console

        return console(args)
    if args.action == "machine":
        return darwin.dispatch(args)
    if args.action == "coverage":
        result = report()
        encoded = json.dumps(result, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded, encoding="utf-8")
        else:
            print(encoded, end="")
        return (
            0
            if result["development_valid" if args.gate == "development" else "complete"]
            else 1
        )
    supplied_evidence = None
    if args.action == "run" and args.suite == "helper" and args.helper_driver is None:
        parser.error("--suite helper requires --helper-driver")
    if (
        args.action == "run"
        and args.helper_driver is not None
        and args.suite not in ("helper", "full")
    ):
        parser.error("--helper-driver applies only to helper/full suites")
    if args.action == "run" and args.native_evidence:
        if args.suite != "full":
            parser.error("--native-evidence applies only to --suite full")
        # Validate before creating the workspace or launching an application.
        supplied_evidence = native_evidence(args.native_evidence)
    with Workspace(args.workspace) as workspace:
        if args.action == "run":
            return run(
                workspace,
                args.aslice,
                args.suite,
                args.seed,
                supplied_evidence,
                args.helper_driver,
            )
        if args.action == "replay":
            return replay(workspace, args.aslice, args.trace, args.helper_driver)
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        if not command:
            parser.error("client requires a command after --")
        code, stdout, stderr, _ = launch(workspace, args.aslice, command)
        sys.stdout.buffer.write(stdout)
        sys.stderr.buffer.write(stderr)
        return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"simulator: {error}", file=sys.stderr)
        sys.exit(2)
