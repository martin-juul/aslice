import { bindAction, element, input, report } from '../../shared/ui';
import type { FeatureContext } from '../../shared/ui';
import type { Acceleration, Machine } from './model';
import { unavailableReason } from './actions';
import type { MachineAction } from './actions';
import { renderMachineList } from './list';
import type { MachineListStatus } from './list';
import { mountMachineDetails } from './details';

function textField(data: FormData, name: string): string {
  const value = data.get(name);
  if (typeof value !== 'string') {
    throw new Error(`Missing text field: ${name}`);
  }
  return value;
}

export function mountMachines(context: FeatureContext): {
  refresh: () => Promise<void>;
} {
  const { root, gateway, selection, signal, notice } = context;
  const list = element(root, 'machines', HTMLDivElement);
  const identity = element(root, 'identity', HTMLDivElement);
  const renderDetails = mountMachineDetails(identity);
  const selectedMachine = element(root, 'selected-machine', HTMLSpanElement);
  let machines: Machine[] = [];
  let refreshVersion = 0;
  let status: MachineListStatus = 'loading';
  let operationPending = false;
  const actionRefreshers: (() => void)[] = [];

  function selected(): Machine | undefined {
    return machines.find((machine) => machine.name === selection.current);
  }

  function renderActions(): void {
    for (const update of actionRefreshers) {
      update();
    }
  }

  function bindMachineAction(
    id: MachineAction,
    action: () => Promise<void>,
  ): void {
    const button = element(root, id, HTMLButtonElement);
    const label = button.textContent?.trim() ?? '';
    const reason = (): string | undefined =>
      unavailableReason(id, selected(), status === 'ready', operationPending);
    const update = bindAction(
      context,
      id,
      async () => {
        operationPending = true;
        renderActions();
        try {
          await action();
        } catch (error) {
          if (status !== 'unavailable') {
            try {
              await refresh();
            } catch {
              // Preserve the operation error; refresh already marks state unknown.
            }
          }
          throw error;
        } finally {
          operationPending = false;
          renderActions();
        }
      },
      () => reason() === undefined,
    );
    actionRefreshers.push(() => {
      button.title = reason() ?? label;
      update();
    });
  }

  function render(): void {
    renderMachineList(list, machines, selection.current, status, (name) =>
      selection.select(name),
    );
    renderActions();
    const machine = selected();
    selectedMachine.textContent = machine
      ? `${machine.name} · ${status === 'ready' ? machine.state : 'Status unavailable'}`
      : 'No machine selected.';
    renderDetails(machine);
  }

  async function refresh(): Promise<void> {
    const version = ++refreshVersion;
    let result;
    try {
      result = await gateway.execute('status', { name: null }, signal);
    } catch (error) {
      if (!signal.aborted && version === refreshVersion) {
        status = 'unavailable';
        render();
      }
      throw error;
    }
    if (signal.aborted || version !== refreshVersion) {
      return;
    }
    status = 'ready';
    machines = result.machines;
    if (!machines.some((machine) => machine.name === selection.current)) {
      selection.select(machines[0]?.name ?? null);
    }
    render();
  }

  selection.subscribe(render, signal);
  bindAction(context, 'refresh', refresh);

  const form = element(root, 'create', HTMLFormElement);
  form.addEventListener(
    'submit',
    (event) => {
      event.preventDefault();
      const data = new FormData(form);
      const name = textField(data, 'name');
      const button = form.querySelector('button');
      if (button) {
        button.disabled = true;
      }
      report(
        context,
        gateway
          .execute(
            'create',
            {
              name,
              image: textField(data, 'image'),
              runtime: textField(data, 'runtime'),
              cpus: Number(data.get('cpus')),
              memory_mib: Number(data.get('memory_mib')),
              disk_gib: Number(data.get('disk_gib')),
            },
            signal,
          )
          .then(async () => {
            selection.select(name);
            await refresh();
            notice('Machine created.');
          })
          .finally(() => {
            if (button) {
              button.disabled = false;
            }
          }),
      );
    },
    { signal },
  );

  bindMachineAction('start', async () => {
    const acceleration = element(root, 'acceleration', HTMLSelectElement).value;
    const allowed: readonly string[] = [
      'auto',
      'kvm',
      'whpx',
      'tcg',
    ] satisfies readonly Acceleration[];
    if (!allowed.includes(acceleration)) {
      throw new Error('Invalid acceleration mode.');
    }
    const result = await gateway.execute(
      'start',
      {
        name: selection.require(),
        acceleration: acceleration as Acceleration,
        network: input(root, 'network').checked,
      },
      signal,
    );
    notice(
      `Starting with ${result.accelerator}. Guest services may take a minute.`,
    );
    await refresh();
  });

  for (const id of ['stop', 'force'] as const) {
    bindMachineAction(id, async () => {
      const result = await gateway.execute(
        'stop',
        { name: selection.require(), force: id === 'force' },
        signal,
      );
      notice(
        result.observed
          ? 'VM stopped.'
          : 'Shutdown requested; VM is still running.',
      );
      await refresh();
    });
  }

  bindMachineAction('clone', async () => {
    const name = selection.require();
    const destination = prompt('New machine name');
    if (destination) {
      await gateway.execute('clone', { name, destination }, signal);
      await refresh();
    }
  });

  bindMachineAction('delete', async () => {
    await gateway.execute('delete', { name: selection.require() }, signal);
    selection.select(null);
    await refresh();
    notice('Machine moved to recoverable host trash.');
  });

  for (const [id, operation] of [
    ['snapshot', 'create'],
    ['restore', 'restore'],
  ] as const) {
    bindMachineAction(id, async () => {
      await gateway.execute(
        'snapshot',
        {
          name: selection.require(),
          snapshot: input(root, 'snapshot-name').value,
          operation,
        },
        signal,
      );
      notice(
        operation === 'create'
          ? 'Stopped-machine snapshot created.'
          : 'Snapshot restored; previous disk retained.',
      );
      await refresh();
    });
  }

  bindMachineAction('network-loss', async () => {
    await gateway.execute(
      'network',
      { name: selection.require(), up: false },
      signal,
    );
    notice(
      'Application network disabled. Management tunnel remains available.',
    );
  });
  render();
  return { refresh };
}
