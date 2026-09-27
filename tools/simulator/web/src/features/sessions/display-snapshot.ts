import type { SerializeAddon } from '@xterm/addon-serialize';
import type { TerminalSize } from './model';

export interface DisplayIdentity {
  machine: string;
  id: string;
}

/** A rendered display export cannot resume a process or establish runtime evidence. */
export function displaySnapshot(
  serializer: SerializeAddon,
  size: TerminalSize,
  identity: DisplayIdentity,
  unicodeVersion: string,
): Uint8Array<ArrayBuffer> {
  const data = serializer.serialize({ scrollback: 4000 });
  const bytes = new TextEncoder().encode(
    JSON.stringify(
      {
        version: 1,
        kind: 'terminal-display',
        machine: identity.machine,
        session: identity.id,
        ...size,
        unicodeVersion,
        data,
        scope:
          'Rendered text, colors and cursor state; excludes images, process state and runtime evidence.',
      },
      null,
      2,
    ),
  );
  if (bytes.length > 16 * 1024 * 1024) {
    throw new Error(
      'Terminal display export exceeds 16 MiB. Reduce the scrollback before exporting.',
    );
  }
  return bytes;
}
