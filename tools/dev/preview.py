"""Compiled simulator demo without Node or a live VM controller."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
import webbrowser


def make_server(directory, port):
    directory = Path(directory).resolve()

    class Handler(SimpleHTTPRequestHandler):
        def translate_path(self, path):
            path = unquote(urlsplit(path).path)
            if path.startswith('/static/'):
                path = path[len('/static/'):]
            target = (directory / path.lstrip('/')).resolve()
            if not target.is_relative_to(directory):
                return str(directory / '__refused__')
            return str(target)

        def list_directory(self, _path):
            self.send_error(404)
            return None

        def log_message(self, *_args):
            pass

    class Server(ThreadingHTTPServer):
        allow_reuse_address = False
        allow_reuse_port = False

    return Server(('127.0.0.1', port), Handler)


def preview(directory, port, browser=True):
    with make_server(directory, port) as server:
        url = f'http://127.0.0.1:{server.server_port}/'
        print(f'Simulator console demo (sample data, no VM): {url}', flush=True)
        if browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
