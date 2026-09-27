import { FitAddon } from '@xterm/addon-fit';
import type { Terminal } from '@xterm/xterm';
import type { TerminalSize } from './model';

export function observeTerminalLayout(
  terminal: Terminal,
  container: HTMLElement,
  changed: (size: TerminalSize) => void,
  signal: AbortSignal,
): void {
  const fit = new FitAddon();
  terminal.loadAddon(fit);
  let frame: number | undefined;

  function measure(): void {
    frame = undefined;
    if (signal.aborted || !container.clientWidth || !container.clientHeight) {
      return;
    }
    const size = fit.proposeDimensions();
    if (size && Number.isFinite(size.cols) && Number.isFinite(size.rows)) {
      terminal.resize(Math.min(1000, size.cols), Math.min(500, size.rows));
    }
  }

  function schedule(): void {
    if (!signal.aborted && frame === undefined) {
      frame = requestAnimationFrame(measure);
    }
  }

  const subscription = terminal.onResize(changed);
  const observer = new ResizeObserver(schedule);
  observer.observe(container);
  document.fonts?.addEventListener('loadingdone', schedule, { signal });
  // Static WOFF faces can finish loading after the first measurement on Safari 9.
  window.addEventListener('load', schedule, { signal });
  schedule();
  signal.addEventListener(
    'abort',
    () => {
      observer.disconnect();
      subscription.dispose();
      if (frame !== undefined) {
        cancelAnimationFrame(frame);
      }
    },
    { once: true },
  );
}
