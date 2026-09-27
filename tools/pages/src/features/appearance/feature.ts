export function mountAppearance(): void {
  const toggle = document.getElementById('appearance');
  let dark = false;
  try {
    dark = localStorage.getItem('aslice.pages.appearance') === 'dark';
  } catch (_) {}

  function render(): void {
    document.documentElement.className = dark ? 'dark' : '';
    if (toggle) {
      toggle.setAttribute('aria-pressed', String(dark));
    }
  }

  render();
  if (toggle) {
    toggle.onclick = function (): void {
      dark = !dark;
      render();
      try {
        localStorage.setItem(
          'aslice.pages.appearance',
          dark ? 'dark' : 'light',
        );
      } catch (_) {}
    };
  }
}
