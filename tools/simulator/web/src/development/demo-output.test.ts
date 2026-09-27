import { expect, it } from 'vitest';
import { DemoOutput, DEMO_OUTPUT_LIMIT } from './demo-output';
import { decode } from '../shared/bytes';
import { DemoTransport } from './demo-transport';
import { Gateway } from '../shared/protocol';

it('uses byte cursors for multibyte Unicode and reads only newly appended bytes', () => {
  const output = new DemoOutput();
  output.append('漢字 😀');
  const first = output.read(0);
  expect(first.cursor).toBe(new TextEncoder().encode('漢字 😀').length);
  expect(new TextDecoder().decode(decode(first.data))).toBe('漢字 😀');
  output.append(' next');
  expect(new TextDecoder().decode(decode(output.read(first.cursor).data))).toBe(
    ' next',
  );
  expect(output.read(0).truncated).toBe(false);
});

it('retains a bounded suffix and reports discarded output with absolute cursors', () => {
  const output = new DemoOutput();
  output.append('a'.repeat(DEMO_OUTPUT_LIMIT - 2));
  output.append('bcdef');
  const result = output.read(0);
  expect(result.cursor).toBe(DEMO_OUTPUT_LIMIT + 3);
  expect(result.truncated).toBe(true);
  expect(decode(result.data)).toHaveLength(DEMO_OUTPUT_LIMIT);
  expect(new TextDecoder().decode(decode(result.data))).toBe(
    'a'.repeat(DEMO_OUTPUT_LIMIT - 5) + 'bcdef',
  );
  output.append('z'.repeat(DEMO_OUTPUT_LIMIT * 2));
  const next = output.read(result.cursor);
  expect(next.truncated).toBe(true);
  expect(next.cursor).toBe(DEMO_OUTPUT_LIMIT * 3 + 3);
  expect(new TextDecoder().decode(decode(next.data))).toBe(
    'z'.repeat(DEMO_OUTPUT_LIMIT),
  );
});

it('interrupts one demo read, then lets the same session resume from its cursor', async () => {
  const transport = new DemoTransport('normal');
  const gateway = new Gateway(transport);
  const name = 'sample-mac';
  await gateway.execute('start', {
    name,
    acceleration: 'auto',
    network: false,
  });
  const session = await gateway.execute('shell', { name, mode: 'darwin' });
  const first = await gateway.execute('session-read', {
    name,
    session: session.id,
    cursor: 0,
  });
  transport.sampleTerminal(name, session.id, 'disconnect');
  await expect(
    gateway.execute('session-read', {
      name,
      session: session.id,
      cursor: first.cursor,
    }),
  ).rejects.toThrow('interrupted');
  transport.sampleTerminal(name, session.id, 'unicode');
  const result = await gateway.execute('session-read', {
    name,
    session: session.id,
    cursor: first.cursor,
  });
  expect(new TextDecoder().decode(decode(result.data))).toContain('漢字');
  expect(result.id).toBe(session.id);
  transport.sampleTerminal(name, session.id, 'exit');
  const ended = await gateway.execute('session-read', {
    name,
    session: session.id,
    cursor: result.cursor,
  });
  expect(ended.exit_code).toBe(0);
  expect(() => transport.sampleTerminal(name, session.id, 'unicode')).toThrow(
    'running demo',
  );
});
