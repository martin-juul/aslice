import { afterEach, expect, it } from 'vitest';
import { Terminal } from '@xterm/headless';
import { SerializeAddon } from '@xterm/addon-serialize';
import { Unicode11Addon } from '@xterm/addon-unicode11';
import { ProgressAddon } from '@xterm/addon-progress';
import type { IProgressState } from '@xterm/addon-progress';
import { z } from 'zod';
import { displaySnapshot } from './display-snapshot';

const terminals: Terminal[] = [];

function createTerminal(): Terminal {
  const terminal = new Terminal({ cols: 40, rows: 6, allowProposedApi: true });
  terminal.loadAddon(new Unicode11Addon());
  terminal.unicode.activeVersion = '11';
  terminals.push(terminal);
  return terminal;
}

function write(terminal: Terminal, text: string): Promise<void> {
  return new Promise((resolve) => terminal.write(text, resolve));
}

afterEach(() => {
  for (const terminal of terminals.splice(0)) {
    terminal.dispose();
  }
});

it('exports and restores Unicode text, colors and cursor position with real xterm parsers', async () => {
  const terminal = createTerminal();
  const serializer = new SerializeAddon();
  terminal.loadAddon(serializer);
  await write(terminal, '\u001b[31mred\u001b[0m 漢字 😀\r\nsecond line');
  const bytes = displaySnapshot(
    serializer,
    { cols: 40, rows: 6 },
    { machine: 'sample', id: 'one' },
    '11',
  );
  const snapshot = z
    .object({
      data: z.string(),
      kind: z.literal('terminal-display'),
      unicodeVersion: z.literal('11'),
    })
    .parse(JSON.parse(new TextDecoder().decode(bytes)));
  const restored = createTerminal();
  await write(restored, snapshot.data);
  expect(restored.buffer.active.getLine(0)?.translateToString(true)).toBe(
    'red 漢字 😀',
  );
  expect(restored.buffer.active.getLine(0)?.getCell(0)?.getFgColor()).toBe(1);
  expect(restored.buffer.active.cursorX).toBe(terminal.buffer.active.cursorX);
  expect(restored.buffer.active.cursorY).toBe(terminal.buffer.active.cursorY);
});

it('parses program-reported progress and clears it explicitly', async () => {
  const terminal = createTerminal();
  const progress = new ProgressAddon();
  terminal.loadAddon(progress);
  const states: IProgressState[] = [];
  progress.onChange((value) => states.push(value));
  await write(terminal, '\u001b]9;4;1;42\u0007');
  expect(states.at(-1)).toEqual({ state: 1, value: 42 });
  await write(terminal, '\u001b]9;4;3\u0007');
  expect(states.at(-1)?.state).toBe(3);
  progress.progress = { state: 0, value: 0 };
  expect(states.at(-1)).toEqual({ state: 0, value: 0 });
});

it('keeps queued output and progress from the old session before the ordered reset', async () => {
  const terminal = createTerminal();
  const progress = new ProgressAddon();
  terminal.loadAddon(progress);
  terminal.write('OLD SESSION\u001b]9;4;1;42\u0007');
  terminal.write('\u001bc', () => {
    progress.progress = { state: 0, value: 0 };
  });
  await write(terminal, 'NEW SESSION');
  expect(terminal.buffer.active.getLine(0)?.translateToString(true)).toBe(
    'NEW SESSION',
  );
  expect(progress.progress.state).toBe(0);
});
