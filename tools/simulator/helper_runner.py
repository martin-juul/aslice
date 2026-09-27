"""Schedule real C++ inspection peers; retain byte-channel setup for replay."""
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import queue
import re
import subprocess
import threading
import time

from .model import Model, atomic_json
from .server import Server

MAX_LINE = 1024 * 1024
MAX_STEPS = 4096


class Peer:
    def __init__(self, process):
        self.process = process
        self.lines = queue.Queue(maxsize=2)
        self.stdout = bytearray()
        self.stderr = bytearray()
        self.stopped = threading.Event()
        self.readers = [threading.Thread(target=self.read_output),
                        threading.Thread(target=self.read_errors)]
        for reader in self.readers:
            reader.start()

    def publish(self, value):
        while not self.stopped.is_set():
            try:
                self.lines.put(value, timeout=0.1)
                return
            except queue.Full:
                pass

    def read_output(self):
        try:
            for _ in range(MAX_STEPS + 2):
                line = self.process.stdout.readline(MAX_LINE + 1)
                if not line:
                    self.publish(EOFError('helper peer exited before a response'))
                    return
                if len(line) > MAX_LINE or not line.endswith(b'\n'):
                    raise ValueError('helper peer output exceeds line bound')
                if len(self.stdout) + len(line) > 16 * MAX_LINE:
                    raise ValueError('helper peer output exceeds total bound')
                self.stdout.extend(line)
                self.publish(line)
            raise ValueError('helper peer exceeded response count')
        except (OSError, ValueError) as error:
            self.publish(error)

    def read_errors(self):
        while chunk := self.process.stderr.read(4096):
            if len(self.stderr) + len(chunk) > MAX_LINE:
                self.process.kill()
                self.publish(ValueError('helper peer stderr exceeds bound'))
                return
            self.stderr.extend(chunk)

    def receive(self, deadline):
        try:
            value = self.lines.get(timeout=max(0, deadline - time.monotonic()))
        except queue.Empty as error:
            raise TimeoutError('helper scenario deadline expired') from error
        if isinstance(value, Exception):
            raise value
        result = json.loads(value)
        if not isinstance(result, dict):
            raise ValueError('helper response must be an object')
        return result

    def close(self):
        self.stopped.set()
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=5)
        for reader in self.readers:
            reader.join(timeout=5)
            if reader.is_alive():
                raise RuntimeError('helper output reader failed to stop')
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            stream.close()


