"""Application lifecycle shared by the source and packaged launchers."""

import argparse
import importlib.util
import json
from pathlib import Path
import time
import webbrowser

from tools.dev.process import state_root
from . import controller


def shutdown(root, stop_machines=False):
    if not (root / '.controller/endpoint.json').exists():
        return {'stopped': True, 'controller': 'not running'}
    if stop_machines:
        status = controller.request(root, 'status')
        for machine in status['machines']:
            if machine.get('supervisor_alive') or machine['state'] in ('starting', 'running', 'stopping'):
                result = controller.request(root, 'stop', name=machine['name'], timeout=30)
                if not result.get('observed'):
                    raise ValueError(f'Shutdown of {machine["name"]} was not observed; controller preserved.')
    controller.request(root, 'controller-stop', _timeout=5)
    deadline = time.monotonic() + 10
    while (root / '.controller/endpoint.json').exists():
        if time.monotonic() >= deadline:
            raise ValueError('Controller shutdown was not confirmed; inspect its startup.log.')
        time.sleep(0.1)
    return {'stopped': True, 'machines': 'stopped' if stop_machines else 'preserved'}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Launch or reconnect to the aslice Simulator application.')
    parser.add_argument('action', choices=('open', 'status', 'shutdown'), nargs='?', default='open')
    parser.add_argument('--root', type=Path, default=state_root())
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--stop-machines', action='store_true', help='gracefully stop machines before shutting down the controller')
    args = parser.parse_args(argv)
    if args.stop_machines and args.action != 'shutdown':
        parser.error('--stop-machines applies only to shutdown')
    if args.action == 'shutdown':
        print(json.dumps(shutdown(args.root, args.stop_machines), indent=2))
        return 0
    if args.action == 'status':
        print(json.dumps(controller.request(args.root, 'status', _timeout=5), indent=2))
        return 0
    if importlib.util.find_spec('aiohttp') is None:
        raise ValueError('Install application dependencies: python simulator.py setup (source checkout: python dev.py simulator setup).')
    if not all((controller.WEB / name).is_file() for name in ('index.html', 'app.js', 'app.css')):
        raise ValueError('Compiled console assets are missing. Rebuild the application package.')
    root = controller.ensure(args.root)
    endpoint = json.loads((root / '.controller/endpoint.json').read_text())
    url = f'http://127.0.0.1:{endpoint["port"]}/#{endpoint["token"]}'
    print('aslice Simulator — Darwin compatibility environment')
    print('Closing the window preserves machines and sessions. Use shutdown to stop the controller.')
    print(url, flush=True)
    if not args.no_browser and not webbrowser.open(url):
        print('No browser could be opened. Open the URL above in your browser.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        import sys
        print(f'Simulator: {error}', file=sys.stderr)
        raise SystemExit(2)
