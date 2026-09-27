import type { Command, Transport } from '../shared/protocol';
import type { Machine } from '../features/machines/model';
import { DemoTransfers } from './demo-transfers';
import { DemoSessions } from './demo-sessions';
import type { TerminalSample } from './terminal-samples';

const sample: Machine = {
  name: 'sample-mac',
  state: 'stopped',
  cpus: 4,
  memory_mib: 8192,
  disk_gib: 64,
  base: 'demo-only',
  runtime_sha256: 'demo-runtime-not-installed',
  capabilities: {
    cli: 'unverified',
    cocoa: 'unverified',
    debugger: 'unverified',
  },
};

/** Development adapter: never contacts the controller or claims runtime evidence. */
export class DemoTransport implements Transport {
  readonly kind = 'demo';
  private machines: Machine[];
  private snapshots = new Set<string>();
  private events: object[] = [];
  private transfers = new DemoTransfers();
  private sessions = new DemoSessions();

  constructor(
    private readonly scenario = new URLSearchParams(
      globalThis.location?.search,
    ).get('scenario') ?? 'normal',
  ) {
    this.machines = scenario === 'empty' ? [] : [{ ...sample }];
  }

  async authenticate(): Promise<void> {}

  sampleTerminal(name: string, id: string, sample: TerminalSample): void {
    this.sessions.sample(name, id, sample);
  }

  async send(command: Command, signal?: AbortSignal): Promise<unknown> {
    signal?.throwIfAborted();
    if (this.scenario === 'error') {
      throw new Error('Demo controller failure requested by ?scenario=error.');
    }
    if (this.scenario === 'slow') {
      await new Promise<void>((resolve) => setTimeout(resolve, 1500));
      signal?.throwIfAborted();
    }
    if (command.action === 'status') {
      return { machines: structuredClone(this.machines) };
    }
    if (command.action === 'create') {
      if (this.machines.some((machine) => machine.name === command.name)) {
        throw new Error('Machine already exists.');
      }
      this.machines.push({ ...sample, ...command, base: command.image });
      return {};
    }
    const machine = this.machines.find((item) => item.name === command.name);
    if (!machine) {
      throw new Error('Unknown demo machine.');
    }
    if (
      !['health', 'session-read', 'timeline', 'logs'].includes(command.action)
    ) {
      this.events.push({
        action: command.action,
        machine: machine.name,
        effect: 'demo only',
        time: new Date().toISOString(),
      });
    }
    switch (command.action) {
      case 'logs':
        return {
          source: command.source,
          available: true,
          truncated: false,
          note: 'Sample Console messages only; no guest logging store is connected.',
          records: [
            {
              id: 'demo-info',
              time: '12:00:00',
              process: 'SampleApp',
              pid: '42',
              type: 'info',
              subsystem: 'org.aslice.sample',
              category: 'document',
              message: 'Opened sample document',
              raw: 'Demo record: document opened',
            },
            {
              id: 'demo-error',
              time: '12:00:01',
              process: 'SampleApp',
              pid: '42',
              type: 'error',
              subsystem: 'org.aslice.sample',
              category: 'document',
              message: 'Sample permission denied',
              raw: 'Demo record: permission denied',
            },
          ],
        };
      case 'start':
        machine.state = 'running';
        return { accelerator: 'demo (no VM)' };
      case 'stop':
        machine.state = 'stopped';
        return { observed: true };
      case 'delete':
        this.stopped(machine);
        this.machines = this.machines.filter((item) => item !== machine);
        return {};
      case 'clone':
        this.stopped(machine);
        if (this.machines.some((item) => item.name === command.destination)) {
          throw new Error('Machine already exists.');
        }
        this.machines.push({ ...machine, name: command.destination });
        return {};
      case 'snapshot': {
        this.stopped(machine);
        const key = `${machine.name}/${command.snapshot}`;
        if (command.operation === 'restore' && !this.snapshots.has(key)) {
          throw new Error('Unknown demo snapshot.');
        }
        this.snapshots.add(key);
        return {};
      }
      case 'health':
        return {
          sessions: this.sessions.list(machine.name),
          runtime_health: {
            state: 'demo',
            note: 'No Darling runtime is connected.',
          },
        };
      case 'shell':
      case 'exec':
      case 'debug':
      case 'session-read':
      case 'session-write':
      case 'session-resize':
      case 'session-close':
        if (machine.state !== 'running') {
          throw new Error('Start the demo machine first.');
        }
        return this.sessions.execute(command);
      case 'import-begin':
      case 'import-chunk':
      case 'import-commit':
      case 'import-abort':
      case 'export':
        return this.transfers.execute(command);
      case 'inspect':
        return {
          processes: [
            {
              pid: 401,
              namespace_pid: 21,
              ppid: 1,
              command: 'sample-process (demo)',
              start: 'demo-start',
            },
          ],
          services: 'sample.service: demo',
          network: 'Network disabled (sample)',
          changes: [{ path: 'Imports/example.txt', effect: 'sample only' }],
        };
      case 'timeline':
        return {
          events: this.events.filter((event) =>
            JSON.stringify(event).includes(command.query),
          ),
        };
      case 'diagnostics':
        throw new Error(
          'Runtime diagnostic archives require a live simulator. This UI is using sample data.',
        );
      case 'fault':
      case 'network':
        return {
          observed: false,
          note: 'Recorded UI demonstration; no runtime effect.',
        };
    }
  }

  private stopped(machine: Machine): void {
    if (machine.state !== 'stopped') {
      throw new Error('Stop the machine before this operation.');
    }
  }
}
