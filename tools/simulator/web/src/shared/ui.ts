import type { MachineSelection } from '../features/machines/model';
import type { Gateway } from './protocol';

export interface FeatureContext {
  readonly root: Document;
  readonly gateway: Gateway;
  readonly selection: MachineSelection;
  readonly signal: AbortSignal;
  readonly notice: (text: string, error?: boolean) => void;
}

export function element<T extends HTMLElement>(
  root: Document,
  id: string,
  constructor: new () => T,
): T {
  const found = root.getElementById(id);
  if (!(found instanceof constructor)) {
    throw new Error(`Missing or invalid console element: ${id}`);
  }
  return found;
}

export function input(root: Document, id: string): HTMLInputElement {
  return element(root, id, HTMLInputElement);
}

export function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function report(context: FeatureContext, task: Promise<unknown>): void {
  void task.catch((error: unknown) => {
    if (!context.signal.aborted) {
      context.notice(message(error), true);
    }
  });
}

export function bindAction(
  context: FeatureContext,
  id: string,
  action: () => Promise<unknown> | void,
  available: () => boolean = () => true,
): () => void {
  const button = element(context.root, id, HTMLButtonElement);
  let pending = false;

  function refresh(): void {
    button.disabled = pending || !available();
  }

  refresh();
  button.addEventListener(
    'click',
    () => {
      if (pending || !available()) {
        return;
      }
      pending = true;
      refresh();
      report(
        context,
        Promise.resolve()
          .then(() => {
            if (available()) {
              return action();
            }
          })
          .finally(() => {
            pending = false;
            refresh();
          }),
      );
    },
    { signal: context.signal },
  );
  return refresh;
}
