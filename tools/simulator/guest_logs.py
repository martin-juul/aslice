"""Read guest macOS logging stores using their own tools, never host logs."""

import hashlib
import json
from pathlib import Path
import plistlib
import selectors
import signal
import subprocess
import os
import time

SOURCES = {
    'asl': ['/usr/bin/syslog', '-F', 'xml', '-k', 'Time', 'ge', '-5m'],
    'unified': ['/usr/bin/log', 'show', '--style', 'json', '--last', '5m', '--info', '--debug'],
    'system': ['/usr/bin/tail', '-n', '500', '/var/log/system.log'],
}
LIMIT = 1024 * 1024


def capture(command, user, home):
    """Bound time and output while running fixed commands as the guest user."""
    environment = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': user.pw_dir,
                   'USER': user.pw_name, 'LOGNAME': user.pw_name,
                   'DPREFIX': str(home / '.darling'), 'LANG': 'C.UTF-8'}
    child = subprocess.Popen(['/usr/local/bin/darling', 'shell', *command],
                             stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True,
                             user=user.pw_uid, group=user.pw_gid, extra_groups=[],
                             cwd=user.pw_dir, env=environment)
    data = {'stdout': bytearray(), 'stderr': bytearray()}
    deadline = time.monotonic() + 5
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ, 'stdout')
            selector.register(child.stderr, selectors.EVENT_READ, 'stderr')
            while selector.get_map():
                if time.monotonic() > deadline:
                    raise ValueError('Guest log query exceeded five seconds.')
                for key, _ in selector.select(0.1):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        data[key.data].extend(chunk)
                        if sum(len(value) for value in data.values()) > LIMIT:
                            raise ValueError('Guest log query exceeded 1 MiB; narrow the guest logging volume.')
            code = child.wait(timeout=max(0.1, deadline - time.monotonic()))
            if code:
                raise ValueError('Guest logging source unavailable: ' + data['stderr'].decode('utf8', 'replace')[-1000:])
            return bytes(data['stdout'])
    finally:
        # Reap this query and any helpers even when its reader or deadline fails.
        if child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        child.wait()
        child.stdout.close()
        child.stderr.close()


def records(source, data):
    if len(data) > LIMIT:
        raise ValueError('Log response exceeds 1 MiB.')
    if source == 'asl':
        values = plistlib.loads(data)
    elif source == 'unified':
        values = json.loads(data)
    else:
        values = [{'Message': line} for line in data.decode('utf8', 'replace').splitlines()]
    if not isinstance(values, list) or any(not isinstance(value, dict) for value in values):
        raise ValueError('Guest returned an unsupported log format.')
    result = []
    for value in values[-500:]:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True)
        priority = str(value.get('Level', ''))
        kind = value.get('messageType', {'0': 'fault', '1': 'fault', '2': 'fault',
                         '3': 'error', '4': 'warning', '5': 'default', '6': 'info', '7': 'debug'}.get(priority, 'default'))
        result.append({'id': hashlib.sha256(raw.encode()).hexdigest(),
                       'time': str(value.get('timestamp', value.get('Time', ''))),
                       'process': str(value.get('Sender', Path(str(value.get('processImagePath', ''))).name)),
                       'pid': str(value.get('processID', value.get('PID', ''))),
                       'type': str(kind).lower(), 'subsystem': str(value.get('subsystem', '')),
                       'category': str(value.get('category', value.get('Facility', ''))),
                       'message': str(value.get('eventMessage', value.get('Message', ''))), 'raw': raw})
    return result, len(values) > 500


def read(source, user, home):
    if source not in SOURCES:
        raise ValueError('Unknown guest log source.')
    try:
        rows, truncated = records(source, capture(SOURCES[source], user, home))
        if source == 'asl' and not rows:
            try:
                definition = plistlib.loads(capture(
                    ['/bin/cat', '/System/Library/LaunchDaemons/com.apple.syslogd.plist'], user, home))
            except (OSError, ValueError, subprocess.SubprocessError, plistlib.InvalidFileException):
                definition = {}
            if isinstance(definition, dict) and definition.get('Disabled') is True:
                try:
                    capture(['/bin/launchctl', 'list', 'com.apple.syslogd'], user, home)
                except (OSError, ValueError, subprocess.SubprocessError):
                    return {'source': source, 'available': False, 'records': [], 'truncated': False,
                            'note': 'ASL logging is unavailable: syslogd is disabled in the guest launch configuration and no loaded job was found. An empty syslog query does not prove logging works.'}
        return {'source': source, 'available': True, 'records': rows, 'truncated': truncated,
                'note': 'Guest logging store; latest five minutes (system.log: last 500 lines). Only messages visible to the guest account are returned.' +
                        (' No records returned; message ingestion has not been verified.' if not rows else '')}
    except (OSError, ValueError, subprocess.SubprocessError, plistlib.InvalidFileException) as error:
        return {'source': source, 'available': False, 'records': [], 'truncated': False,
                'note': str(error) + ' The compatibility runtime may not implement this logging facility.'}
