import type { Gateway } from '../../shared/protocol';
import { encode } from '../../shared/bytes';
import type { DebuggerDisposition, Session, TerminalSize } from './model';
import { InputQueue } from './input-queue';

/** A connection is bound to one guest session for its entire lifetime. */
export class SessionConnection {
  private closing = false;

  constructor(
    readonly machine: string,
    private session: Session,
    private readonly gateway: Gateway,
    private readonly signal: AbortSignal,
    private readonly input: InputQueue = new InputQueue(),
  ) {}

  get id(): string {
    return this.session.id;
  }

  update(session: Session): void {
    if (session.id !== this.id) {
      throw new Error('Cannot change the identity of a session connection.');
    }
    this.session = {
      ...session,
      exit_code: this.session.exit_code ?? session.exit_code,
    };
  }

  async send(text: string, debuggerCommand = false): Promise<void> {
    this.requireActive(debuggerCommand);
    const bytes = new TextEncoder().encode(text);
    if (bytes.length > 65536) {
      throw new Error('Terminal input exceeds 64 KiB. Paste a smaller block.');
    }
    await this.input.enqueue(async () => {
      this.signal.throwIfAborted();
      await this.gateway.execute(
        'session-write',
        {
          name: this.machine,
          session: this.id,
          data: encode(bytes),
        },
        this.signal,
      );
    }, bytes.length);
  }

  async closeDebugger(disposition: DebuggerDisposition): Promise<void> {
    this.requireActive(true);
    this.closing = true;
    await this.input.enqueue(async () => {
      this.signal.throwIfAborted();
      await this.gateway.execute(
        'session-close',
        {
          name: this.machine,
          session: this.id,
          disposition,
        },
        this.signal,
      );
    });
  }

  async resize(size: TerminalSize): Promise<void> {
    if (this.closing || this.session.exit_code !== null) {
      return;
    }
    if (
      !Number.isInteger(size.cols) ||
      !Number.isInteger(size.rows) ||
      size.cols < 1 ||
      size.cols > 1000 ||
      size.rows < 1 ||
      size.rows > 500
    ) {
      throw new Error('Invalid terminal dimensions.');
    }
    await this.input.enqueue(async () => {
      this.signal.throwIfAborted();
      await this.gateway.execute(
        'session-resize',
        {
          name: this.machine,
          session: this.id,
          ...size,
        },
        this.signal,
      );
    });
  }

  dispose(): void {
    this.closing = true;
    this.input.close();
  }

  private requireActive(debuggerCommand: boolean): void {
    if (debuggerCommand && this.session.kind !== 'debug') {
      throw new Error(
        'Select a debugger session before using debugger controls.',
      );
    }
    if (this.session.exit_code !== null || this.closing) {
      throw new Error(
        'This session has exited or is closing. Select a running session.',
      );
    }
  }
}
