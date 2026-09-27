export function mountReader(): void {
  const search = document.getElementById('filter') as HTMLInputElement;
  if (search) {
    search.oninput = function (): void {
      const rows = document.querySelectorAll('[data-search]');
      for (let i = 0; i < rows.length; i++) {
        const row = rows[i] as HTMLElement;
        row.hidden =
          (row.textContent || '')
            .toLowerCase()
            .indexOf(search.value.toLowerCase()) < 0;
      }
    };
  }

  const frame = document.getElementById('capture') as HTMLIFrameElement;
  if (frame) {
    const initial = frame.getAttribute('src') || '';

    function navigate(): void {
      const path = location.hash.slice(1);
      // Only generated, collection-local resource names may be loaded.
      if (/^[a-f0-9]{64}\.html(?:#.*)?$/.test(path)) {
        frame.src = 'resources/' + path;
      } else {
        frame.src = initial;
      }
    }

    frame.onload = function (): void {
      try {
        const current = frame.contentWindow!.location;
        const name = current.pathname.split('/').pop() || '';
        if (/^[a-f0-9]{64}\.html$/.test(name)) {
          history.replaceState(null, '', '#' + name + current.hash);
        }
        // The viewer handles navigation; archived scripts remain disabled.
        frame.contentDocument!.addEventListener(
          'click',
          function (event): void {
            let target = event.target as HTMLElement | null;
            while (target && target.tagName.toLowerCase() !== 'a') {
              target = target.parentElement;
            }
            if (
              !target ||
              event.ctrlKey ||
              event.metaKey ||
              event.shiftKey ||
              event.altKey
            ) {
              return;
            }
            const href = target.getAttribute('href') || '';
            const route = href.charAt(0) === '#' ? name + href : href;
            if (/^[a-f0-9]{64}\.html(?:#.*)?$/.test(route)) {
              event.preventDefault();
              location.hash = route;
            }
          },
        );
      } catch (_) {}
    };
    window.addEventListener('hashchange', navigate);
    navigate();
  }
}
