import { DEMO_OUTPUT_LIMIT } from './demo-output';

export const terminalSamples = {
  unicode:
    '\r\nUI sample: \u001b[32mcolored text\u001b[0m · 漢字 · Ω · e\u0301\r\n',
  progress: '\u001b]9;4;1;42\u0007',
  busy: '\u001b]9;4;3\u0007',
  paused: '\u001b]9;4;4;42\u0007',
  error: '\u001b]9;4;2;42\u0007',
  clear: '\u001b]9;4;0\u0007',
  image:
    '\r\nSample red image:\r\n\u001bPq"1;1;24;6#0;2;100;0;0#0!24~\u001b\\\r\n',
  truncated: 'Sample captured output\r\n'.repeat(
    Math.ceil(DEMO_OUTPUT_LIMIT / 10),
  ),
} as const;

export type TerminalSample =
  keyof typeof terminalSamples | 'disconnect' | 'exit';
