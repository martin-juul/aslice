"""One public development command; recipes delegate to existing authorities."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

from .audit import audit_build
from .process import ROOT, Runner, executable, state_root


def quality_tool(name, runner):
    override = os.environ.get('ASLICE_' + name.upper().replace('-', '_'))
    for candidate in (override, shutil.which(name + '-22'), shutil.which(name)):
        if candidate and Path(candidate).is_file():
            return str(candidate)
    # Transitional support for tools already installed by this checkout's bootstrap.
    patterns = {'clang-format': 'llvm-tools/clang_format/data/bin/clang-format.exe',
                'clang-tidy': 'llvm-tools-22/clang_tidy/data/bin/clang-tidy.exe'}
    candidate = runner.root / 'build' / patterns[name]
    if candidate.is_file():
        return str(candidate)
    if runner.dry_run:
        return name + '-22'
    raise ValueError(f'Install LLVM 22 {name} or set ASLICE_{name.upper().replace("-", "_")}.')


def configure(runner, build):
    command = [runner.tool('cmake')]
    if os.name == 'nt':
        command += ['--preset', 'windows-clion', '-B', build]
    else:
        command += ['-S', runner.root, '-B', build, '-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Debug']
    runner.run(command)


def build_native(runner, build):
    if runner.dry_run or not (build / 'CMakeCache.txt').is_file():
        configure(runner, build)
    runner.run([runner.tool('cmake'), '--build', build, '--parallel', '4'])


def quality(runner, build, mode):
    command = [sys.executable, runner.root / 'tools/quality.py', mode, '--build', build]
    name = 'clang-tidy' if mode == 'tidy' else 'clang-format'
    command += ['--tidy-tool' if mode == 'tidy' else '--format-tool', quality_tool(name, runner)]
    runner.run(command)


def web(runner, project, action):
    directory = runner.root / ('tools/simulator/web' if project == 'simulator' else 'docs/library')
    npm = runner.tool('npm')
    if action == 'setup':
        runner.run([npm, 'ci'], cwd=directory)
        return
    if not runner.dry_run and not (directory / 'node_modules').is_dir():
        raise ValueError(f'Run python dev.py web {project} setup first.')
    if action == 'build' and project == 'simulator':
        for script in ('build', 'build:demo', 'check:browser'):
            runner.run([npm, 'run', script], cwd=directory)
    else:
        runner.run([npm, 'run', action], cwd=directory)


def tests(runner, build, suite):
    if suite == 'developer':
        runner.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests/dev'])
    elif suite == 'browser':
        console_assets(runner, True)
        runner.run([sys.executable, runner.root / 'tests/simulator/check_console_browser.py'])
    elif suite in ('web', 'library'):
        web(runner, 'simulator' if suite == 'web' else 'library', 'check')
    else:
        if not runner.dry_run and not (build / 'CTestTestfile.cmake').is_file():
            raise ValueError('Configure and build first: python dev.py build')
        command = [runner.tool('ctest'), '--test-dir', build, '--output-on-failure', '--no-tests=error', '-j', '2']
        if suite != 'all':
            command += ['-L', suite]
        runner.run(command)


def docker_check(runner, args):
    if args.docker_action == 'application':
        if args.sanitizers or args.reuse_image:
            raise ValueError('application checks use a Python image; sanitizer/reuse flags apply to check.')
        console_assets(runner, False)
        runner.run([runner.tool('docker'), 'run', '--rm', '--mount',
                    f'type=bind,source={runner.root.as_posix()},target=/src,readonly',
                    '--workdir', '/src', '--entrypoint', 'python3', args.image or 'python:3.14-slim',
                    '/src/tools/dev/docker-application-check.py'])
        return
    image = args.image or ('aslice-dev-sanitized' if args.sanitizers else 'aslice-dev-check')
    mode = 'ON' if args.sanitizers else 'OFF'
    docker = runner.tool('docker')
    if args.reuse_image:
        runner.run([docker, 'run', '--rm', '--network', 'none', '--mount',
                    f'type=bind,source={runner.root.as_posix()},target=/src,readonly',
                    '--entrypoint', 'sh', image, '/src/tools/dev/docker-check.sh', mode])
    else:
        runner.run([docker, 'build', '--build-arg', f'ASLICE_SANITIZERS={mode}',
                    '-t', image, '-f', runner.root / 'Dockerfile', runner.root])


def console_assets(runner, demo, rebuild=False):
    output = runner.root / ('build/simulator-web-demo' if demo else 'build/simulator-web')
    if rebuild or not all((output / name).is_file() for name in ('index.html', 'app.js', 'app.css')):
        source = runner.root / 'tools/simulator/web'
        if not (source / 'node_modules').is_dir():
            web(runner, 'simulator', 'setup')
        web(runner, 'simulator', 'build')
    return output


def simulator(runner, build, args):
    action = args.simulator_action
    if action == 'logs-probe':
        runner.run([sys.executable, '-m', 'tools.dev.guest_log_probe',
                    '--machine-dir', args.machine_dir, '--output', args.output])
    elif action == 'setup':
        runner.run([sys.executable, '-m', 'pip', 'install', '-r', 'tools/simulator/runtime-requirements.txt'])
        web(runner, 'simulator', 'setup')
        web(runner, 'simulator', 'build')
    elif action == 'open':
        if not runner.dry_run and importlib.util.find_spec('aiohttp') is None:
            raise ValueError('The controller needs aiohttp. Run python dev.py simulator setup.')
        console_assets(runner, False, args.rebuild)
        command = [sys.executable, '-m', 'tools.simulator.application', 'open', '--root', args.root]
        if args.no_browser:
            command.append('--no-browser')
        # The console prints a one-time authentication URL. Never retain it in logs.
        runner.run(command, retain=False)
    elif action == 'package':
        console_assets(runner, False, args.rebuild)
        if runner.dry_run:
            print(f'Would package the application to {args.output}')
        else:
            from .package import package
            print(package(runner.root, args.output))
    elif action == 'shutdown':
        command = [sys.executable, '-m', 'tools.simulator.application', 'shutdown', '--root', args.root]
        if args.stop_machines:
            command.append('--stop-machines')
        runner.run(command, retain=False)
    elif action == 'demo':
        output = console_assets(runner, True, args.rebuild)
        if runner.dry_run:
            print(f'Would serve sample console from {output} on 127.0.0.1:{args.port}')
        else:
            from .preview import preview
            preview(output, args.port, not args.no_browser)
    elif action == 'model':
        suffix = '.exe' if os.name == 'nt' else ''
        binary = build / ('aslice-simulator' + suffix)
        if not runner.dry_run and not binary.is_file():
            raise ValueError('Build the modeled executable first: python dev.py build')
        workspace = args.workspace or runner.root / 'build/runs/modeled' / uuid.uuid4().hex
        command = [sys.executable, '-m', 'tools.simulator', 'run', '--suite', args.suite,
                   '--workspace', workspace, '--seed', str(args.seed), '--aslice', binary]
        if args.suite in ('helper', 'full'):
            command += ['--helper-driver', build / ('simulator_helper_driver' + suffix)]
        runner.run(command)
    else:
        command = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
        if not command:
            command = ['status']
        runner.run([sys.executable, '-m', 'tools.simulator', 'machine', '--root', args.root, *command], retain=False)


def compare_coverage(runner, image):
    command = [runner.tool('docker'), 'run', '--rm', '--network', 'none', '--mount',
               f'type=bind,source={runner.root.as_posix()},target=/src,readonly',
               '--entrypoint', 'python3', image, '-m', 'tools.simulator', 'coverage', '--gate', 'development']
    if runner.dry_run:
        runner.run(command)
        return
    from tools.simulator.requirements import evaluate
    local = evaluate(runner.root)
    result = subprocess.run(command, cwd=runner.root, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise ValueError('Container coverage failed: ' + result.stderr[-2000:])
    remote = json.loads(result.stdout)
    matched = local == remote
    runner.report.mkdir(parents=True, exist_ok=True)
    output = runner.report / 'coverage-comparison.json'
    output.write_text(json.dumps({'matched': matched, 'registry_sha256': local['registry_sha256'],
                                 'comparison': 'Complete decoded reports; no fields omitted.'}, indent=2) + '\n')
    print(output)
    if not matched:
        raise ValueError('Native and container requirement reports differ.')


def parser():
    result = argparse.ArgumentParser(description='Build, check, and launch aslice development tools.')
    result.add_argument('--dry-run', action='store_true', help='print recipes without executing or creating files')
    result.add_argument('--build-dir', type=Path, help='CMake build directory; default build/windows-clion on Windows, build/native elsewhere')
    commands = result.add_subparsers(dest='action', required=True)
    for name in ('doctor', 'configure', 'build', 'format', 'format-check', 'tidy'):
        commands.add_parser(name)
    check = commands.add_parser('check', help='build, formatting check, analysis, CTest, and developer harness tests')
    check.add_argument('--with-web', action='store_true', help='also check simulator and library web projects')
    test = commands.add_parser('test')
    test.add_argument('suite', nargs='?', default='all', choices=('all', 'core', 'modeled', 'runtime', 'requirements', 'developer', 'web', 'library', 'browser'))
    container = commands.add_parser('docker', help='Linux quality and test matrix')
    container.add_argument('docker_action', choices=('check', 'application'))
    container.add_argument('--sanitizers', action='store_true')
    container.add_argument('--image')
    container.add_argument('--reuse-image', action='store_true', help='offline check in an existing provisioned image, with current source mounted read-only')
    frontend = commands.add_parser('web')
    frontend.add_argument('project', choices=('simulator', 'library'))
    frontend.add_argument('web_action', choices=('setup', 'check', 'build', 'serve'))
    audit = commands.add_parser('audit-build', help='inventory source candidates and protected state; never delete')
    audit.add_argument('--output', type=Path)
    comparison = commands.add_parser('compare-coverage', help='compare complete native and container requirement reports')
    comparison.add_argument('--image', default='aslice-dev-check')
    sim = commands.add_parser('simulator', help='console, sample demo, modeled tests, and persistent machines')
    actions = sim.add_subparsers(dest='simulator_action', required=True)
    actions.add_parser('setup', help='install controller dependencies and build console assets')
    probe = actions.add_parser('logs-probe', help='verify guest logging with a tagged message without restarting the agent')
    probe.add_argument('--machine-dir', type=Path, required=True)
    probe.add_argument('--output', type=Path, required=True)
    bundle = actions.add_parser('package', help='package the Windows/Linux application with compiled console assets')
    bundle.add_argument('--output', type=Path, default=ROOT / 'build/packages/aslice-simulator.zip')
    bundle.add_argument('--rebuild', action='store_true')
    shutdown = actions.add_parser('shutdown', help='stop the controller, preserving machines unless explicitly requested')
    shutdown.add_argument('--root', type=Path, default=state_root())
    shutdown.add_argument('--stop-machines', action='store_true')
    for name in ('open', 'demo'):
        launch = actions.add_parser(name)
        launch.add_argument('--no-browser', action='store_true')
        launch.add_argument('--rebuild', action='store_true')
        if name == 'open':
            launch.add_argument('--root', type=Path, default=state_root())
        else:
            launch.add_argument('--port', type=int, default=8766)
    model = actions.add_parser('model')
    model.add_argument('--suite', choices=('foundation', 'fixture', 'helper', 'full'), default='fixture')
    model.add_argument('--workspace', type=Path)
    model.add_argument('--seed', type=int, default=17)
    machine = actions.add_parser('machine', help='forward existing machine CLI commands, using the persistent state directory')
    machine.add_argument('--root', type=Path, default=state_root())
    machine.add_argument('arguments', nargs=argparse.REMAINDER)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    runner = Runner(args.dry_run)
    build = (args.build_dir or ROOT / ('build/windows-clion' if os.name == 'nt' else 'build/native')).absolute()
    try:
        if args.action == 'doctor':
            tools = {}
            for name in ('cmake', 'ctest', 'docker', 'npm', 'node', 'qemu-system-x86_64', 'qemu-img', 'ssh'):
                try:
                    tools[name] = executable(name)
                except ValueError:
                    tools[name] = None
            print(json.dumps({'python': sys.version.split()[0], 'tools': tools,
                              'build': str(build), 'simulator_state': str(state_root()),
                              'note': 'Executable discovery only; VM boot and target qualification are separate.'}, indent=2))
        elif args.action == 'configure':
            configure(runner, build)
        elif args.action == 'build':
            build_native(runner, build)
        elif args.action in ('format', 'format-check', 'tidy'):
            quality(runner, build, args.action)
        elif args.action == 'test':
            tests(runner, build, args.suite)
        elif args.action == 'check':
            configure(runner, build)
            build_native(runner, build)
            quality(runner, build, 'format-check')
            quality(runner, build, 'tidy')
            tests(runner, build, 'all')
            if args.with_web:
                tests(runner, build, 'web')
                tests(runner, build, 'library')
        elif args.action == 'docker':
            docker_check(runner, args)
        elif args.action == 'web':
            web(runner, args.project, args.web_action)
        elif args.action == 'simulator':
            simulator(runner, build, args)
        elif args.action == 'compare-coverage':
            compare_coverage(runner, args.image)
        elif args.action == 'audit-build':
            if args.dry_run:
                print('Would inventory build/ without changing its contents.')
            else:
                report = audit_build(ROOT / 'build')
                output = args.output or runner.report / 'build-inventory.json'
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
                print(json.dumps({'report': str(output), 'counts': report.get('counts', {}),
                                  'notice': report.get('notice')}, indent=2))
        return 0
    except KeyboardInterrupt:
        print('Interrupted.', file=sys.stderr)
        return 130
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'dev: {error}', file=sys.stderr)
        return error.returncode if isinstance(error, subprocess.CalledProcessError) else 2
