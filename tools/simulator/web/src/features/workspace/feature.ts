import { element } from '../../shared/ui';
import { mountSplit } from './split';
import { mountViews } from './views';

export function mountWorkspace(root: Document, signal: AbortSignal): void {
  mountSplit(root, signal);
  mountViews(root, signal);
  const workspace = element(root, 'workspace', HTMLElement);
  const terminalTools = root.querySelector('.terminal-tools');
  function updateTools(): void {
    workspace.dataset.toolsOpen = String(
      !!terminalTools?.querySelector('details[open]'),
    );
  }
  const toolsObserver = new MutationObserver(updateTools);
  if (terminalTools) {
    toolsObserver.observe(terminalTools, {
      attributes: true,
      subtree: true,
      attributeFilter: ['open'],
    });
  }
  updateTools();
  signal.addEventListener('abort', () => toolsObserver.disconnect(), {
    once: true,
  });

  const panels = root.querySelectorAll<HTMLDetailsElement>('.machine-panel');
  for (const panel of panels) {
    panel.querySelector('summary')?.addEventListener(
      'click',
      () => {
        for (const other of panels) {
          if (other !== panel) {
            other.open = false;
          }
        }
      },
      { signal },
    );
  }
  root.addEventListener(
    'pointerdown',
    (event) => {
      for (const panel of panels) {
        if (event.target instanceof Node && !panel.contains(event.target)) {
          panel.open = false;
        }
      }
    },
    { signal },
  );
  root.addEventListener(
    'keydown',
    (event) => {
      if (event.key !== 'Escape' || event.defaultPrevented) {
        return;
      }
      for (const panel of panels) {
        if (panel.open) {
          panel.open = false;
          panel.querySelector('summary')?.focus();
          event.preventDefault();
          break;
        }
      }
    },
    { signal },
  );
}
