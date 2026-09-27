import { bindAction, element, input, report } from '../../shared/ui';
import type { FeatureContext } from '../../shared/ui';
import type { SessionActions } from './feature';
import { sourceMapCommand } from './model';

export function mountDebugger(
  context: FeatureContext,
  sessions: SessionActions,
): void {
  const { root, signal, notice } = context;
  bindAction(context, 'debug', () => {
    const value = input(root, 'debug-pid').value;
    const attach = value ? Number(value) : null;
    if (attach !== null && (!Number.isSafeInteger(attach) || attach < 1)) {
      throw new Error('Debugger PID must be a positive integer.');
    }
    return sessions.launch('debug', {
      program: input(root, 'debug-program').value || null,
      attach,
    });
  });
  bindAction(context, 'debug-core', () =>
    sessions.launch('debug', { core: input(root, 'debug-program').value }),
  );
  bindAction(context, 'break', () =>
    sessions.sendDebuggerCommand(
      `breakpoint set --name ${JSON.stringify(input(root, 'breakpoint').value)}\n`,
    ),
  );
  bindAction(context, 'map', () =>
    sessions.sendDebuggerCommand(
      sourceMapCommand(input(root, 'source-map').value),
    ),
  );
  element(root, 'debug-actions', HTMLDivElement).addEventListener(
    'click',
    (event) => {
      const button =
        event.target instanceof Element ? event.target.closest('button') : null;
      if (button?.dataset.command) {
        report(
          context,
          sessions.sendDebuggerCommand(button.dataset.command + '\n'),
        );
      }
    },
    { signal },
  );
  for (const disposition of ['detach', 'terminate'] as const) {
    bindAction(context, disposition, async () => {
      await sessions.closeDebugger(disposition);
      notice(
        `${disposition === 'detach' ? 'Detach' : 'Target termination'} requested; confirm in debugger output.`,
      );
    });
  }
}
