import type RFB from '@novnc/novnc';
import { bindAction, element } from '../../shared/ui';
import type { FeatureContext } from '../../shared/ui';

export function mountDisplay(context: FeatureContext): void {
  const { root, selection, signal, gateway } = context;
  const container = element(root, 'display', HTMLDivElement);
  const status = element(root, 'display-status', HTMLSpanElement);
  const frame = element(root, 'display-frame', HTMLDivElement);
  const frameToggle = element(root, 'display-frame-toggle', HTMLButtonElement);
  let framed = true;
  try {
    framed = localStorage.getItem('aslice-display-frame') !== 'off';
  } catch {
    // Storage may be unavailable in a restricted browser profile.
  }
  function showFrame(): void {
    frame.classList.toggle('unframed', !framed);
    frameToggle.setAttribute('aria-pressed', String(framed));
  }
  showFrame();
  bindAction(context, 'display-frame-toggle', () => {
    framed = !framed;
    showFrame();
    try {
      localStorage.setItem('aslice-display-frame', framed ? 'on' : 'off');
    } catch {
      // The current window still retains the selected presentation.
    }
  });
  let connection: RFB | undefined;
  let revision = 0;

  function disconnect(): void {
    revision += 1;
    const previous = connection;
    connection = undefined;
    previous?.disconnect();
    container.replaceChildren();
    status.textContent = 'Disconnected';
  }

  bindAction(context, 'display-connect', async () => {
    const machine = selection.require();
    disconnect();
    if (gateway.transport.kind === 'demo') {
      status.textContent = 'Demo display · no guest connection';
      const window = document.createElement('section');
      window.className = 'demo-window';
      const heading = document.createElement('h3');
      heading.textContent = 'Sample application · UI preview only';
      const field = document.createElement('input');
      field.setAttribute('aria-label', 'Demo application input');
      field.value = 'Edit this sample text';
      const button = document.createElement('button');
      button.textContent = 'Apply';
      const result = document.createElement('output');
      button.addEventListener('click', () => {
        result.textContent = field.value;
      });
      window.append(heading, field, button, result);
      container.append(window);
      return;
    }
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const requestRevision = revision;
    const { default: RemoteDisplay } = await import('@novnc/novnc');
    if (signal.aborted || requestRevision !== revision) {
      return;
    }
    const current = new RemoteDisplay(
      container,
      `${protocol}//${location.host}/v1/vnc/${encodeURIComponent(machine)}`,
    );
    connection = current;
    current.scaleViewport = true;
    current.resizeSession = false;
    current.addEventListener('connect', () => {
      if (connection === current) {
        status.textContent = 'Connected · guest X11';
      }
    });
    current.addEventListener('disconnect', () => {
      if (connection === current) {
        status.textContent = 'Disconnected';
      }
    });
  });
  bindAction(context, 'display-disconnect', disconnect);
  selection.subscribe(disconnect, signal);
  signal.addEventListener('abort', disconnect, { once: true });
}
