import { z } from 'zod';

export const processSchema = z.object({
  pid: z.number().int(),
  namespace_pid: z.number().int().nullable().optional(),
  ppid: z.number().int(),
  command: z.string(),
  start: z.string(),
});

export const inspectionSchema = z.object({
  processes: z.array(processSchema),
  services: z.string(),
  network: z.string(),
  changes: z.unknown(),
});

export type Fault =
  | { kind: 'process'; pid: number; start: string }
  | { kind: 'service'; service: string }
  | { kind: 'disk-full'; mib: number }
  | { kind: 'disk-clear' };