def validate_schedule(schedule):
    if not isinstance(schedule, dict) or set(schedule) != {'actors', 'capacity', 'steps'}:
        raise ValueError('invalid helper replay schedule')
    actors = schedule['actors']
    if (not isinstance(actors, list) or len(actors) != 2 or actors[0] == actors[1]
            or not all(isinstance(actor, str) and re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', actor) for actor in actors)):
        raise ValueError('invalid helper actors')
    if type(schedule['capacity']) is not int or not 1 <= schedule['capacity'] <= 65536:
        raise ValueError('invalid helper channel capacity')
    steps = schedule['steps']
    if not isinstance(steps, list) or not 0 <= len(steps) <= MAX_STEPS:
        raise ValueError('invalid helper step count')
    for step in steps:
        if (not isinstance(step, dict) or set(step) != {'actor', 'action'}
                or step['actor'] not in actors or not isinstance(step['action'], dict)
                or step['action'].get('command') not in ('request', 'send', 'receive', 'inspect', 'verify')):
            raise ValueError('invalid helper step')
        if len(json.dumps(step['action'], allow_nan=False).encode()) > MAX_LINE - 1:
            raise ValueError('helper step exceeds input bound')


def inspection(workspace, executable, manifest=None, seed=0, *, baseline=None, schedule=None):
    # Replay schedules are validated before starting processes or altering OS state.
    if schedule is not None:
        validate_schedule(schedule)
    executable = Path(executable).resolve(strict=True)
    model = Model(workspace, seed)
    if baseline is not None:
        model.state = copy.deepcopy(baseline)
        model.save()
    before = copy.deepcopy(model.state)
    actors = (schedule['actors'] if schedule else
              [f'inspection-{role}-{model.state["tick"] + 1}' for role in ('manager', 'helper')])
    capacity = schedule['capacity'] if schedule else 257
    server = Server(model)
    peers = {}
    sessions = []
    steps, observations = [], []
    error, outcome = None, None
    deadline = time.monotonic() + 60

    def step(actor, action):
        if len(steps) >= MAX_STEPS:
            raise ValueError('helper scenario exceeds step limit')
        payload = json.dumps(action, allow_nan=False).encode() + b'\n'
        if len(payload) > MAX_LINE:
            raise ValueError('helper action exceeds input bound')
        # Inputs are bounded and the fixed driver waits for each command. The
        # watchdog also terminates peers blocked in a write or application work.
        peers[actor].process.stdin.write(payload)
        peers[actor].process.stdin.flush()
        steps.append({'actor': actor, 'action': copy.deepcopy(action)})
        result = peers[actor].receive(deadline)
        observations.append({'actor': actor, 'response': result})
        if 'error' in result or result.get('failure') is not None:
            raise ValueError(f'helper {action["command"]} failed')
        return result

    def transfer(sender, receiver, length):
        if type(length) is not int or not 0 < length <= MAX_LINE + 4:
            raise ValueError('invalid C++ frame length')
        transferred = 0
        while transferred < length:
            sent = step(sender, {'command': 'send'})
            if sent.get('failure') is not None or 'error' in sent:
                raise ValueError('helper send failed')
            count = sent['result']['written']
            if type(count) is not int or not 0 < count <= min(capacity, length - transferred):
                raise ValueError('invalid helper short-write result')
            received = step(receiver, {'command': 'receive', 'limit': count})
            if (received.get('failure') is not None or 'error' in received
                    or len(bytes.fromhex(received['result']['hex'])) != count):
                raise ValueError('helper receive failed')
            transferred += count

    expired = threading.Event()
    def expire():
        expired.set()
        for peer in list(peers.values()):
            if peer.process.poll() is None:
                peer.process.kill()
    watchdog = threading.Timer(60, expire)
    watchdog.start()
    try:
        descriptors = [server.issue(actor, ['channel']) for actor in actors]
        endpoints = server.inherit_channel(*actors, capacity)
        environment = os.environ.copy()
        environment.pop('ASLICE_PROTOTYPE_FAILPOINT', None)
        for actor, descriptor, endpoint in zip(actors, descriptors, endpoints):
            if expired.is_set() or time.monotonic() >= deadline:
                raise TimeoutError('helper scenario deadline expired')
            path = workspace / 'sessions' / (actor + '.json')
            with path.open('x', encoding='utf-8') as output:
                sessions.append(path)
                os.chmod(path, 0o600)
                json.dump(descriptor, output)
            process = subprocess.Popen([str(executable), str(path), endpoint], cwd=workspace,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment)
            peer = Peer(process)
            peers[actor] = peer
            server.attach_process(actor, process)
            greeting = peer.receive(deadline)
            if greeting.get('failure') is not None or greeting.get('result', {}).get('owner') != actor:
                raise ValueError('helper endpoint admission failed')
            observations.append({'actor': actor, 'greeting': greeting})
        if schedule is not None:
            for item in schedule['steps']:
                outcome = step(item['actor'], item['action'])
        else:
            request = step(actors[0], {'command': 'request', 'manifest': manifest})
            transfer(*actors, request['remaining'])
            response = step(actors[1], {'command': 'inspect'})
            transfer(actors[1], actors[0], response['remaining'])
            outcome = step(actors[0], {'command': 'verify'})
        for peer in peers.values():
            peer.process.stdin.close()
        for peer in peers.values():
            peer.process.wait(timeout=max(0.01, deadline - time.monotonic()))
    except (OSError, EOFError, ValueError, KeyError, TimeoutError, subprocess.TimeoutExpired) as failure:
        if isinstance(failure, (TimeoutError, subprocess.TimeoutExpired)):
            expired.set()
        error = 'helper scenario deadline expired' if expired.is_set() else str(failure)
    finally:
        watchdog.cancel()
        watchdog.join()
        termination = {actor: ('timeout' if expired.is_set() else
                       'harness-cleanup' if peer.process.poll() is None else None)
                       for actor, peer in peers.items()}
        server.close()
        for peer in peers.values():
            peer.close()
        for path in sessions:
            path.unlink(missing_ok=True)
    from .harness import source_identity
    processes = {actor: {'exit_status': peer.process.returncode, 'termination_kind': termination[actor], 'stdout_hex': peer.stdout.hex(),
                         'stderr_hex': peer.stderr.hex()} for actor, peer in peers.items()}
    passed = (error is None and not expired.is_set() and len(processes) == 2
              and all(value['exit_status'] == 0 and not value['stderr_hex'] for value in processes.values())
              and isinstance(outcome, dict) and outcome.get('effects') == []
              and isinstance(outcome.get('observations'), list) and len(outcome['observations']) == 1)
    trace = {'version': 1, 'qualification': 'simulated', 'execution_mode': 'cpp-helper-scenario',
             'source': source_identity(), 'host': {'system': platform.system(), 'machine': platform.machine()},
             'executable_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
             'schedule': {'actors': actors, 'capacity': capacity, 'steps': steps},
             'initial_state': before, 'final_state': copy.deepcopy(model.state),
             'requests': server.transcript, 'observations': observations, 'processes': processes,
             'passed': passed, 'error': error, 'timed_out': expired.is_set()}
    path = workspace / 'evidence' / (actors[0] + '.json')
    suffix = 2
    while path.exists():
        path = workspace / 'evidence' / (actors[0] + f'-{suffix}.json')
        suffix += 1
    atomic_json(path, trace)
    return {'passed': passed, 'trace': path.name, 'error': error}, path
