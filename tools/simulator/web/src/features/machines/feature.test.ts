// @vitest-environment jsdom
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { DemoTransport } from '../../development/demo-transport';
import { Gateway } from '../../shared/protocol';
import { MachineSelection } from './model';
import { mountMachines } from './feature';

let lifetime: AbortController;

beforeEach(() => {
  document.body.innerHTML = `
    <div id="machines"></div><div id="identity"></div>
    <span id="selected-machine"></span><form id="create"><button>Create</button></form>
    <select id="acceleration"><option value="auto">Automatic</option></select>
    <input id="network" type="checkbox"><input id="snapshot-name" value="saved">
    ${[
      'refresh',
      'start',
      'stop',
      'force',
      'clone',
      'delete',
      'snapshot',
      'restore',
      'network-loss',
    ]
      .map((id) => `<button id="${id}">${id}</button>`)
      .join('')}`;
  lifetime = new AbortController();
});

afterEach(() => {
  lifetime.abort();
  vi.restoreAllMocks();
});

function button(id: string): HTMLButtonElement {
  const node = document.getElementById(id);
  if (!(node instanceof HTMLButtonElement)) {
    throw new Error(`Missing button fixture: ${id}`);
  }
  return node;
}

function mount(transport = new DemoTransport('normal')) {
  return mountMachines({
    root: document,
    gateway: new Gateway(transport),
    selection: new MachineSelection(),
    signal: lifetime.signal,
    notice: vi.fn(),
  });
}

test('lifecycle controls follow observed state after actions settle', async () => {
  const machines = mount();
  expect(button('start').disabled).toBe(true);
  await machines.refresh();
  expect(button('start').disabled).toBe(false);
  expect(button('stop').disabled).toBe(true);
  expect(button('snapshot').disabled).toBe(false);
  button('start').click();
  await vi.waitFor(() => expect(button('stop').disabled).toBe(false));
  expect(button('start').disabled).toBe(true);
  expect(button('snapshot').disabled).toBe(true);
  expect(button('delete').disabled).toBe(true);
  button('stop').click();
  await vi.waitFor(() => expect(button('start').disabled).toBe(false));
  expect(button('stop').disabled).toBe(true);
});

test('refresh cannot enable conflicting actions during a pending operation', async () => {
  const transport = new DemoTransport('normal');
  const send = transport.send.bind(transport);
  const pending = Promise.withResolvers<void>();
  vi.spyOn(transport, 'send').mockImplementation(async (command, signal) => {
    if (command.action === 'start') {
      await pending.promise;
    }
    return send(command, signal);
  });
  const machines = mount(transport);
  await machines.refresh();
  button('start').click();
  await vi.waitFor(() => expect(button('clone').disabled).toBe(true));
  await machines.refresh();
  expect(button('start').disabled).toBe(true);
  expect(button('clone').disabled).toBe(true);
  pending.resolve();
  await vi.waitFor(() => expect(button('stop').disabled).toBe(false));
  expect(button('start').disabled).toBe(true);
});

test('failed status refresh makes stale state explicit until recovery', async () => {
  const transport = new DemoTransport('normal');
  const machines = mount(transport);
  await machines.refresh();
  const spy = vi.spyOn(transport, 'send');
  spy.mockRejectedValueOnce(new Error('Controller unavailable'));
  await expect(machines.refresh()).rejects.toThrow('Controller unavailable');
  expect(button('start').disabled).toBe(true);
  expect(button('delete').disabled).toBe(true);
  expect(document.getElementById('selected-machine')?.textContent).toContain(
    'Status unavailable',
  );
  await machines.refresh();
  expect(button('start').disabled).toBe(false);
});

test('empty inventories explain how to create a machine', async () => {
  await mount(new DemoTransport('empty')).refresh();
  expect(document.getElementById('machines')?.textContent).toContain(
    'No machines yet',
  );
  expect(button('start').disabled).toBe(true);
  expect(button('delete').disabled).toBe(true);
});

test('refresh preserves focus in the selected machine row', async () => {
  const machines = mount();
  await machines.refresh();
  const row = document.querySelector<HTMLButtonElement>('.machine-row');
  row?.focus();
  await machines.refresh();
  expect(document.activeElement?.getAttribute('data-machine')).toBe(
    'sample-mac',
  );
  expect(document.activeElement?.getAttribute('aria-pressed')).toBe('true');
});
