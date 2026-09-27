import type { DemoTransport } from './demo-transport';
import type { SessionActions } from '../features/sessions/feature';
import type { FeatureContext } from '../shared/ui';
import { element, message } from '../shared/ui';
import type { TerminalSample } from './terminal-samples';

export function mountTerminalLab(
  context: FeatureContext,
  sessions: SessionActions,
  transport: DemoTransport,
): void {
  const lab = element(context.root, 'terminal-demo-lab', HTMLDetailsElement);
  lab.hidden = false;
  const controls = document.createElement('div');
  controls.className = 'toolbar';
  const samples: [TerminalSample, string][] = [
    ['unicode', 'Unicode and colors'],
    ['progress', '42% progress'],
    ['busy', 'Indeterminate'],
    ['paused', 'Paused'],
    ['error', 'Error'],
    ['clear', 'Clear progress'],
    ['image', 'Inline image'],
    ['truncated', 'Truncated output'],
    ['disconnect', 'Interrupt output'],
    ['exit', 'Exit session'],
  ];
  for (const [sample, label] of samples) {
    const button = document.createElement('button');
    button.textContent = label;
    button.dataset.sample = sample;
    button.addEventListener(
      'click',
      () => {
        try {
          const target = sessions.selectedSession();
          if (!target) {
            throw new Error(
              'Start a sample machine and open a terminal first.',
            );
          }
          transport.sampleTerminal(target.machine, target.id, sample);
          context.notice(
            `Demo terminal sample: ${label}. No guest command executed.`,
          );
        } catch (error) {
          context.notice(message(error), true);
        }
      },
      { signal: context.signal },
    );
    controls.append(button);
  }
  lab.append(controls);
}
