import { describe, expect, it, vi } from 'vitest';
import { Gateway } from '../../shared/protocol';
import type { Command, Transport } from '../../shared/protocol';
import { DemoTransport } from '../../development/demo-transport';
import { FileTransfers } from './service';
import { CHUNK_SIZE, transferPath } from './model';
import { encode, sha256 } from '../../shared/bytes';

function transport(send: Transport['send']): Transport {
  return { kind: 'demo', authenticate: async () => {}, send };
}

describe('bounded file transfers', () => {
  it('round trips multiple chunks and empty files through the protocol', async () => {
    const service = new FileTransfers(new Gateway(new DemoTransport('normal')));
    for (const bytes of [
      new Uint8Array(),
      new Uint8Array(CHUNK_SIZE + 9).fill(42),
    ]) {
      await service.import('sample-mac', 'nested/file', bytes, false);
      expect(await service.export('sample-mac', 'nested/file')).toEqual(bytes);
    }
  });

  it('aborts failed imports using the original machine and a fresh request', async () => {
    const calls: Command[] = [];
    const controller = new AbortController();
    const send = vi.fn<Transport['send']>(async (command, signal) => {
      calls.push(command);
      if (command.action === 'import-begin') {
        return { transfer: 'transfer-1' };
      }
      if (command.action === 'import-chunk') {
        controller.abort();
        throw new Error('connection lost');
      }
      expect(signal).toBeUndefined();
      return {};
    });
    const service = new FileTransfers(new Gateway(transport(send)));
    await expect(
      service.import(
        'original',
        'file',
        new Uint8Array([1]),
        false,
        controller.signal,
      ),
    ).rejects.toThrow('connection lost');
    expect(calls.map((call) => call.action)).toEqual([
      'import-begin',
      'import-chunk',
      'import-abort',
    ]);
    expect(calls.every((call) => call.name === 'original')).toBe(true);
  });

  it('rejects corrupted export contents', async () => {
    const digest = await sha256(new Uint8Array([1]));
    const service = new FileTransfers(
      new Gateway(
        transport(async () => ({
          size: 1,
          offset: 0,
          sha256: digest,
          data: encode(new Uint8Array([2])),
        })),
      ),
    );
    await expect(service.export('machine', 'file')).rejects.toThrow(
      'hash mismatch',
    );
  });

  it('rejects an export that makes no progress', async () => {
    const service = new FileTransfers(
      new Gateway(
        transport(async () => ({
          size: 1,
          offset: 0,
          sha256: '0'.repeat(64),
          data: '',
        })),
      ),
    );
    await expect(service.export('machine', 'file')).rejects.toThrow(
      'Incomplete',
    );
  });

  it.each(['../secret', '/absolute', 'a//b', 'a/./b', 'a\\b', ''])(
    'rejects unsafe path %s',
    (path) => {
      expect(() => transferPath(path)).toThrow();
    },
  );
});
