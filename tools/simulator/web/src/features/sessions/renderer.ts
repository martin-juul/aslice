import type { Terminal } from '@xterm/xterm';
import type { WebglAddon } from '@xterm/addon-webgl';
import { input, element, report } from '../../shared/ui';
import type { FeatureContext } from '../../shared/ui';

export function mountRenderer(
  terminal: Terminal,
  context: FeatureContext,
): void {
  const option = input(context.root, 'terminal-webgl');
  const status = element(context.root, 'terminal-renderer', HTMLSpanElement);
  let renderer: WebglAddon | undefined;
  let revision = 0;

  function fallback(reason: string): void {
    renderer?.dispose();
    renderer = undefined;
    status.textContent = `Standard renderer${reason ? ` · ${reason}` : ''}`;
  }

  async function update(): Promise<void> {
    const version = ++revision;
    fallback('');
    if (!option.checked || context.signal.aborted) {
      return;
    }
    try {
      const { WebglAddon } = await import('@xterm/addon-webgl');
      if (version !== revision || context.signal.aborted) {
        return;
      }
      const addon = new WebglAddon();
      renderer = addon;
      addon.onContextLoss(() => {
        if (renderer === addon) {
          fallback('GPU context lost');
        }
      });
      terminal.loadAddon(addon);
      status.textContent = 'WebGL renderer';
    } catch {
      if (version === revision && !context.signal.aborted) {
        fallback('WebGL unavailable');
      }
    }
  }

  option.addEventListener('change', () => report(context, update()), {
    signal: context.signal,
  });
  context.signal.addEventListener(
    'abort',
    () => {
      ++revision;
      fallback('');
    },
    { once: true },
  );
  report(context, update());
}
