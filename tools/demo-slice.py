"""Pack and inspect a real unsigned slice using a disposable payload directory."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile

binary = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='aslice-slice-demo-') as directory:
    root = Path(directory)
    payload = root / 'payload'
    (payload / 'bin').mkdir(parents=True)
    content = b'#!/bin/sh\nprintf "hello from a slice\\n"\n'
    program = payload / 'bin/hello'
    program.write_bytes(content)
    program.chmod(0o755)
    manifest = dict(manifest_version=1, repository='local', name='hello', version='1.0.0',
                    epoch=0, revision=0, build_id=hashlib.sha256(b'local demo build').hexdigest(),
                    recipe_digest='sha256:' + hashlib.sha256(b'local demo recipe').hexdigest(),
                    user_flags={}, cpu_features=['sse2'], requires_i386=False, min_os='10.11',
                    files=[dict(path='bin/hello', kind='file', mode='0755', size=len(content),
                                sha256=hashlib.sha256(content).hexdigest())],
                    dependencies=[], relocations=[], abi=dict(provides=[], requires=[]))
    source = root / 'manifest.json'
    source.write_text(json.dumps(manifest), encoding='utf-8')
    archive = root / 'hello.slice'
    def run(*args):
        return json.loads(subprocess.check_output([str(binary), *map(str, args)], encoding='utf-8'))
    packed = run('slice', 'pack', source, payload, archive)
    checked = run('slice', 'inspect', archive)
    assert checked['artifact_id'] == packed['artifact_id']
    print(json.dumps({key: checked[key] for key in ('artifact_id', 'blob_digest', 'blob_size',
                                                   'container_verified', 'authenticated')}, indent=2))
