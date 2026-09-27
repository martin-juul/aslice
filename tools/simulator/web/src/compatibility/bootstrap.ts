import 'core-js/actual';
import 'abortcontroller-polyfill/dist/abortcontroller-polyfill-only';
import 'whatwg-fetch';
import 'fast-text-encoding';
import './dom';
import './events';
import 'pepjs';
import ResizeObserverFallback from 'resize-observer-polyfill';

if (!window.ResizeObserver) {
  window.ResizeObserver = ResizeObserverFallback;
}

if (!AbortSignal.prototype.throwIfAborted) {
  AbortSignal.prototype.throwIfAborted = function (): void {
    if (this.aborted) {
      throw this.reason ?? new DOMException('Operation aborted', 'AbortError');
    }
  };
}

if (!crypto.randomUUID) {
  crypto.randomUUID =
    function (): `${string}-${string}-${string}-${string}-${string}` {
      const bytes = crypto.getRandomValues(new Uint8Array(16));
      bytes[6] = ((bytes[6] ?? 0) & 15) | 64;
      bytes[8] = ((bytes[8] ?? 0) & 63) | 128;
      const hex = Array.from(bytes, (byte) =>
        byte.toString(16).padStart(2, '0'),
      );
      return `${hex.slice(0, 4).join('')}-${hex.slice(4, 6).join('')}-${hex.slice(6, 8).join('')}-${hex.slice(8, 10).join('')}-${hex.slice(10).join('')}`;
    };
}
