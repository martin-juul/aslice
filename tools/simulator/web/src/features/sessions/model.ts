import { z } from 'zod';

export type ExecutionMode = 'darwin' | 'linux';
export type DebuggerDisposition = 'detach' | 'terminate';

export interface TerminalSize {
  cols: number;
  rows: number;
}

export interface LaunchSession {
  name: string;
  mode: ExecutionMode;
  argv?: string[];
  program?: string | null;
  attach?: number | null;
  core?: string;
}

export const sessionSchema = z.object({
  id: z.string(),
  pid: z.number().int(),
  mode: z.enum(['darwin', 'linux']),
  kind: z.string(),
  exit_code: z.number().int().nullable(),
});

export const outputSchema = sessionSchema.extend({
  data: z.string(),
  cursor: z.number().int().nonnegative(),
  truncated: z.boolean(),
});

export const healthSchema = z.object({
  sessions: z.array(sessionSchema),
  runtime_health: z
    .object({
      state: z.string(),
      note: z.string().optional(),
      error: z.string().optional(),
    })
    .optional(),
});

export type SessionOutput = z.infer<typeof outputSchema>;
export type Session = z.infer<typeof sessionSchema>;

export function sourceMapCommand(value: string): string {
  const parts = value.split('→').map((part) => part.trim());
  if (parts.length !== 2 || parts.some((part) => !part)) {
    throw new Error('Use build path → guest path.');
  }
  return `settings set target.source-map ${parts.map((part) => JSON.stringify(part)).join(' ')}\n`;
}
