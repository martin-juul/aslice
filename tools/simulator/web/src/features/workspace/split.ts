import { element } from '../../shared/ui';

const preferenceKey = 'aslice.workspace.split.v1';
const minimum = 30;
const maximum = 70;
const defaultShare = 50;

function readPreference(): number {
  try {
    const saved = localStorage.getItem(preferenceKey);
    const value = saved === null ? defaultShare : Number(saved);
    return Number.isFinite(value) && value >= minimum && value <= maximum
      ? value
      : defaultShare;
  } catch {
    // Browser privacy settings can disable storage; resizing still works.
    return defaultShare;
  }
}

function savePreference(value: number): void {
  try {
    localStorage.setItem(preferenceKey, String(value));
  } catch {
    // A layout preference must never prevent use of the console.
  }
}

export function mountSplit(root: Document, signal: AbortSignal): void {
  const panels = element(root, 'primary-panels', HTMLDivElement);
  const divider = element(root, 'workspace-divider', HTMLDivElement);
  const terminal = element(root, 'terminal-panel', HTMLElement);
  const display = element(root, 'display-panel', HTMLElement);
  let share = readPreference();
  let drag: { pointer: number; previousShare: number } | undefined;

  function render(value: number): void {
    share = Math.min(maximum, Math.max(minimum, Math.round(value)));
    terminal.style.flexGrow = String(share);
    display.style.flexGrow = String(100 - share);
    divider.setAttribute('aria-valuenow', String(share));
    divider.setAttribute(
      'aria-valuetext',
      `Terminal ${share}%, application display ${100 - share}%`,
    );
  }

  function finishDrag(commit: boolean): void {
    if (!drag) {
      return;
    }
    const previous = drag;
    drag = undefined;
    panels.classList.remove('resizing');
    if (commit) {
      savePreference(share);
    } else {
      render(previous.previousShare);
    }
    if (divider.hasPointerCapture(previous.pointer)) {
      divider.releasePointerCapture(previous.pointer);
    }
  }

  render(share);
  divider.addEventListener(
    'pointerdown',
    (event) => {
      if (event.button !== 0 || !event.isPrimary || drag) {
        return;
      }
      drag = { pointer: event.pointerId, previousShare: share };
      divider.setPointerCapture(event.pointerId);
      divider.focus();
      panels.classList.add('resizing');
      event.preventDefault();
    },
    { signal },
  );
  divider.addEventListener(
    'pointermove',
    (event) => {
      if (drag?.pointer !== event.pointerId) {
        return;
      }
      const bounds = panels.getBoundingClientRect();
      const dividerWidth = divider.getBoundingClientRect().width;
      if (!dividerWidth || bounds.width <= dividerWidth) {
        finishDrag(false);
        return;
      }
      const position = event.clientX - bounds.left - dividerWidth / 2;
      render((position / (bounds.width - dividerWidth)) * 100);
    },
    { signal },
  );
  divider.addEventListener(
    'pointerup',
    (event) => {
      if (drag?.pointer === event.pointerId) {
        finishDrag(true);
      }
    },
    { signal },
  );
  divider.addEventListener('pointercancel', () => finishDrag(false), {
    signal,
  });
  divider.addEventListener('lostpointercapture', () => finishDrag(false), {
    signal,
  });
  divider.addEventListener(
    'keydown',
    (event) => {
      if (event.key === 'Escape' && drag) {
        finishDrag(false);
      } else if (!drag) {
        const step = event.shiftKey ? 5 : 1;
        switch (event.key) {
          case 'ArrowLeft':
            render(share - step);
            break;
          case 'ArrowRight':
            render(share + step);
            break;
          case 'Home':
            render(minimum);
            break;
          case 'End':
            render(maximum);
            break;
          case 'Enter':
            render(defaultShare);
            break;
          default:
            return;
        }
        savePreference(share);
      } else {
        return;
      }
      event.preventDefault();
    },
    { signal },
  );
  signal.addEventListener('abort', () => finishDrag(false), { once: true });
}
