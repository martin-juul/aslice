import type { TerminalSize } from './model';

/** At most one resize is in flight; intermediate sizes are replaced, not queued. */
export class SizeSynchronizer {
  private pending: TerminalSize | undefined;
  private acknowledged: TerminalSize | undefined;
  private running = false;
  private disposed = false;

  constructor(
    private readonly send: (size: TerminalSize) => Promise<void>,
    private readonly failed: (error: unknown) => void,
  ) {}

  update(size: TerminalSize): void {
    if (this.disposed) {
      return;
    }
    this.pending = { ...size };
    if (!this.running) {
      void this.flush();
    }
  }

  dispose(): void {
    this.disposed = true;
    this.pending = undefined;
  }

  private async flush(): Promise<void> {
    this.running = true;
    try {
      while (this.pending && !this.disposed) {
        const size = this.pending;
        this.pending = undefined;
        if (
          size.cols === this.acknowledged?.cols &&
          size.rows === this.acknowledged.rows
        ) {
          continue;
        }
        await this.send(size);
        this.acknowledged = size;
      }
    } catch (error) {
      this.pending = undefined;
      if (!this.disposed) {
        this.failed(error);
      }
    } finally {
      this.running = false;
    }
  }
}
