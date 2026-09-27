import { Unicode11Addon } from '@xterm/addon-unicode11';
import { ProgressAddon } from '@xterm/addon-progress';
import { SerializeAddon } from '@xterm/addon-serialize';
import type { ImageAddon } from '@xterm/addon-image';
import type { Terminal } from '@xterm/xterm';
import { bindAction, element, input, report } from '../../shared/ui';
import type { FeatureContext } from '../../shared/ui';
import { download } from '../../shared/bytes';
import { displaySnapshot } from './display-snapshot';
import type { DisplayIdentity } from './display-snapshot';
import { mountRenderer } from './renderer';

export function mountTerminalAddons(
  terminal: Terminal,
  context: FeatureContext,
  identity: () => DisplayIdentity | null,
): { reset: () => void } {
  const { root, signal, notice } = context;
  terminal.loadAddon(new Unicode11Addon());
  terminal.unicode.activeVersion = '11';
  const serializer = new SerializeAddon();
  terminal.loadAddon(serializer);
  const progress = new ProgressAddon();
  terminal.loadAddon(progress);
  const progressArea = element(root, 'terminal-progress-area', HTMLDivElement);
  const bar = element(root, 'terminal-progress', HTMLProgressElement);
  const label = element(root, 'terminal-progress-label', HTMLSpanElement);
  const progressListener = progress.onChange(({ state, value }) => {
    progressArea.hidden = state === 0;
    progressArea.dataset.state = String(state);
    if (state === 3) {
      bar.removeAttribute('value');
      label.textContent = 'Program reports work in progress';
    } else {
      bar.value = value;
      const description =
        state === 2 ? 'error' : state === 4 ? 'paused' : 'progress';
      label.textContent = `Program reports ${description}: ${value}%`;
    }
  });
  mountRenderer(terminal, context);

  let images: ImageAddon | undefined;
  let imageRevision = 0;
  const imageOption = input(root, 'terminal-images');
  const imageStatus = element(root, 'terminal-image-status', HTMLSpanElement);

  async function updateImages(): Promise<void> {
    const version = ++imageRevision;
    images?.dispose();
    images = undefined;
    imageStatus.textContent = 'Images disabled';
    if (!imageOption.checked) {
      return;
    }
    if (typeof WebAssembly === 'undefined') {
      imageOption.checked = false;
      imageStatus.textContent =
        'Inline images require WebAssembly, unavailable in this browser.';
      return;
    }
    const { ImageAddon } = await import('@xterm/addon-image');
    if (signal.aborted || version !== imageRevision) {
      return;
    }
    images = new ImageAddon({
      enableSizeReports: false,
      pixelLimit: 4_000_000,
      // The addon measures this option in decimal MB; the UI reports MiB.
      storageLimit: (32 * 1024 * 1024) / 1_000_000,
      sixelSizeLimit: 4 * 1024 * 1024,
      iipSizeLimit: 4 * 1024 * 1024,
    });
    try {
      terminal.loadAddon(images);
      imageStatus.textContent = 'Inline images enabled · 32 MiB image cache';
    } catch (error) {
      images.dispose();
      images = undefined;
      imageOption.checked = false;
      throw error;
    }
  }

  imageOption.addEventListener(
    'change',
    () => report(context, updateImages()),
    { signal },
  );
  bindAction(context, 'terminal-export', async () => {
    const selected = identity();
    if (!selected) {
      throw new Error('Choose a session before exporting its display.');
    }
    // Flush pending parsed output before capturing the display.
    await new Promise<void>((resolve) => terminal.write('', resolve));
    if (signal.aborted || identity() !== selected) {
      return;
    }
    const bytes = displaySnapshot(
      serializer,
      { cols: terminal.cols, rows: terminal.rows },
      selected,
      terminal.unicode.activeVersion,
    );
    download(bytes, `${selected.machine}-${selected.id}-terminal.json`);
    notice(
      'Terminal display exported. This file contains text and display state, not a process snapshot.',
    );
  });
  signal.addEventListener(
    'abort',
    () => {
      ++imageRevision;
      progressListener.dispose();
      images?.dispose();
      images = undefined;
    },
    { once: true },
  );

  return {
    reset() {
      progress.progress = { state: 0, value: 0 };
      images?.reset();
    },
  };
}
