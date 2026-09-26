"""Run quality tools on owned C++ only. Checks never modify source files."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('mode', choices=('format', 'format-check', 'tidy'))
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--format-tool', default='clang-format-20')
    parser.add_argument('--tidy-tool', default='clang-tidy-20')
    parser.add_argument('--resource-dir', default=os.environ.get('ASLICE_CLANG_RESOURCE_DIR'))
    args = parser.parse_args()
    sources = sorted([*ROOT.joinpath('src').rglob('*.cpp'),
                      *ROOT.joinpath('src').rglob('*.hpp'),
                      *ROOT.joinpath('tests').glob('*.cpp')])
    if args.mode != 'tidy':
        flags = ['-i'] if args.mode == 'format' else ['--dry-run', '--Werror']
        return subprocess.call([args.format_tool, *flags, *map(str, sources)])
    subprocess.run([args.tidy_tool, '--verify-config'], cwd=ROOT, check=True)
    database = json.loads((args.build / 'compile_commands.json').read_text())
    extra = []
    if args.resource_dir:
        extra.append('--extra-arg=-resource-dir=' + args.resource_dir)
    if os.name == 'nt':
        compiler = shlex.split(database[0]['command'], posix=False)[0].strip('"')
        if Path(compiler).name in ('g++.exe', 'gcc.exe'):
            # Ask the actual compilation-database compiler for its target and system
            # headers. CLion clang-tidy does not discover bundled MinGW by itself.
            probe = subprocess.run([compiler, '-E', '-x', 'c++', '-', '-v'], input='',
                                   capture_output=True, text=True, check=True)
            includes = re.search(r'#include <\.\.\.> search starts here:\n(.*?)End of search list',
                                 probe.stderr, re.S)
            if includes is None:
                raise RuntimeError('Cannot discover MinGW include directories')
            target = subprocess.check_output([compiler, '-dumpmachine'], text=True).strip()
            extra.append('--extra-arg=--target=' + target)
            # GCC intrinsic headers implement GCC-only builtins. Clang must use
            # its own resource headers, while retaining MinGW's C++ and CRT headers.
            extra.extend('--extra-arg=-isystem' + line.strip()
                         for line in includes[1].splitlines()
                         if line.strip() and not re.search(r'/lib/gcc/[^/]+/[^/]+/include(?:-fixed)?$',
                                                           line.strip().replace('\\', '/')))
    owned = set(sources)
    files = sorted({Path(entry['file']).resolve() for entry in database
                    if Path(entry['file']).resolve() in owned})
    if not files:
        raise RuntimeError('Compilation database contains no owned C++ files')
    def analyze(path):
        result = subprocess.run([args.tidy_tool, '-p', str(args.build), *extra, str(path)],
                                cwd=ROOT, capture_output=True, text=True)
        return path, result
    failed = False
    with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as pool:
        for path, result in pool.map(analyze, files):
            print(path.relative_to(ROOT))
            if result.stdout:
                print(result.stdout)
            if result.returncode:
                print(result.stderr, file=sys.stderr)
                failed = True
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
