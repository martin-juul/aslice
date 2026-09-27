// @vitest-environment jsdom
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { mountViews } from './views';

let lifetime: AbortController;

beforeEach(() => {
  localStorage.clear();
  document.body.innerHTML = `
    <section id="workspace">
      <button id="view-split">Split</button>
      <button id="view-terminal">Terminal</button>
      <button id="view-display">Display</button>
      <article id="terminal-panel"><input value="guest state"></article>
      <article id="display-panel"></article>
    </section>`;
  lifetime = new AbortController();
});

afterEach(() => {
  lifetime.abort();
  vi.restoreAllMocks();
});

function button(view: string): HTMLButtonElement {
  const result = document.getElementById(`view-${view}`);
  if (!(result instanceof HTMLButtonElement)) {
    throw new Error(`Missing view fixture: ${view}`);
  }
  return result;
}

function press(view: string, key: string): void {
  button(view).dispatchEvent(
    new KeyboardEvent('keydown', { key, bubbles: true }),
  );
}

test('keyboard selection wraps, moves focus, and preserves mounted content', () => {
  const guestInput = document.querySelector('input');
  mountViews(document, lifetime.signal);
  press('split', 'ArrowLeft');
  expect(document.activeElement).toBe(button('display'));
  expect(document.getElementById('terminal-panel')?.hidden).toBe(true);
  expect(button('display').getAttribute('aria-pressed')).toBe('true');
  expect(button('split').tabIndex).toBe(-1);
  press('display', 'Home');
  press('split', 'ArrowRight');
  expect(document.activeElement).toBe(button('terminal'));
  expect(document.getElementById('display-panel')?.hidden).toBe(true);
  press('terminal', 'End');
  expect(document.activeElement).toBe(button('display'));
  expect(document.querySelector('input')).toBe(guestInput);
  expect(guestInput?.value).toBe('guest state');
  expect(localStorage.getItem('aslice.workspace.view.v1')).toBe('display');
});

test('restores a saved view and releases listeners on teardown', () => {
  localStorage.setItem('aslice.workspace.view.v1', 'terminal');
  mountViews(document, lifetime.signal);
  expect(button('terminal').tabIndex).toBe(0);
  expect(document.getElementById('display-panel')?.hidden).toBe(true);
  lifetime.abort();
  button('display').click();
  expect(document.getElementById('workspace')?.dataset.view).toBe('terminal');
});

test('invalid or unavailable preferences do not prevent view switching', () => {
  localStorage.setItem('aslice.workspace.view.v1', 'invalid');
  mountViews(document, lifetime.signal);
  expect(button('split').getAttribute('aria-pressed')).toBe('true');
  lifetime.abort();
  lifetime = new AbortController();
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
    throw new Error('Storage disabled');
  });
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('Storage disabled');
  });
  mountViews(document, lifetime.signal);
  button('display').click();
  expect(document.getElementById('workspace')?.dataset.view).toBe('display');
});
