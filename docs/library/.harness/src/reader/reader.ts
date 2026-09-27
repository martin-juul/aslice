import { button, element, search } from '../dom';
import { information } from '../information/information';
import { route } from '../models';
import type { Book, Section } from '../models';

export function reader(
  book: Book,
  selected?: Section,
): { element: HTMLElement; dispose: () => void } {
  const root = element('section', 'reader');
  root.setAttribute('aria-label', book.title);
  const toolbar = element('div', 'toolbar');
  const back = element('a', 'control', 'Library');
  back.href = '#/';
  const body = element('div', 'reader-body');
  const contents = element('nav', 'contents');
  contents.id = 'contents';
  contents.setAttribute('aria-label', 'Captured sections');
  const narrow = window.matchMedia('(max-width: 720px)');
  contents.hidden = narrow.matches;
  const info = information(book);
  info.hidden = true;
  const contentsToggle = button('Contents', () =>
    disclose(contents, contentsToggle),
  );
  const infoToggle = button('Information', () => disclose(info, infoToggle));

  function disclose(panel: HTMLElement, toggle: HTMLButtonElement): void {
    panel.hidden = !panel.hidden;
    if (!panel.hidden && window.matchMedia('(max-width: 720px)').matches) {
      const other = panel === info ? contents : info;
      other.hidden = true;
      (panel === info ? contentsToggle : infoToggle).setAttribute(
        'aria-expanded',
        'false',
      );
    }
    toggle.setAttribute('aria-expanded', String(!panel.hidden));
  }

  contentsToggle.setAttribute('aria-controls', 'contents');
  contentsToggle.setAttribute('aria-expanded', String(!contents.hidden));
  infoToggle.setAttribute('aria-controls', 'information');
  infoToggle.setAttribute('aria-expanded', 'false');
  for (const control of [
    back,
    contentsToggle,
    element('span', 'reader-title', book.coverTitle || book.title),
    infoToggle,
  ])
    toolbar.appendChild(control);
  const filter = search('Filter contents');
  const links = element('ul', 'section-links');
  contents.appendChild(filter);
  contents.appendChild(links);

  function renderContents(): void {
    links.textContent = '';
    const matches = (book.sections || []).filter((section) =>
      `${section.title} ${section.path}`
        .toLowerCase()
        .includes(filter.value.toLowerCase()),
    );
    for (const section of matches) {
      const item = element('li');
      const link = element('a', '', section.title.split(' - ')[0]);
      link.href = route(book, section);
      link.title = section.path;
      if (section.url === selected?.url)
        link.setAttribute('aria-current', 'page');
      item.appendChild(link);
      links.appendChild(item);
    }
    if (matches.length === 0)
      links.appendChild(element('li', 'empty', 'No sections match.'));
  }

  filter.addEventListener('input', renderContents);
  renderContents();
  const frame = element('iframe', 'documentation');
  frame.title = selected?.title || book.title;
  frame.setAttribute('sandbox', 'allow-scripts allow-same-origin');
  frame.setAttribute('referrerpolicy', 'no-referrer');
  frame.src = selected?.replay || book.entry || '';
  body.appendChild(contents);
  body.appendChild(frame);
  body.appendChild(info);
  root.appendChild(toolbar);
  root.appendChild(body);
  root.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      if (!info.hidden) {
        info.hidden = true;
        infoToggle.setAttribute('aria-expanded', 'false');
        infoToggle.focus();
      } else if (!contents.hidden) {
        contents.hidden = true;
        contentsToggle.setAttribute('aria-expanded', 'false');
        contentsToggle.focus();
      }
    }
  });
  function resize(event: MediaQueryListEvent): void {
    if (event.matches) {
      contents.hidden = true;
      info.hidden = true;
      contentsToggle.setAttribute('aria-expanded', 'false');
      infoToggle.setAttribute('aria-expanded', 'false');
    }
  }

  narrow.addListener(resize);
  return { element: root, dispose: () => narrow.removeListener(resize) };
}
