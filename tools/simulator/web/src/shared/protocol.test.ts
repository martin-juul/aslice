import { expect, it, vi } from 'vitest';
import { Gateway } from './protocol';
import { HttpTransport } from './http-transport';
import { DemoTransport } from '../development/demo-transport';
import { MachineSelection } from '../features/machines/model';

it('rejects malformed responses at the boundary', async () => {
  const gateway = new Gateway({
    kind: 'live',
    authenticate: async () => {},
    send: async () => ({ machines: [{ name: 'incomplete' }] }),
  });
  await expect(gateway.execute('status', { name: null })).rejects.toThrow(
    'Invalid controller response',
  );
});

it('reports controller errors without treating them as successful results', async () => {
  const request = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(JSON.stringify({ error: 'machine is running' }), {
      status: 400,
    }),
  );
  const transport = new HttpTransport(request);
  await expect(
    transport.send({ action: 'stop', name: 'machine' }),
  ).rejects.toThrow('machine is running');
});

it('refuses running snapshots in the demo and supports stopped restoration', async () => {
  const gateway = new Gateway(new DemoTransport('normal'));
  const name = 'sample-mac';
  await gateway.execute('start', {
    name,
    acceleration: 'auto',
    network: false,
  });
  await expect(
    gateway.execute('snapshot', {
      name,
      snapshot: 'first',
      operation: 'create',
    }),
  ).rejects.toThrow('Stop the machine');
  await gateway.execute('stop', { name });
  await gateway.execute('snapshot', {
    name,
    snapshot: 'first',
    operation: 'create',
  });
  await expect(
    gateway.execute('snapshot', {
      name,
      snapshot: 'first',
      operation: 'restore',
    }),
  ).resolves.toEqual({});
  await expect(gateway.execute('inspect', { name })).resolves.toHaveProperty(
    'processes',
  );
});

it('disposes selection subscriptions and emits only changes', () => {
  const selection = new MachineSelection();
  const lifetime = new AbortController();
  const changed = vi.fn();
  selection.subscribe(changed, lifetime.signal);
  selection.select('one');
  selection.select('one');
  lifetime.abort();
  selection.select('two');
  expect(changed).toHaveBeenCalledExactlyOnceWith('one');
  expect(selection.require()).toBe('two');
});
