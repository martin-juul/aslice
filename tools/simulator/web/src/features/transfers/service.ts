import type { Gateway } from '../../shared/protocol';
import { decode, encode, sha256 } from '../../shared/bytes';
import { CHUNK_SIZE, TRANSFER_LIMIT, transferPath } from './model';

/** A transfer captures its machine once, even if the user changes selection. */
export class FileTransfers {
  constructor(private readonly gateway: Gateway) {}

  async import(
    name: string,
    path: string,
    bytes: Uint8Array<ArrayBuffer>,
    executable: boolean,
    signal?: AbortSignal,
  ): Promise<void> {
    transferPath(path);
    if (bytes.length > TRANSFER_LIMIT) {
      throw new Error('Select one file, at most 64 MiB.');
    }
    const digest = await sha256(bytes);
    const { transfer } = await this.gateway.execute(
      'import-begin',
      { name, path, size: bytes.length, sha256: digest, executable },
      signal,
    );
    try {
      for (let offset = 0; offset < bytes.length; offset += CHUNK_SIZE) {
        await this.gateway.execute(
          'import-chunk',
          {
            name,
            transfer,
            offset,
            data: encode(bytes.subarray(offset, offset + CHUNK_SIZE)),
          },
          signal,
        );
      }
      await this.gateway.execute('import-commit', { name, transfer }, signal);
    } catch (error) {
      try {
        // Cleanup gets its own request even when the original signal was aborted.
        await this.gateway.execute('import-abort', { name, transfer });
      } catch (cleanupError) {
        throw new AggregateError(
          [error, cleanupError],
          'Import failed and cleanup could not be confirmed. Inspect the transfer record.',
        );
      }
      throw error;
    }
  }

  async export(
    name: string,
    path: string,
    signal?: AbortSignal,
  ): Promise<Uint8Array<ArrayBuffer>> {
    transferPath(path);
    let offset = 0;
    let expected: { size: number; sha256: string } | undefined;
    const blocks: Uint8Array<ArrayBuffer>[] = [];
    for (;;) {
      const result = await this.gateway.execute(
        'export',
        { name, path, offset },
        signal,
      );
      expected ??= { size: result.size, sha256: result.sha256 };
      if (
        result.size !== expected.size ||
        result.sha256 !== expected.sha256 ||
        result.offset !== offset
      ) {
        throw new Error('Export identity or offset changed.');
      }
      const block = decode(result.data);
      if (!block.length && offset !== result.size) {
        throw new Error('Incomplete export.');
      }
      offset += block.length;
      if (offset > result.size) {
        throw new Error('Export overflow.');
      }
      blocks.push(block);
      if (offset === result.size) {
        break;
      }
    }
    const bytes = new Uint8Array(expected.size);
    let position = 0;
    for (const block of blocks) {
      bytes.set(block, position);
      position += block.length;
    }
    if ((await sha256(bytes)) !== expected.sha256) {
      throw new Error('Export hash mismatch.');
    }
    return bytes;
  }
}
