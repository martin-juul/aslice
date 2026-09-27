"""Portable Windows/Linux application archive with compiled, offline UI assets."""

import hashlib
import os
from pathlib import Path
import zipfile


LAUNCHER = '''#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess
import sys

if sys.version_info < (3, 11):
    raise SystemExit('aslice Simulator requires Python 3.11 or newer.')
root = Path(__file__).resolve().parent
os.chdir(root)
environment = root / '.venv'
python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
if sys.argv[1:2] == ['setup']:
    subprocess.run([sys.executable, '-m', 'venv', str(environment)], check=True)
    raise SystemExit(subprocess.call([str(python), '-m', 'pip', 'install', '-r', 'tools/simulator/runtime-requirements.txt']))
if python.is_file() and Path(sys.prefix).resolve() != environment.resolve():
    raise SystemExit(subprocess.call([str(python), str(Path(__file__).resolve()), *sys.argv[1:]]))
from tools.simulator.application import main
try:
    raise SystemExit(main())
except (OSError, ValueError) as error:
    print('Simulator: ' + str(error), file=sys.stderr)
    raise SystemExit(2)
'''


def package(root, output):
    root, output = Path(root), Path(output)
    assets = root / 'build/simulator-web'
    if not all((assets / name).is_file() for name in ('index.html', 'app.js', 'app.css')):
        raise ValueError('Build the simulator console before packaging.')
    files = {}
    for folder in ('tools/simulator', 'tools/dev'):
        for current, directories, names in os.walk(root / folder):
            directories[:] = [name for name in directories if name not in ('node_modules', '__pycache__', 'web')]
            for name in names:
                path = Path(current) / name
                files[path.relative_to(root).as_posix()] = path.read_bytes()
    for path in assets.rglob('*'):
        if path.is_file():
            files[path.relative_to(root).as_posix()] = path.read_bytes()
    files['tools/__init__.py'] = b''
    files['simulator.py'] = LAUNCHER.encode()
    files['Simulator.cmd'] = b'@echo off\r\npython "%~dp0simulator.py" %*\r\nif errorlevel 1 pause\r\n'
    files['simulator.sh'] = b'#!/bin/sh\nexec python3 "$(dirname "$0")/simulator.py" "$@"\n'
    files['LICENSE'] = (root / 'LICENSE').read_bytes()
    files['README.txt'] = b'''aslice Simulator (Windows and Linux development hosts)
Requires Python 3.11+ and a browser. Run python simulator.py setup once;
then launch Simulator.cmd, ./simulator.sh, or python simulator.py.
Node is not required. Setup downloads pinned Python dependencies.
VM execution additionally requires QEMU, SSH, and a provisioned runtime.
The application starts/reconnects its loopback controller and opens its UI.
Closing the browser preserves sessions and machines.
python simulator.py status
python simulator.py shutdown                 (preserves machines)
python simulator.py shutdown --stop-machines (graceful machine shutdown first)
Use --root PATH to reconnect to an existing simulator state directory.
This compatibility environment does not establish native macOS qualification.
See tools/simulator/DARWIN.md for provisioning and compatibility limits.
'''
    files['SHA256SUMS'] = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n'
                                for name, data in sorted(files.items())).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Refuse overwrites: an existing package may be retained evidence.
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo('aslice-simulator/' + name)
            info.external_attr = (0o100755 if name.endswith('.sh') else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    return output
