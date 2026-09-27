import { bindAction, element, message } from '../../shared/ui';
import type { FeatureContext } from '../../shared/ui';
import { filterLogs } from './model';
import type { LogRecord } from './model';

export function mountConsole(context: FeatureContext): void {
  const { root, gateway, selection, signal } = context;
  const pane = element(root, 'console-panel', HTMLDetailsElement);
  const source = element(root, 'console-source', HTMLSelectElement);
  const search = element(root, 'console-search', HTMLInputElement);
  const severity = element(root, 'console-type', HTMLSelectElement);
  const body = element(root, 'console-messages', HTMLTableSectionElement);
  const detail = element(root, 'console-detail', HTMLPreElement);
  const status = element(root, 'console-status', HTMLDivElement);
  const pause = element(root, 'console-pause', HTMLButtonElement);
  const count = element(root, 'console-count', HTMLSpanElement);
  let rows: LogRecord[] = [];
  let hidden = new Set<string>();
  let paused = false;
  let busy = false;
  let revision = 0;

  function render(): void {
    const visible = filterLogs(
      rows.filter((row) => !hidden.has(row.id)),
      search.value,
      severity.value,
    );
    body.replaceChildren();
    count.textContent = `${visible.length} of ${rows.length} messages`;
    for (const record of visible) {
      const row = document.createElement('tr');
      row.tabIndex = 0;
      row.className = `log-${record.type === 'error' || record.type === 'fault' ? 'error' : 'normal'}`;
      for (const value of [
        record.type,
        record.time,
        record.process,
        record.message,
      ]) {
        const cell = document.createElement('td');
        cell.textContent = value;
        row.append(cell);
      }
      const select = (): void => {
        for (const previous of Array.from(body.children)) {
          previous.removeAttribute('aria-selected');
        }
        row.setAttribute('aria-selected', 'true');
        detail.textContent = `Process: ${record.process}  PID: ${record.pid}\nSubsystem: ${record.subsystem}  Category: ${record.category}\n${record.message}\n\n${record.raw}`;
      };
      row.addEventListener('click', select);
      row.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          select();
        } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
          event.preventDefault();
          const sibling =
            event.key === 'ArrowDown'
              ? row.nextElementSibling
              : row.previousElementSibling;
          if (sibling instanceof HTMLElement) {
            sibling.focus();
          }
        }
      });
      body.append(row);
    }
  }

  async function refresh(): Promise<void> {
    if (busy || !selection.current) {
      return;
    }
    busy = true;
    const version = revision;
    try {
      const result = await gateway.execute(
        'logs',
        { name: selection.require(), source: source.value },
        signal,
      );
      if (version !== revision || signal.aborted) {
        return;
      }
      rows = result.records;
      status.textContent = `${result.available ? '' : 'Unavailable: '}${result.note}${result.truncated ? ' Showing the latest 500 records.' : ''}`;
      render();
    } catch (error) {
      if (version === revision && !signal.aborted) {
        rows = [];
        render();
        status.textContent = `Log source unavailable: ${message(error)}. An older guest agent may need updating.`;
      }
    } finally {
      busy = false;
    }
  }

  function reset(): void {
    revision += 1;
    rows = [];
    hidden.clear();
    detail.textContent = '';
    status.textContent =
      'Select a source and refresh. Guest logs are read-only.';
    render();
  }
  bindAction(context, 'console-refresh', refresh);
  bindAction(context, 'console-pause', () => {
    paused = !paused;
    if (paused) {
      revision += 1;
    }
    pause.textContent = paused ? 'Resume' : 'Pause';
    pause.setAttribute('aria-pressed', String(paused));
  });
  bindAction(context, 'console-clear', () => {
    hidden = new Set(rows.map((row) => row.id));
    detail.textContent = '';
    render();
  });
  source.addEventListener(
    'change',
    () => {
      reset();
      void refresh();
    },
    { signal },
  );
  search.addEventListener('input', render, { signal });
  severity.addEventListener('change', render, { signal });
  pane.addEventListener(
    'toggle',
    () => {
      if (pane.open) {
        void refresh();
      }
    },
    { signal },
  );
  selection.subscribe(reset, signal);
  const timer = setInterval(() => {
    if (pane.open && !paused && !body.contains(root.activeElement)) {
      void refresh();
    }
  }, 3000);
  signal.addEventListener('abort', () => clearInterval(timer), { once: true });
  root.addEventListener(
    'keydown',
    (event) => {
      if (
        pane.open &&
        (event.ctrlKey || event.metaKey) &&
        event.key.toLowerCase() === 'f' &&
        pane.contains(root.activeElement)
      ) {
        event.preventDefault();
        search.focus();
      }
    },
    { signal },
  );
  reset();
}
