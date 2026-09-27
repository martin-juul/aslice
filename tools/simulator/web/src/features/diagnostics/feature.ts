import { decode, download } from '../../shared/bytes';
import { bindAction, element, input } from '../../shared/ui';
import type { FeatureContext } from '../../shared/ui';

export function mountDiagnostics(context: FeatureContext): void {
  const { root, gateway, selection, signal } = context;
  let revision = 0;
  bindAction(context, 'timeline-refresh', async () => {
    const name = selection.require();
    const version = ++revision;
    const result = await gateway.execute(
      'timeline',
      { name, query: input(root, 'search').value },
      signal,
    );
    if (name === selection.current && version === revision && !signal.aborted) {
      element(root, 'timeline', HTMLPreElement).textContent = JSON.stringify(
        result.events,
        null,
        2,
      );
    }
  });
  selection.subscribe(() => {
    ++revision;
    element(root, 'timeline', HTMLPreElement).textContent = '';
  }, signal);
  bindAction(context, 'diagnostics', async () => {
    const name = selection.require();
    const result = await gateway.execute('diagnostics', { name }, signal);
    download(decode(result.archive), `${name}-diagnostics.zip`);
  });
}
