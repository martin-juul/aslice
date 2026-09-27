// @vitest-environment jsdom
import { beforeEach, expect, test } from 'vitest';
import { mountMachineDetails } from './details';
import type { Machine } from './model';

const machine: Machine = {
  name: 'test-mac',
  state: 'stopped',
  cpus: 4,
  memory_mib: 8192,
  disk_gib: 64,
  base: 'base-image-id',
  runtime_sha256: 'runtime-id',
  capabilities: { 'unchanged-cli': 'pending', 'cocoa-input': 'unverified' },
};

let container: HTMLDivElement;

beforeEach(() => {
  container = document.createElement('div');
  document.body.replaceChildren(container);
});

function disclosure(): HTMLDetailsElement {
  const details = container.querySelector('details');
  if (!details) {
    throw new Error('Missing technical details');
  }
  return details;
}

test('renders readable configuration without exposing raw data by default', () => {
  mountMachineDetails(container)(machine);
  const values = [...container.querySelectorAll('dd')].map(
    (row) => row.textContent,
  );
  expect(values).toContain('8 GiB');
  expect(values).toContain('64 GiB');
  expect(values).toContain('Pending verification');
  expect(values).toContain('Unverified');
  expect(disclosure().open).toBe(false);
  expect(disclosure().textContent).toContain('runtime-id');
  expect(JSON.parse(container.querySelector('pre')?.textContent ?? '')).toEqual(
    machine.capabilities,
  );
});

test('unknown capability data stays inspectable without implying success', () => {
  const render = mountMachineDetails(container);
  render({
    ...machine,
    memory_mib: 1536,
    capabilities: {
      'new-gate': { status: true, note: '<img src=x onerror=alert(1)>' },
      'unchanged-cli': 'custom result',
    },
  });
  expect(container.textContent).toContain('1536 MiB');
  expect(container.textContent).toContain('See technical details');
  expect(container.textContent).toContain('custom result');
  expect(container.textContent).not.toContain('Reported passed');
  expect(container.querySelector('img')).toBeNull();
  expect(container.querySelector('pre')?.textContent).toContain('<img');
  render({ ...machine, capabilities: false });
  expect(container.textContent).toContain(
    'See Technical details for the reported capability data.',
  );
  expect(container.querySelector('pre')?.textContent).toBe('false');
  render({ ...machine, capabilities: {} });
  expect(container.textContent).toContain('No capability results reported.');
});

test('keeps technical disclosure open on refresh and closes it on selection change', () => {
  const render = mountMachineDetails(container);
  render(machine);
  const details = disclosure();
  details.open = true;
  render({ ...machine, state: 'running' });
  expect(disclosure()).toBe(details);
  expect(details.open).toBe(true);
  render({ ...machine, name: 'other-mac' });
  expect(details.open).toBe(false);
  render(undefined);
  expect(container.hidden).toBe(true);
  expect(container.textContent).not.toContain('base-image-id');
});
