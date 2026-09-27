import { encode } from '../shared/bytes';

export const DEMO_OUTPUT_LIMIT = 64 * 1024;

/** Match the guest's absolute byte cursors and bounded capture semantics. */
export class DemoOutput {
  private bytes = new Uint8Array();
  private offset = 0;

  append(text: string): void {
    const incoming = new TextEncoder().encode(text);
    const total = this.bytes.length + incoming.length;
    const retained = Math.min(DEMO_OUTPUT_LIMIT, total);
    const discarded = total - retained;
    const next = new Uint8Array(retained);
    if (incoming.length >= retained) {
      next.set(incoming.subarray(incoming.length - retained));
    } else {
      const previous = this.bytes.subarray(discarded);
      next.set(previous);
      next.set(incoming, previous.length);
    }
    this.bytes = next;
    this.offset += discarded;
  }

  read(cursor: number): { data: string; cursor: number; truncated: boolean } {
    const start = Math.max(
      0,
      Math.min(this.bytes.length, cursor - this.offset),
    );
    return {
      data: encode(this.bytes.subarray(start)),
      cursor: this.offset + this.bytes.length,
      truncated: cursor < this.offset,
    };
  }
}
