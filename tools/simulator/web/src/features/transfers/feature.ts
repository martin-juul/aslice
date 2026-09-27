import { download } from '../../shared/bytes';
import { bindAction, input } from '../../shared/ui';
import type { FeatureContext } from '../../shared/ui';
import { FileTransfers } from './service';
import { TRANSFER_LIMIT } from './model';

export function mountTransfers(context: FeatureContext): void {
  const { root, gateway, selection, signal, notice } = context;
  const service = new FileTransfers(gateway);
  bindAction(context, 'import', async () => {
    const name = selection.require();
    const file = input(root, 'file').files?.[0];
    if (!file || file.size > TRANSFER_LIMIT) {
      throw new Error('Select one file, at most 64 MiB.');
    }
    const path = input(root, 'transfer-path').value || file.name;
    const executable = input(root, 'executable').checked;
    const bytes = new Uint8Array(await file.arrayBuffer());
    await service.import(name, path, bytes, executable, signal);
    notice(`File imported into ${name} with a verified hash.`);
  });
  bindAction(context, 'export', async () => {
    const name = selection.require();
    const path = input(root, 'transfer-path').value;
    const bytes = await service.export(name, path, signal);
    download(bytes, path.split('/').at(-1) ?? 'export');
  });
}
