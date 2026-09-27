// @vitest-environment jsdom
import { expect, it, vi } from 'vitest';
import { bindAction } from './ui';
import { Gateway } from './protocol';
import { DemoTransport } from '../development/demo-transport';
import { MachineSelection } from '../features/machines/model';

it('disables pending actions, reports failures, and removes disposed listeners', async () => {
  document.body.innerHTML = '<button id="run">Run</button>';
  const button = document.querySelector('button');
  if (!button) {
    throw new Error('Missing fixture button');
  }
  const pending = Promise.withResolvers<void>();
  const action = vi.fn(() => pending.promise);
  const notice = vi.fn();
  const lifetime = new AbortController();
  bindAction(
    {
      root: document,
      gateway: new Gateway(new DemoTransport('normal')),
      selection: new MachineSelection(),
      signal: lifetime.signal,
      notice,
    },
    'run',
    action,
  );
  button.click();
  expect(button.disabled).toBe(true);
  button.click();
  await Promise.resolve();
  expect(action).toHaveBeenCalledTimes(1);
  pending.reject(new Error('Operation failed'));
  await vi.waitFor(() =>
    expect(notice).toHaveBeenCalledWith('Operation failed', true),
  );
  expect(button.disabled).toBe(false);
  lifetime.abort();
  button.click();
  expect(action).toHaveBeenCalledTimes(1);
});
