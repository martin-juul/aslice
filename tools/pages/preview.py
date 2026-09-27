"""Portable loopback preview, including a project-site URL prefix."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2] / "build/pages"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--prefix", default="/aslice/")
    args = parser.parse_args()
    prefix = "/" + args.prefix.strip("/") + "/" if args.prefix.strip("/") else "/"
    if not (ROOT / "index.html").is_file():
        parser.error("Build the portal first; see tools/pages/README.md.")

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            if urlsplit(self.path).path == prefix.rstrip("/"):
                self.send_response(302)
                self.send_header("Location", prefix)
                self.end_headers()
                return
            if not self.path.startswith(prefix):
                self.send_error(404)
                return
            self.path = "/" + self.path[len(prefix) :]
            super().do_GET()

    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port), partial(Handler, directory=str(ROOT))
    )
    print(f"Preview: http://127.0.0.1:{server.server_port}{prefix}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
