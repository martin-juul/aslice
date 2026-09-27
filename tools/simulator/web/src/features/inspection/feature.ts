import { bindAction, element, input, report } from '../../shared/ui';
import type { FeatureContext } from '../../shared/ui';

export function mountInspection(context: FeatureContext): void {
  const { root, gateway, selection, signal, notice } = context;
  let revision = 0;
  bindAction(context, 'inspect', async () => {
    const name = selection.require();
    const version = ++revision;
    const result = await gateway.execute('inspect', { name }, signal);
    if (name !== selection.current || version !== revision || signal.aborted) {
      return;
    }
    element(root, 'services', HTMLPreElement).textContent = result.services;
    element(root, 'changes', HTMLPreElement).textContent = JSON.stringify(
      result.changes,
      null,
      2,
    );
    element(root, 'network-activity', HTMLPreElement).textContent =
      result.network;
    const table = document.createElement('table');
    const header = table.createTHead().insertRow();
    for (const title of [
      'Linux PID',
      'Namespace PID',
      'Linux parent PID',
      'Command',
      'Action',
    ]) {
      const cell = document.createElement('th');
      cell.scope = 'col';
      cell.textContent = title;
      header.append(cell);
    }
    const body = table.createTBody();
    for (const process of result.processes) {
      const row = body.insertRow();
      for (const value of [
        process.pid,
        process.namespace_pid ?? '—',
        process.ppid,
        process.command,
      ]) {
        row.insertCell().textContent = String(value);
      }
      const button = document.createElement('button');
      button.textContent = 'Kill';
      button.addEventListener('click', () => {
        button.disabled = true;
        report(
          context,
          gateway
            .execute(
              'fault',
              { name, kind: 'process', pid: process.pid, start: process.start },
              signal,
            )
            .then(() => {
              notice('Process termination acknowledged; refresh to observe.');
            })
            .finally(() => {
              button.disabled = false;
            }),
        );
      });
      row.insertCell().append(button);
    }
    element(root, 'processes', HTMLDivElement).replaceChildren(table);
  });

  selection.subscribe(() => {
    ++revision;
    for (const id of ['processes', 'services', 'changes', 'network-activity']) {
      element(root, id, HTMLElement).replaceChildren();
    }
  }, signal);
  bindAction(context, 'service-stop', async () => {
    await gateway.execute(
      'fault',
      {
        name: selection.require(),
        kind: 'service',
        service: input(root, 'service-name').value,
      },
      signal,
    );
    notice('Guest service interruption acknowledged.');
  });
  bindAction(context, 'disk-full', async () => {
    await gateway.execute(
      'fault',
      { name: selection.require(), kind: 'disk-full', mib: 64 },
      signal,
    );
    notice('Full fault filesystem created at Imports/fault-disk.');
  });
  bindAction(context, 'disk-clear', async () => {
    await gateway.execute(
      'fault',
      { name: selection.require(), kind: 'disk-clear' },
      signal,
    );
    notice('Fault filesystem removed.');
  });
}
