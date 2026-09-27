import { z } from 'zod';
import { machineSchema } from '../features/machines/model';
import type { Acceleration, CreateMachine } from '../features/machines/model';
import {
  healthSchema,
  outputSchema,
  sessionSchema,
} from '../features/sessions/model';
import type {
  DebuggerDisposition,
  LaunchSession,
  TerminalSize,
} from '../features/sessions/model';
import { inspectionSchema } from '../features/inspection/model';
import type { Fault } from '../features/inspection/model';
import { exportSchema } from '../features/transfers/model';
import { logsSchema } from '../features/console/model';

type MachineTarget = { name: string };
type SessionTarget = MachineTarget & { session: string };

export interface Parameters {
  logs: MachineTarget & { source: string };
  status: { name: null };
  create: CreateMachine;
  start: MachineTarget & { acceleration: Acceleration; network: boolean };
  stop: MachineTarget & { force?: boolean };
  clone: MachineTarget & { destination: string };
  delete: MachineTarget;
  snapshot: MachineTarget & {
    snapshot: string;
    operation: 'create' | 'restore';
  };
  network: MachineTarget & { up: boolean };
  health: MachineTarget;
  shell: LaunchSession;
  exec: LaunchSession;
  debug: LaunchSession;
  'session-read': SessionTarget & { cursor: number };
  'session-write': SessionTarget & { data: string };
  'session-resize': SessionTarget & TerminalSize;
  'session-close': SessionTarget & { disposition: DebuggerDisposition };
  inspect: MachineTarget;
  fault: MachineTarget & Fault;
  timeline: MachineTarget & { query: string };
  diagnostics: MachineTarget;
  'import-begin': MachineTarget & {
    path: string;
    size: number;
    sha256: string;
    executable: boolean;
  };
  'import-chunk': MachineTarget & {
    transfer: string;
    offset: number;
    data: string;
  };
  'import-commit': MachineTarget & { transfer: string };
  'import-abort': MachineTarget & { transfer: string };
  export: MachineTarget & { path: string; offset: number };
}

const acknowledgment = z.record(z.string(), z.unknown());

const responses = {
  logs: logsSchema,
  status: z.object({ machines: z.array(machineSchema) }),
  create: acknowledgment,
  start: z.object({ accelerator: z.string() }),
  stop: z.object({ observed: z.boolean() }),
  clone: acknowledgment,
  delete: acknowledgment,
  snapshot: acknowledgment,
  network: acknowledgment,
  health: healthSchema,
  shell: sessionSchema,
  exec: sessionSchema,
  debug: sessionSchema,
  'session-read': outputSchema,
  'session-write': acknowledgment,
  'session-resize': acknowledgment,
  'session-close': acknowledgment,
  inspect: inspectionSchema,
  fault: acknowledgment,
  timeline: z.object({ events: z.array(z.unknown()) }),
  diagnostics: z.object({ archive: z.string(), format: z.literal('zip') }),
  'import-begin': z.object({ transfer: z.string() }),
  'import-chunk': acknowledgment,
  'import-commit': acknowledgment,
  'import-abort': acknowledgment,
  export: exportSchema,
} satisfies Record<keyof Parameters, z.ZodType>;

export type Action = keyof Parameters;
export type Result<A extends Action> = z.infer<(typeof responses)[A]>;
export type Command = { [A in Action]: { action: A } & Parameters[A] }[Action];

export interface Transport {
  readonly kind: 'live' | 'demo';
  authenticate(token: string): Promise<void>;
  send(command: Command, signal?: AbortSignal): Promise<unknown>;
}

/** Runtime validation is performed once, where untrusted controller data enters. */
export class Gateway {
  constructor(readonly transport: Transport) {}

  async execute<A extends Action>(
    action: A,
    parameters: Parameters[A],
    signal?: AbortSignal,
  ): Promise<Result<A>> {
    // The mapped union preserves each action's parameter/result relationship.
    const command = { ...parameters, action } as Command;
    const raw = await this.transport.send(command, signal);
    const parsed = responses[action].safeParse(raw);
    if (!parsed.success) {
      throw new Error(
        `Invalid controller response for ${action}: ${parsed.error.message}`,
      );
    }
    return parsed.data as Result<A>;
  }
}
