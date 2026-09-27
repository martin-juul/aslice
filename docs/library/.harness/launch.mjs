import { spawn, spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createInterface } from 'node:readline';

const directory = fileURLToPath(new URL('.', import.meta.url));
const args = process.argv.slice(2);
const portIndex = args.indexOf('--port');
const port = Number(
  portIndex < 0 ? process.env.LIBRARY_PORT || 8765 : args[portIndex + 1],
);
const origin = `http://127.0.0.1:${port}`;
let backend;
let viewer;
let creatingViewer;
let stopping = false;

async function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  // A signal can arrive while Vite is initializing its server.
  if (creatingViewer) {
    try {
      viewer = await creatingViewer;
    } catch {
      /* Startup reports the error. */
    }
  }
  if (viewer) {
    if (viewer.close) await viewer.close();
    else await new Promise((resolve) => viewer.httpServer.close(resolve));
  }
  if (backend && backend.exitCode === null) {
    const exited = new Promise((resolve) => backend.once('exit', resolve));
    backend.stdin.end();
    const timer = setTimeout(() => backend.kill(), 5000);
    await exited;
    clearTimeout(timer);
  }
  process.exitCode = code;
}

process.on('SIGINT', () => void stop());
process.on('SIGTERM', () => void stop());

try {
  const [major, minor] = process.versions.node.split('.').map(Number);
  if (!(major >= 26 || (major === 24 && minor >= 15)))
    throw new Error('Node.js 24.15+ (24.x) or 26+ is required.');
  if (!Number.isInteger(port) || port < 1 || port > 65535)
    throw new Error('--port must be between 1 and 65535.');
  const built = args.includes('--built');
  if (built && !existsSync(new URL('./dist/index.html', import.meta.url)))
    throw new Error('Run npm run build before npm run serve.');
  const candidates = process.env.LIBRARY_PYTHON
    ? [[process.env.LIBRARY_PYTHON, []]]
    : [
        ['python3', []],
        ['python', []],
        ['py', ['-3']],
      ];
  const python = candidates.find(
    ([command, prefix]) =>
      spawnSync(
        command,
        [...prefix, '-c', 'import sys; sys.exit(sys.version_info < (3, 10))'],
        { windowsHide: true, timeout: 5000 },
      ).status === 0,
  );
  if (!python)
    throw new Error(
      'Python 3.10 or newer is required. Install Python or set LIBRARY_PYTHON to its executable.',
    );
  backend = spawn(
    python[0],
    [...python[1], '-u', '-m', 'backend.bookshelf', '--viewer-origin', origin],
    { cwd: directory, windowsHide: true, stdio: ['pipe', 'pipe', 'inherit'] },
  );
  backend.once('exit', (code) => {
    if (!stopping) {
      console.error(`Replay backend stopped (${code}).`);
      void stop(1);
    }
  });
  const ready = await new Promise((resolve, reject) => {
    const lines = createInterface({ input: backend.stdout });
    const timer = setTimeout(
      () =>
        reject(
          new Error('Replay backend did not become ready within 60 seconds.'),
        ),
      60000,
    );
    backend.once('error', reject);
    backend.once('exit', () => {
      clearTimeout(timer);
      reject(new Error('Replay backend failed during startup.'));
    });
    lines.once('line', (line) => {
      clearTimeout(timer);
      try {
        resolve(JSON.parse(line));
      } catch {
        reject(new Error('Invalid replay backend readiness response.'));
      }
    });
  });
  if (stopping) throw new Error('Startup interrupted.');
  process.env.LIBRARY_BACKEND = `http://127.0.0.1:${ready.port}`;
  const { createServer, preview } = await import('vite');
  if (stopping) throw new Error('Startup interrupted.');
  const config = {
    configFile: fileURLToPath(new URL('./vite.config.ts', import.meta.url)),
    server: { port },
    preview: { port },
  };
  creatingViewer = built ? preview(config) : createServer(config);
  viewer = await creatingViewer;
  if (stopping) throw new Error('Startup interrupted.');
  if (!built) await viewer.listen();
  if (stopping) throw new Error('Startup interrupted.');
  const response = await fetch(`${origin}/api/catalog`);
  if (!response.ok)
    throw new Error('The library catalog failed its readiness check.');
  console.log(`Documentation Library: ${origin}`);
  if (!args.includes('--no-open')) {
    const command =
      process.platform === 'win32'
        ? ['rundll32', ['url.dll,FileProtocolHandler', origin]]
        : process.platform === 'darwin'
          ? ['open', [origin]]
          : ['xdg-open', [origin]];
    const browser = spawn(command[0], command[1], {
      windowsHide: true,
      stdio: 'ignore',
    });
    browser.on('error', () => console.error(`Open ${origin} in your browser.`));
    browser.unref();
  }
} catch (error) {
  console.error(`Library startup failed: ${error.message}`);
  await stop(1);
}
