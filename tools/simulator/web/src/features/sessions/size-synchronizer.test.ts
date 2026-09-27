import { expect, it, vi } from 'vitest';
import { SizeSynchronizer } from './size-synchronizer';
import type { TerminalSize } from './model';

it('sends only the latest size after an in-flight resize completes', async () => {
  const pending = Promise.withResolvers<void>();
  const send = vi
    .fn<(size: TerminalSize) => Promise<void>>()
    .mockReturnValueOnce(pending.promise)
    .mockResolvedValue(undefined);
  const sizing = new SizeSynchronizer(send, vi.fn());
  sizing.update({ cols: 80, rows: 20 });
  sizing.update({ cols: 90, rows: 21 });
  sizing.update({ cols: 100, rows: 22 });
  expect(send).toHaveBeenCalledTimes(1);
  pending.resolve();
  await vi.waitFor(() => expect(send).toHaveBeenCalledTimes(2));
  expect(send.mock.calls[1]?.[0]).toEqual({ cols: 100, rows: 22 });
  sizing.update({ cols: 100, rows: 22 });
  await Promise.resolve();
  expect(send).toHaveBeenCalledTimes(2);
});

it('drops pending sizes and ignores old request errors after disposal', async () => {
  const pending = Promise.withResolvers<void>();
  const send = vi.fn().mockReturnValue(pending.promise);
  const failed = vi.fn();
  const sizing = new SizeSynchronizer(send, failed);
  sizing.update({ cols: 80, rows: 20 });
  sizing.update({ cols: 100, rows: 20 });
  sizing.dispose();
  pending.reject(new Error('old machine disconnected'));
  await Promise.resolve();
  sizing.update({ cols: 120, rows: 20 });
  expect(send).toHaveBeenCalledTimes(1);
  expect(failed).not.toHaveBeenCalled();
});

it('reports a resize failure without reporting the size as acknowledged', async () => {
  const error = new Error('disconnected');
  const send = vi
    .fn()
    .mockRejectedValueOnce(error)
    .mockResolvedValue(undefined);
  const failed = vi.fn();
  const sizing = new SizeSynchronizer(send, failed);
  sizing.update({ cols: 80, rows: 20 });
  await vi.waitFor(() => expect(failed).toHaveBeenCalledWith(error));
  sizing.update({ cols: 80, rows: 20 });
  await vi.waitFor(() => expect(send).toHaveBeenCalledTimes(2));
});
