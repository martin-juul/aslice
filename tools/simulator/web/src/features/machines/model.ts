import { z } from 'zod';

export const machineSchema = z.object({
  name: z.string(),
  state: z.string(),
  cpus: z.number().int().positive(),
  memory_mib: z.number().int().positive(),
  disk_gib: z.number().positive(),
  base: z.string(),
  runtime_sha256: z.string(),
  capabilities: z.unknown(),
});

export type Machine = z.infer<typeof machineSchema>;
export type Acceleration = 'auto' | 'kvm' | 'whpx' | 'tcg';

export interface CreateMachine {
  name: string;
  image: string;
  runtime: string;
  cpus: number;
  memory_mib: number;
  disk_gib: number;
}

/** Selection is UI state; it never implies ownership of a running machine. */
export class MachineSelection {
  private name: string | null = null;
  private selectionRevision = 0;
  private listeners = new Set<(name: string | null) => void>();

  get current(): string | null {
    return this.name;
  }

  get revision(): number {
    return this.selectionRevision;
  }

  require(): string {
    if (!this.name) {
      throw new Error('Select a machine first.');
    }
    return this.name;
  }

  select(name: string | null): void {
    if (name === this.name) {
      return;
    }
    this.name = name;
    this.selectionRevision += 1;
    for (const listener of this.listeners) {
      listener(name);
    }
  }

  subscribe(
    listener: (name: string | null) => void,
    signal: AbortSignal,
  ): void {
    if (signal.aborted) {
      return;
    }
    this.listeners.add(listener);
    signal.addEventListener('abort', () => this.listeners.delete(listener), {
      once: true,
    });
  }
}
