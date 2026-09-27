const PENDING_INPUT_LIMIT = 1024 * 1024;

/** Preserve input order without retrying writes whose guest effect is uncertain. */
export class InputQueue {
  private tail: Promise<void>;
  private pendingBytes = 0;
  private closed = false;
  private failed = false;

  constructor(after: Promise<void> = Promise.resolve()) {
    this.tail = after;
  }

  successor(): InputQueue {
    this.close();
    return new InputQueue(this.tail);
  }

  enqueue(operation: () => Promise<void>, bytes = 0): Promise<void> {
    if (this.pendingBytes + bytes > PENDING_INPUT_LIMIT) {
      return Promise.reject(
        new Error(
          'Terminal input queue is full. Wait for pending input before typing again.',
        ),
      );
    }
    this.pendingBytes += bytes;
    const result = this.tail.then(async () => {
      if (this.closed) {
        throw new Error(
          'Session selection changed; unsent input was discarded.',
        );
      }
      if (this.failed) {
        throw new Error(
          'Input delivery is uncertain. Inspect the terminal and reselect the session to resume; input was not retried.',
        );
      }
      await operation();
    });
    this.tail = result.then(
      () => {
        this.pendingBytes -= bytes;
      },
      () => {
        this.pendingBytes -= bytes;
        this.failed = true;
      },
    );
    return result;
  }

  close(): void {
    this.closed = true;
  }
}
