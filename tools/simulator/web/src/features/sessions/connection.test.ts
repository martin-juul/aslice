import { expect, it, vi } from 'vitest';
import { Gateway } from '../../shared/protocol';
import type { Transport } from '../../shared/protocol';
import { SessionConnection } from './connection';
import type { Session } from './model';
import { InputQueue } from './input-queue';

const session: Session = {
  id: 'session',
  pid: 42,
  kind: 'terminal',
  mode: 'darwin',
  exit_code: null,
};

function setup(kind = 'terminal') {
  const send = vi.fn<Transport['send']>().mockResolvedValue({});
  const gateway = new Gateway({
    kind: 'live',
    authenticate: async () => {},
    send,
  });
  const connection = new SessionConnection(
    'original-machine',
    { ...session, kind },
    gateway,
    new AbortController().signal,
  );
  return { connection, send };
}

it('refuses debugger commands and debugger termination on an ordinary shell', async () => {
  const { connection, send } = setup();
  await expect(connection.send('run\n', true)).rejects.toThrow(
    'Select a debugger',
  );
  await expect(connection.closeDebugger('terminate')).rejects.toThrow(
    'Select a debugger',
  );
  expect(send).not.toHaveBeenCalled();
});

it('orders input and debugger closure, preserving the captured target', async () => {
  const { connection, send } = setup('debug');
  const pending = Promise.withResolvers<unknown>();
  send.mockReturnValueOnce(pending.promise);
  const first = connection.send('thread list\n', true);
  const second = connection.send('frame variable\n', true);
  const close = connection.closeDebugger('detach');
  await Promise.resolve();
  expect(send).toHaveBeenCalledTimes(1);
  await expect(connection.send('continue\n', true)).rejects.toThrow('closing');
  pending.resolve({});
  await Promise.all([first, second, close]);
  expect(send.mock.calls.map(([command]) => command.action)).toEqual([
    'session-write',
    'session-write',
    'session-close',
  ]);
  expect(
    send.mock.calls.every(([command]) => command.name === 'original-machine'),
  ).toBe(true);
  expect(send.mock.calls[2]?.[0]).toEqual({
    action: 'session-close',
    name: 'original-machine',
    session: 'session',
    disposition: 'detach',
  });
});

it('does not replay uncertain input or send later queued input after failure', async () => {
  const { connection, send } = setup();
  send.mockRejectedValueOnce(new Error('connection lost'));
  const results = await Promise.allSettled([
    connection.send('first'),
    connection.send('second'),
  ]);
  expect(results.every((result) => result.status === 'rejected')).toBe(true);
  expect(send).toHaveBeenCalledTimes(1);
  await expect(connection.send('third')).rejects.toThrow('uncertain');
  expect(send).toHaveBeenCalledTimes(1);
});

it('rejects large pastes by encoded byte size before sending anything', async () => {
  const { connection, send } = setup();
  await expect(connection.send('€'.repeat(22000))).rejects.toThrow('64 KiB');
  expect(send).not.toHaveBeenCalled();
});

it('does not let a stale health response resurrect an exited session', async () => {
  const { connection, send } = setup();
  connection.update({ ...session, exit_code: 0 });
  connection.update(session);
  await expect(connection.send('command')).rejects.toThrow('exited');
  expect(send).not.toHaveBeenCalled();
});

it('discards unsent old input and waits for the in-flight write before sending to a new selection', async () => {
  const oldQueue = new InputQueue();
  const pending = Promise.withResolvers<void>();
  const sent: string[] = [];
  const first = oldQueue.enqueue(async () => {
    sent.push('old first');
    await pending.promise;
  });
  const discarded = oldQueue.enqueue(async () => {
    sent.push('old unsent');
  });
  const rejected = expect(discarded).rejects.toThrow('selection changed');
  await Promise.resolve();
  const newQueue = oldQueue.successor();
  const next = newQueue.enqueue(async () => {
    sent.push('new');
  });
  await Promise.resolve();
  expect(sent).toEqual(['old first']);
  pending.resolve();
  await Promise.all([first, rejected, next]);
  expect(sent).toEqual(['old first', 'new']);
});

it('bounds queued input while a write is pending', async () => {
  const queue = new InputQueue();
  const pending = Promise.withResolvers<void>();
  const first = queue.enqueue(() => pending.promise, 1024 * 1024);
  await expect(queue.enqueue(async () => {}, 1)).rejects.toThrow(
    'queue is full',
  );
  pending.resolve();
  await first;
  await expect(queue.enqueue(async () => {}, 1)).resolves.toBeUndefined();
});

it('sends bounded terminal dimensions to the captured session', async () => {
  const { connection, send } = setup();
  await connection.resize({ cols: 91, rows: 23 });
  expect(send.mock.calls[0]?.[0]).toEqual({
    action: 'session-resize',
    name: 'original-machine',
    session: 'session',
    cols: 91,
    rows: 23,
  });
  await expect(connection.resize({ cols: 1001, rows: 23 })).rejects.toThrow(
    'dimensions',
  );
  connection.dispose();
  await connection.resize({ cols: 92, rows: 24 });
  expect(send).toHaveBeenCalledTimes(1);
});
