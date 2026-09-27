import { element } from '../../shared/ui';

type WorkspaceView = 'split' | 'terminal' | 'display';

const preferenceKey = 'aslice.workspace.view.v1';
const views: readonly WorkspaceView[] = ['split', 'terminal', 'display'];

function savedView(): WorkspaceView {
  try {
    const saved = localStorage.getItem(preferenceKey);
    return views.find((view) => view === saved) ?? 'split';
  } catch {
    return 'split';
  }
}

export function mountViews(root: Document, signal: AbortSignal): void {
  const workspace = element(root, 'workspace', HTMLElement);
  const terminal = element(root, 'terminal-panel', HTMLElement);
  const display = element(root, 'display-panel', HTMLElement);
  const buttons = views.map((view) =>
    element(root, `view-${view}`, HTMLButtonElement),
  );

  // Keep sessions and guest display connections mounted when their pane is hidden.
  function select(view: WorkspaceView, save = true): void {
    workspace.dataset.view = view;
    terminal.hidden = view === 'display';
    display.hidden = view === 'terminal';
    for (const [index, button] of buttons.entries()) {
      const selected = views[index] === view;
      button.setAttribute('aria-pressed', String(selected));
      button.tabIndex = selected ? 0 : -1;
    }
    if (save) {
      try {
        localStorage.setItem(preferenceKey, view);
      } catch {
        // Storage restrictions must not prevent changing the workspace.
      }
    }
  }

  for (const [index, button] of buttons.entries()) {
    button.addEventListener('click', () => select(views[index]!), { signal });
    button.addEventListener(
      'keydown',
      (event) => {
        if (event.altKey || event.ctrlKey || event.metaKey) {
          return;
        }
        let next: number;
        switch (event.key) {
          case 'ArrowRight':
            next = (index + 1) % views.length;
            break;
          case 'ArrowLeft':
            next = (index + views.length - 1) % views.length;
            break;
          case 'Home':
            next = 0;
            break;
          case 'End':
            next = views.length - 1;
            break;
          default:
            return;
        }
        event.preventDefault();
        select(views[next]!);
        buttons[next]!.focus();
      },
      { signal },
    );
  }
  select(savedView(), false);
}
