"""Argument-vector execution with retained logs and child cleanup."""

from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]


def executable(name, dry_run=False):
    override = os.environ.get('ASLICE_' + name.upper().replace('-', '_'))
    found = shutil.which(override or name)
    if not found and name in ('cmake', 'ctest') and os.name == 'nt':
        candidate = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/CLion/bin/cmake/win/x64/bin' / (name + '.exe')
        if candidate.is_file():
            found = str(candidate)
    if found:
        return found
    if dry_run:
        return override or name
    raise ValueError(f'{name} was not found. Install it or set ASLICE_{name.upper().replace("-", "_")} to its executable.')


class Runner:
    def __init__(self, dry_run=False, root=ROOT):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(errors='replace')
        self.root = Path(root)
        self.dry_run = dry_run
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        self.report = self.root / 'build/reports' / (stamp + '-' + uuid.uuid4().hex[:8])
        self.steps = 0

    def tool(self, name):
        return executable(name, self.dry_run)

    def run(self, arguments, cwd=None, retain=True):
        arguments = [str(argument) for argument in arguments]
        cwd = Path(cwd or self.root)
        print(f'[{cwd}] {subprocess.list2cmdline(arguments)}', flush=True)
        if self.dry_run:
            return
        self.steps += 1
        log = None
        if retain:
            self.report.mkdir(parents=True, exist_ok=True)
            path = self.report / f'{self.steps:02d}.log'
            log = path.open('w', encoding='utf-8')
            print(f'Log: {path}', flush=True)
        child = None
        try:
            child = subprocess.Popen(arguments, cwd=cwd, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True,
                                     encoding='utf-8', errors='replace',
                                     start_new_session=os.name != 'nt')
            for line in child.stdout:
                print(line, end='', flush=True)
                if log:
                    log.write(line)
                    log.flush()
            result = child.wait()
            if result:
                raise subprocess.CalledProcessError(result, arguments)
        except BaseException:
            if child and child.poll() is None:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if os.name == 'nt':
                        child.kill()
                    else:
                        os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
            raise
        finally:
            if child and child.stdout:
                child.stdout.close()
            if log:
                log.close()


def state_root():
    if os.environ.get('ASLICE_SIMULATOR_HOME'):
        return Path(os.environ['ASLICE_SIMULATOR_HOME']).expanduser().absolute()
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/aslice/simulator'
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'aslice/simulator'
    return Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'aslice/simulator'
