"""Probe a running compatibility guest without replacing or restarting its agent."""

import argparse
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import time
import uuid

from tools.simulator.controller import Controller


async def probe(directory):
    directory = Path(directory).resolve(strict=True)
    client = Controller(directory.parent)
    client.directory = lambda _name: directory

    async def request(action, **fields):
        return await client.guest(directory.name, {'action': action, **fields})

    before = await request('health')
    active = [item['id'] for item in before['sessions'] if item['exit_code'] is None]
    source = Path(__file__).resolve().parents[1] / 'simulator/guest_logs.py'
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    filename = f'console-probe-{digest[:16]}-{uuid.uuid4().hex[:8]}.py'
    transfer = await request('import-begin', path=filename, size=len(data), sha256=digest, executable=False)
    try:
        await request('import-chunk', transfer=transfer['transfer'], offset=0, data=base64.b64encode(data).decode())
        await request('import-commit', transfer=transfer['transfer'])
    except BaseException:
        await request('import-abort', transfer=transfer['transfer'])
        raise
    marker = 'aslice-console-probe-' + uuid.uuid4().hex
    guest_file = '/home/aslice/.darling/Users/aslice/Imports/' + filename
    code = f'''import importlib.util,json,pwd
from pathlib import Path
spec=importlib.util.spec_from_file_location('reader',{guest_file!r})
reader=importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
user=pwd.getpwnam('aslice')
home=Path('/home/aslice')
result={{'marker':{marker!r},'reader_sha256':{digest!r}}}
result['diagnostics']={{}}
for label,command in [('daemon-files',['/bin/ls','-ld','/usr/sbin/syslogd','/System/Library/LaunchDaemons/com.apple.syslogd.plist']),('daemon-definition',['/bin/cat','/System/Library/LaunchDaemons/com.apple.syslogd.plist']),('launch-jobs',['/bin/launchctl','list'])]:
 try:
  result['diagnostics'][label]=reader.capture(command,user,home).decode('utf8','replace')[-4000:]
 except Exception as error:
  result['diagnostics'][label]=str(error)
try:
 reader.capture(['/usr/bin/logger','-t','aslice-console-probe',{marker!r}],user,home)
 result['write']='completed'
except Exception as error:
 result['write']=str(error)
try:
 reader.capture(['/usr/bin/syslog','-s','-k','Sender','aslice-console-probe','Message',{marker!r}],user,home)
 result['asl_write']='completed'
except Exception as error:
 result['asl_write']=str(error)
result['sources']={{}}
for source in reader.SOURCES:
 response=reader.read(source,user,home)
 result['sources'][source]={{'available':response['available'],'count':len(response['records']),'marker_observed':any({marker!r} in row['message'] for row in response['records']),'note':response['note']}}
print(json.dumps(result))
'''
    session = await request('exec', mode='linux', admin=True,
                            argv=['sudo', '/usr/bin/python3', '-c', code])
    cursor, output = 0, bytearray()
    deadline = time.monotonic() + 65
    try:
        while time.monotonic() < deadline:
            result = await request('session-read', session=session['id'], cursor=cursor)
            output.extend(base64.b64decode(result['data']))
            cursor = result['cursor']
            if len(output) > 65536:
                raise ValueError('Probe output exceeded 64 KiB.')
            if result['exit_code'] is not None:
                if result['exit_code']:
                    raise ValueError('Guest probe failed: ' + output.decode('utf8', 'replace')[-2000:])
                report = json.loads(output)
                after = await request('health')
                remaining = {item['id'] for item in after['sessions'] if item['exit_code'] is None}
                report['previous_active_sessions'] = len(active)
                report['previous_sessions_still_active'] = all(item in remaining for item in active)
                report['agent_restarted'] = False
                return report
            await asyncio.sleep(0.2)
        raise ValueError('Guest log probe exceeded 65 seconds.')
    finally:
        await request('session-close', session=session['id'], disposition='terminate')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--machine-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = asyncio.run(probe(args.machine_dir))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, indent=2))
    return 0 if any(item['marker_observed'] for item in report['sources'].values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
