import type { SessionOutput } from './model';

interface Source {
  read(
    machine: string,
    session: string,
    cursor: number,
    signal: AbortSignal,
  ): Promise<SessionOutput>;
}

/** One polling chain per selection. Old responses cannot write into a new terminal. */
export class OutputStream {
  private active: AbortController | undefined;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private target: { machine: string; session: string } | undefined;
  private cursor = 0;

  constructor(
    private readonly source: Source,
    private readonly receive: (output: SessionOutput) => void,
    private readonly failed: (error: unknown) => void,
  ) {}

  follow(machine: string, session: string): void {
    this.stop();
    this.target = { machine, session };
    this.reconnect();
  }

  reconnect(): void {
    const target = this.target;
    if (!target) {
      throw new Error('Choose a session before reconnecting its output.');
    }
    this.cancelRead();
    const active = new AbortController();
    this.active = active;
    const poll = async (): Promise<void> => {
      try {
        const output = await this.source.read(
          target.machine,
          target.session,
          this.cursor,
          active.signal,
        );
        if (active.signal.aborted) {
          return;
        }
        this.receive(output);
        this.cursor = output.cursor;
        if (output.exit_code === null) {
          this.timer = setTimeout(() => {
            void poll();
          }, 300);
        }
      } catch (error) {
        if (!active.signal.aborted) {
          this.failed(error);
        }
      }
    };
    void poll();
  }

  stop(): void {
    this.cancelRead();
    this.target = undefined;
    this.cursor = 0;
  }

  private cancelRead(): void {
    this.active?.abort();
    this.active = undefined;
    clearTimeout(this.timer);
    this.timer = undefined;
  }
}
