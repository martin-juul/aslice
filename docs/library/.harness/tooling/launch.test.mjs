import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { createServer } from 'node:net';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import test from 'node:test';

const launcher = fileURLToPath(new URL('../launch.mjs', import.meta.url));

function launch(args = [], env = {}) {
  const child = spawn(process.execPath, [launcher, '--no-open', ...args], {
    env: { ...process.env, ...env },
    windowsHide: true,
  });
  let output = '';
  child.stdout.on('data', (chunk) => {
    output += chunk;
  });
  child.stderr.on('data', (chunk) => {
    output += chunk;
  });
  return { child, output: () => output };
}

test('reports missing Python and invalid ports', async () => {
  for (const [args, env, expected] of [
    [[], { LIBRARY_PYTHON: 'aslice-python-does-not-exist' }, /Python 3.10/],
    [['--port', 'bad'], {}, /--port must/],
  ]) {
    const run = launch(args, env);
    const [code] = await once(run.child, 'exit');
    assert.equal(code, 1);
    assert.match(run.output(), expected);
  }
});

test(
  'reports port conflicts without selecting another port',
  { timeout: 90000 },
  async () => {
    const occupied = createServer();
    occupied.listen(0, '127.0.0.1');
    await once(occupied, 'listening');
    try {
      const run = launch(['--port', String(occupied.address().port)]);
      const [code] = await once(run.child, 'exit');
      assert.equal(code, 1);
      assert.match(run.output(), /already in use|EADDRINUSE/);
      assert.doesNotMatch(run.output(), /Documentation Library:/);
    } finally {
      occupied.close();
    }
  },
);

test(
  'parent termination closes the backend and all replay origins',
  { timeout: 90000 },
  async () => {
    const available = createServer();
    available.listen(0, '127.0.0.1');
    await once(available, 'listening');
    const port = available.address().port;
    await new Promise((resolve) => available.close(resolve));
    const run = launch(['--port', String(port)]);
    try {
      await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error(run.output())), 60000);
        run.child.stdout.on('data', () => {
          if (run.output().includes('Documentation Library:')) {
            clearTimeout(timer);
            resolve();
          }
        });
        run.child.once('exit', () => {
          clearTimeout(timer);
          reject(new Error(run.output()));
        });
      });
      const books = await (
        await fetch(`http://127.0.0.1:${port}/api/catalog`)
      ).json();
      assert.ok(books.some((book) => book.origin));
      const exited = once(run.child, 'exit');
      run.child.kill('SIGTERM');
      await exited;
      // On Windows termination is abrupt; the backend observes stdin EOF.
      for (const book of books.filter((book) => book.origin)) {
        let closed = false;
        for (let attempt = 0; attempt < 30; attempt++) {
          try {
            await fetch(book.entry, { signal: AbortSignal.timeout(500) });
          } catch {
            closed = true;
            break;
          }
          await new Promise((resolve) => setTimeout(resolve, 100));
        }
        assert.ok(closed, `${book.origin} survived parent termination`);
      }
    } finally {
      if (run.child.exitCode === null) run.child.kill();
    }
  },
);
