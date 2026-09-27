import './compatibility/bootstrap';
import '@xterm/xterm/css/xterm.css';
import '@fontsource/geist/latin-400.css';
import '@fontsource/geist/latin-600.css';
import '@fontsource/geist-mono/latin-400.css';
import '@fontsource/space-grotesk/latin-600.css';
import './styles/main.scss';
import { MachineSelection } from './features/machines/model';
import { mountMachines } from './features/machines/feature';
import { mountSessions } from './features/sessions/feature';
import { mountDebugger } from './features/sessions/debugger';
import { mountDisplay } from './features/display/feature';
import { mountInspection } from './features/inspection/feature';
import { mountTransfers } from './features/transfers/feature';
import { mountDiagnostics } from './features/diagnostics/feature';
import { mountConsole } from './features/console/feature';
import { mountWorkspace } from './features/workspace/feature';
import { mountAppearance } from './features/appearance/feature';
import { Gateway } from './shared/protocol';
import { HttpTransport } from './shared/http-transport';
import { element, message } from './shared/ui';
import type { FeatureContext } from './shared/ui';

// The composition root becomes app.js. Features own behavior and local state.
const lifetime = new AbortController();
mountAppearance(document, lifetime.signal);
mountWorkspace(document, lifetime.signal);
const status = element(document, 'notice', HTMLDivElement);
const notice = (text: string, error = false): void => {
  status.textContent = text;
  status.classList.toggle('error', error);
};

async function start(): Promise<void> {
  try {
    const transport =
      import.meta.env.MODE === 'demo'
        ? new (await import('./development/demo-transport')).DemoTransport()
        : new HttpTransport();
    const token = location.hash.slice(1);
    history.replaceState(null, '', location.pathname + location.search);
    if (transport.kind === 'demo') {
      element(document, 'development-banner', HTMLDivElement).hidden = false;
    }
    await transport.authenticate(token);
    const context: FeatureContext = {
      root: document,
      gateway: new Gateway(transport),
      selection: new MachineSelection(),
      signal: lifetime.signal,
      notice,
    };
    const machines = mountMachines(context);
    const sessions = mountSessions(context);
    if (import.meta.env.MODE === 'demo' && transport.kind === 'demo') {
      const { mountTerminalLab } = await import('./development/terminal-lab');
      mountTerminalLab(context, sessions, transport);
    }
    mountDebugger(context, sessions);
    mountDisplay(context);
    mountInspection(context);
    mountTransfers(context);
    mountDiagnostics(context);
    mountConsole(context);
    await machines.refresh();
    notice(
      transport.kind === 'demo'
        ? 'Demo UI ready. Sample machines and operations stay in this browser; no simulator is connected.'
        : 'Connected to the local controller. Pending compatibility gates remain visible.',
    );
  } catch (error) {
    notice(
      `${message(error)} For live mode, open the authenticated console URL or configure the Vite controller proxy.`,
      true,
    );
  }
}

void start();

window.addEventListener('pagehide', () => lifetime.abort(), { once: true });
import.meta.hot?.dispose(() => lifetime.abort());
