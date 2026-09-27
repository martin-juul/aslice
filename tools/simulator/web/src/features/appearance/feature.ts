import { element } from '../../shared/ui';

const preferenceKey = 'aslice.appearance.v1';

export function mountAppearance(root: Document, signal: AbortSignal): void {
  const toggle = element(root, 'dark-appearance', HTMLButtonElement);
  let dark = false;
  try {
    dark = localStorage.getItem(preferenceKey) === 'dark';
  } catch {
    // Storage may be unavailable. Light remains the default.
  }

  function render(): void {
    root.documentElement.dataset.appearance = dark ? 'dark' : 'light';
    toggle.setAttribute('aria-pressed', String(dark));
  }

  render();
  toggle.addEventListener(
    'click',
    () => {
      dark = !dark;
      render();
      try {
        localStorage.setItem(preferenceKey, dark ? 'dark' : 'light');
      } catch {
        // Appearance changes still work without persistent storage.
      }
    },
    { signal },
  );
}
