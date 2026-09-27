import { button } from '../dom';

export function appearance(): HTMLButtonElement {
  let dark = false;
  try {
    dark = localStorage.getItem('library-appearance') === 'dark';
  } catch {
    /* Storage is optional. */
  }
  const toggle = button('Dark appearance', () => {
    dark = !dark;
    try {
      localStorage.setItem('library-appearance', dark ? 'dark' : 'light');
    } catch {
      /* Keep the session choice. */
    }
    update();
  });

  function update(): void {
    document.documentElement.className = dark ? 'dark' : 'light';
    toggle.setAttribute('aria-pressed', String(dark));
  }

  update();
  return toggle;
}
