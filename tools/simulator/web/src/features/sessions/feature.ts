import { Terminal } from '@xterm/xterm';
import { decode } from '../../shared/bytes';
import { bindAction, element, input, message, report } from '../../shared/ui';
import type { FeatureContext } from '../../shared/ui';
import type { DebuggerDisposition, LaunchSession, Session } from './model';
import { OutputStream } from './output-stream';
import { SessionConnection } from './connection';
import { InputQueue } from './input-queue';
import { SizeSynchronizer } from './size-synchronizer';
import { observeTerminalLayout } from './terminal-layout';
import { observeTerminalAppearance } from './appearance';
import { mountTerminalAddons } from './terminal-addons';
import type { DisplayIdentity } from './display-snapshot';

export interface SessionActions {
  launch(
    action: 'shell' | 'exec' | 'debug',
    options?: Partial<LaunchSession>,
  ): Promise<void>;
  sendDebuggerCommand(text: string): Promise<void>;
  closeDebugger(disposition: DebuggerDisposition): Promise<void>;
  selectedSession(): DisplayIdentity | null;
}

export function mountSessions(context: FeatureContext): SessionActions {
  const { root, gateway, selection, signal, notice } = context;
  const terminal = new Terminal({
    cols: 85,
    rows: 20,
    fontFamily: 'Geist Mono, monospace',
    convertEol: false,
    minimumContrastRatio: 4.5,
    scrollback: 4000,
    allowProposedApi: true,
  });
  const container = element(root, 'terminal', HTMLDivElement);
  observeTerminalAppearance(terminal, root, signal);
  terminal.open(container);
  const picker = element(root, 'sessions', HTMLSelectElement);
  const healthDisplay = element(root, 'runtime-health', HTMLElement);
  const outputStatus = element(root, 'session-status', HTMLSpanElement);
  let connection: SessionConnection | null = null;
  let sizing: SizeSynchronizer | undefined;
  let inputQueue = new InputQueue();
  let sessions: Session[] = [];
  let revision = 0;
  let launchRevision = 0;
  const addons = mountTerminalAddons(terminal, context, () => connection);
  const stream = new OutputStream(
    {
      read: (name, sessionId, cursor, requestSignal) =>
        gateway.execute(
          'session-read',
          { name, session: sessionId, cursor },
          requestSignal,
        ),
    },
    (output) => {
      connection?.update(output);
      if (output.truncated) {
        terminal.write('\r\n[earlier captured output truncated]\r\n');
      }
      terminal.write(decode(output.data));
      outputStatus.textContent =
        output.exit_code === null
          ? 'Output connected.'
          : `Session exited with code ${output.exit_code}.`;
    },
    (error) => {
      outputStatus.textContent =
        'Output disconnected. Reconnect to resume reading.';
      notice(message(error), true);
    },
  );
  observeTerminalLayout(
    terminal,
    container,
    (size) => sizing?.update(size),
    signal,
  );

  function selectSession(session: Session | null): void {
    connection?.dispose();
    sizing?.dispose();
    sizing = undefined;
    inputQueue = inputQueue.successor();
    connection = session
      ? new SessionConnection(
          selection.require(),
          session,
          gateway,
          signal,
          inputQueue,
        )
      : null;
    stream.stop();
    // Reset in the parser's write order so pending output from the previous
    // session cannot appear after a synchronous reset.
    terminal.write('\u001bc', () => addons.reset());
    picker.value = session?.id ?? '';
    outputStatus.textContent = connection
      ? 'Connecting output…'
      : 'No session selected.';
    if (connection) {
      const selected = connection;
      sizing = new SizeSynchronizer(
        (size) => selected.resize(size),
        (error) => notice(message(error), true),
      );
      sizing.update({ cols: terminal.cols, rows: terminal.rows });
      stream.follow(connection.machine, connection.id);
      terminal.focus();
    }
  }

  function requireConnection(): SessionConnection {
    if (!connection) {
      throw new Error('Choose a terminal or debugger session.');
    }
    return connection;
  }

  async function refresh(): Promise<void> {
    const name = selection.require();
    const version = ++revision;
    const result = await gateway.execute('health', { name }, signal);
    if (name !== selection.current || version !== revision || signal.aborted) {
      return;
    }
    const health = result.runtime_health;
    sessions = result.sessions;
    const active = sessions.find((item) => item.id === connection?.id);
    if (active) {
      connection?.update(active);
    } else if (connection) {
      selectSession(null);
    }
    healthDisplay.textContent = health
      ? `Darling runtime: ${health.state}. ${health.note ?? health.error ?? ''}`
      : 'Runtime health is unavailable; update the guest agent.';
    healthDisplay.classList.toggle('error', health?.state === 'server-missing');
    picker.replaceChildren(new Option('Choose session', ''));
    for (const item of result.sessions) {
      const option = new Option(
        `${item.kind} · ${item.mode} · Linux launcher PID ${item.pid} · ${item.exit_code ?? 'running'}`,
        item.id,
      );
      option.selected = item.id === connection?.id;
      picker.append(option);
    }
  }

  const actions: SessionActions = {
    selectedSession() {
      return connection;
    },
    async launch(action, options = {}) {
      const name = selection.require();
      const machineRevision = selection.revision;
      const requestRevision = ++launchRevision;
      const value = element(root, 'mode', HTMLSelectElement).value;
      if (value !== 'darwin' && value !== 'linux') {
        throw new Error('Select Darwin or Linux execution mode.');
      }
      const result = await gateway.execute(
        action,
        { ...options, name, mode: value },
        signal,
      );
      if (
        machineRevision !== selection.revision ||
        requestRevision !== launchRevision ||
        signal.aborted
      ) {
        return;
      }
      selectSession(result);
      await refresh();
      if (connection?.id !== result.id || signal.aborted) {
        return;
      }
      notice(
        gateway.transport.kind === 'demo'
          ? `Demo session ${result.id}; reloading this page resets sample sessions.`
          : `Session ${result.id} persists when this tab disconnects.`,
      );
    },
    async sendDebuggerCommand(text) {
      await requireConnection().send(text, true);
    },
    async closeDebugger(disposition) {
      await requireConnection().closeDebugger(disposition);
    },
  };

  const inputSubscription = terminal.onData((text) => {
    // Capture the connection before scheduling any asynchronous work.
    const selected = connection;
    if (selected) {
      report(context, selected.send(text));
    } else {
      notice('Choose a terminal or debugger session.', true);
    }
  });
  picker.addEventListener(
    'change',
    () => {
      ++launchRevision;
      selectSession(sessions.find((item) => item.id === picker.value) ?? null);
    },
    {
      signal,
    },
  );
  selection.subscribe(() => {
    ++revision;
    ++launchRevision;
    sessions = [];
    selectSession(null);
    picker.replaceChildren(new Option('Choose session', ''));
    healthDisplay.textContent =
      'Runtime health has not been checked. Refresh sessions to check.';
  }, signal);
  signal.addEventListener(
    'abort',
    () => {
      stream.stop();
      sizing?.dispose();
      connection?.dispose();
      inputSubscription.dispose();
      terminal.dispose();
    },
    { once: true },
  );
  bindAction(context, 'sessions-refresh', refresh);
  bindAction(context, 'session-reconnect', () => {
    requireConnection();
    stream.reconnect();
    outputStatus.textContent = 'Reconnecting output…';
  });
  bindAction(context, 'shell', () => actions.launch('shell'));
  bindAction(context, 'exec', () =>
    actions.launch('exec', {
      argv: ['/bin/bash', '-lc', input(root, 'command').value],
    }),
  );
  return actions;
}
