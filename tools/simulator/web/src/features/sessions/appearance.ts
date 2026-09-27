import type { Terminal } from '@xterm/xterm';

export function observeTerminalAppearance(
  terminal: Terminal,
  root: Document,
  signal: AbortSignal,
): void {
  function update(): void {
    const container = root.getElementById('terminal');
    if (!container) {
      return;
    }
    const style = getComputedStyle(container);
    const background = style.backgroundColor;
    const foreground = style.color;
    terminal.options.theme = {
      background,
      foreground,
      cursor: foreground,
      cursorAccent: background,
      selectionBackground:
        root.documentElement.dataset.appearance === 'dark'
          ? '#34577e'
          : '#b6d7ff',
    };
  }

  update();
  const observer = new MutationObserver(update);
  observer.observe(root.documentElement, {
    attributes: true,
    attributeFilter: ['data-appearance'],
  });
  signal.addEventListener('abort', () => observer.disconnect(), { once: true });
}
