"""Read-only triage of ignored work; never execute or delete discovered files."""

from collections import Counter
import hashlib
import os
from pathlib import Path

SOURCE_SUFFIXES = {'.py', '.sh', '.ps1', '.bat', '.cmd', '.cpp', '.c', '.m', '.mm', '.h', '.hpp', '.patch', '.diff'}
DEPENDENCIES = {'node_modules', '_deps', 'deps', 'vcpkg', 'windows-deps', 'llvm-resource',
                'llvm-tools', 'llvm-tools-22', 'archive-tools', 'pdf-tools', 'python',
                'CMakeFiles', '__pycache__', '.git', 'site-packages'}


def audit_build(root):
    root = Path(root)
    counts = Counter()
    sizes = Counter()
    candidates = []
    protected = []
    skipped = []
    if not root.is_dir():
        return {'version': 1, 'root': str(root), 'exists': False, 'candidates': [], 'protected': []}
    for directory, directories, filenames in os.walk(root, followlinks=False):
        kept = []
        for name in directories:
            path = Path(directory) / name
            if name in DEPENDENCIES or path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
                skipped.append(path.relative_to(root).as_posix())
            else:
                kept.append(name)
        directories[:] = kept
        for name in sorted(filenames):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                protected.append({'path': relative, 'reason': 'link; not followed'})
                continue
            size = path.stat().st_size
            suffix = path.suffix.lower()
            if suffix in {'.qcow2', '.raw', '.img', '.vmdk', '.vdi', '.iso'} or any(
                    part in {'.controller', 'control', 'machines', 'bases', 'snapshots'} for part in path.parts):
                category = 'persistent-state'
                protected.append({'path': relative, 'bytes': size, 'reason': category})
            elif suffix in SOURCE_SUFFIXES or name.endswith('Dockerfile'):
                category = 'source-candidate'
                record = {'path': relative, 'bytes': size}
                if size <= 4 * 1024 * 1024:
                    record['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
                candidates.append(record)
            elif suffix in {'.json', '.log', '.txt', '.png', '.md', '.zip'}:
                category = 'evidence-or-notes'
            else:
                category = 'generated-or-unclassified'
            counts[category] += 1
            sizes[category] += size
    return {'version': 1, 'root': str(root), 'exists': True, 'counts': dict(counts),
            'bytes': dict(sizes), 'skipped_directories': sorted(skipped),
            'candidates': sorted(candidates, key=lambda item: item['path']),
            'protected': sorted(protected, key=lambda item: item['path']),
            'notice': 'Classification is a review aid, not permission to delete. Credentials and evidence may also occur in unclassified files.'}
