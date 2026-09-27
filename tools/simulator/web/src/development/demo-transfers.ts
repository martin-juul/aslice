import { decode, encode, sha256 } from '../shared/bytes';
import type { Command } from '../shared/protocol';
import { CHUNK_SIZE } from '../features/transfers/model';

type TransferCommand = Extract<
  Command,
  {
    action:
      | 'import-begin'
      | 'import-chunk'
      | 'import-commit'
      | 'import-abort'
      | 'export';
  }
>;

export class DemoTransfers {
  private files = new Map<string, Uint8Array<ArrayBuffer>>();
  private pending = new Map<
    string,
    {
      name: string;
      path: string;
      digest: string;
      bytes: Uint8Array<ArrayBuffer>;
      offset: number;
    }
  >();

  async execute(command: TransferCommand): Promise<unknown> {
    if (command.action === 'export') {
      const bytes = this.files.get(`${command.name}/${command.path}`);
      if (!bytes) {
        throw new Error('Import a sample file before exporting it.');
      }
      return {
        size: bytes.length,
        offset: command.offset,
        sha256: await sha256(bytes),
        data: encode(
          bytes.subarray(command.offset, command.offset + CHUNK_SIZE),
        ),
      };
    }
    if (command.action === 'import-begin') {
      const transfer = crypto.randomUUID();
      this.pending.set(transfer, {
        name: command.name,
        path: command.path,
        digest: command.sha256,
        bytes: new Uint8Array(command.size),
        offset: 0,
      });
      return { transfer };
    }
    const pending = this.pending.get(command.transfer);
    if (!pending || pending.name !== command.name) {
      throw new Error('Unknown demo transfer.');
    }
    if (command.action === 'import-abort') {
      this.pending.delete(command.transfer);
    } else if (command.action === 'import-chunk') {
      if (pending.offset !== command.offset) {
        throw new Error('Unexpected transfer offset.');
      }
      const bytes = decode(command.data);
      pending.bytes.set(bytes, pending.offset);
      pending.offset += bytes.length;
    } else {
      if (
        pending.offset !== pending.bytes.length ||
        (await sha256(pending.bytes)) !== pending.digest
      ) {
        throw new Error('Incomplete demo transfer.');
      }
      this.files.set(`${pending.name}/${pending.path}`, pending.bytes);
      this.pending.delete(command.transfer);
    }
    return {};
  }
}
