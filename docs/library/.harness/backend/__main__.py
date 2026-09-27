"""Browse and verify captured documentation without external dependencies."""

import argparse

from .archive import collection, import_capture, verify
from .replay import make_server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("import-capture")
    capture.add_argument("source")
    capture.add_argument("name")
    capture.add_argument("--title", required=True)
    capture.add_argument("--entry-url", required=True)
    check = commands.add_parser("verify")
    check.add_argument("name")
    serve = commands.add_parser("serve")
    serve.add_argument("name")
    serve.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.command == "import-capture":
        print(import_capture(args.source, args.name, args.title, args.entry_url))
        return
    directory = collection(args.name)
    count = verify(directory)
    print(f"Verified {count} preserved files.")
    if args.command == "serve":
        with make_server(directory, args.port) as server:
            print(
                f"Browse http://127.0.0.1:{server.server_port}/__library/", flush=True
            )
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
