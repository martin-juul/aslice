import { afterEach, expect, it, vi } from 'vitest';
import { OutputStream } from './output-stream';
import type { SessionOutput } from './model';
import { sourceMapCommand } from './model';

const output: SessionOutput = {
  id: 'session',
  pid: 1,
  mode: 'darwin',
  kind: 'shell',
  exit_code: null,
  cursor: 12,
  data: '',
  truncated: false,
};

afterEach(() => vi.useRealTimers());

it('ignores a late response from the previous machine and stops polling on disposal', async () => {
  vi.useFakeTimers();
  const pending = Promise.withResolvers<SessionOutput>();
  const receive = vi.fn();
  const failed = vi.fn();
  const read = vi
    .fn()
    .mockReturnValueOnce(pending.promise)
    .mockResolvedValue(output);
  const stream = new OutputStream({ read }, receive, failed);
  stream.follow('first', 'old');
  stream.follow('second', 'new');
  await Promise.resolve();
  pending.resolve({ ...output, id: 'old' });
  await Promise.resolve();
  expect(receive).toHaveBeenCalledExactlyOnceWith(output);
  expect(read.mock.calls[0]?.[3].aborted).toBe(true);
  stream.stop();
  await vi.advanceTimersByTimeAsync(1000);
  expect(read).toHaveBeenCalledTimes(2);
  expect(failed).not.toHaveBeenCalled();
});

it('does not overlap reads and stops after process exit', async () => {
  vi.useFakeTimers();
  const pending = Promise.withResolvers<SessionOutput>();
  const read = vi.fn().mockReturnValue(pending.promise);
  const stream = new OutputStream({ read }, vi.fn(), vi.fn());
  stream.follow('machine', 'session');
  await vi.advanceTimersByTimeAsync(1000);
  expect(read).toHaveBeenCalledTimes(1);
  pending.resolve({ ...output, exit_code: 0 });
  await vi.advanceTimersByTimeAsync(1000);
  expect(read).toHaveBeenCalledTimes(1);
  stream.stop();
});

it('quotes source paths and rejects ambiguous mappings', () => {
  expect(sourceMapCommand('/build/a b → /guest/a b')).toBe(
    'settings set target.source-map "/build/a b" "/guest/a b"\n',
  );
  expect(() => sourceMapCommand('a → b → c')).toThrow();
});

it('reconnects the same session from the last received cursor without replaying output', async () => {
  vi.useFakeTimers();
  const error = new Error('connection lost');
  const read = vi
    .fn()
    .mockResolvedValueOnce(output)
    .mockRejectedValueOnce(error)
    .mockResolvedValueOnce({ ...output, cursor: 24, exit_code: 0 });
  const receive = vi.fn();
  const failed = vi.fn();
  const stream = new OutputStream({ read }, receive, failed);
  stream.follow('machine', 'session');
  await vi.advanceTimersByTimeAsync(300);
  expect(failed).toHaveBeenCalledWith(error);
  expect(read.mock.calls[1]?.slice(0, 3)).toEqual(['machine', 'session', 12]);
  stream.reconnect();
  await Promise.resolve();
  expect(read.mock.calls[2]?.slice(0, 3)).toEqual(['machine', 'session', 12]);
  expect(receive).toHaveBeenCalledTimes(2);
  stream.stop();
  expect(() => stream.reconnect()).toThrow('Choose a session');
});
