import { appearance } from './appearance/appearance';
import { button, element } from './dom';
import { readRoute } from './models';
import type { Book } from './models';
import { reader } from './reader/reader';
import { shelf } from './shelf/shelf';

export async function app(root: HTMLElement): Promise<() => void> {
  root.textContent = '';
  const header = element('header', 'titlebar');
  header.appendChild(element('h1', '', 'Documentation Library'));
  header.appendChild(appearance());
  root.appendChild(header);
  const main = element('main');
  root.appendChild(main);
  main.appendChild(element('p', 'message', 'Opening library…'));
  let books: Book[];
  try {
    const response = await fetch('/api/catalog');
    if (!response.ok)
      throw new Error(`Catalog returned HTTP ${response.status}.`);
    books = (await response.json()) as Book[];
    if (!Array.isArray(books))
      throw new Error('The catalog response is invalid.');
  } catch (error) {
    main.textContent = '';
    const message = element('div', 'message');
    message.setAttribute('role', 'alert');
    message.appendChild(
      element('p', '', `Unable to open the library. ${String(error)}`),
    );
    message.appendChild(
      button('Retry', () => {
        void app(root);
      }),
    );
    main.appendChild(message);
    return () => {};
  }
  main.textContent = '';
  const library = shelf(books);
  main.appendChild(library);
  let opened: HTMLElement | null = null;
  let disposeReader: (() => void) | null = null;
  let lastBook = '';
  let scrollTop = 0;

  function navigate(): void {
    disposeReader?.();
    disposeReader = null;
    if (!library.hidden)
      scrollTop = library.querySelector('.shelf-scroll')?.scrollTop || 0;
    if (opened) main.removeChild(opened);
    opened = null;
    try {
      const target = readRoute(location.hash);
      library.hidden = !!target;
      if (!target) {
        document.title = 'Documentation Library';
        if (lastBook) document.getElementById(`book-${lastBook}`)?.focus();
        const scroll = library.querySelector('.shelf-scroll');
        if (scroll) scroll.scrollTop = scrollTop;
        return;
      }
      const book = books.find((item) => item.id === target.id);
      if (!book) throw new Error('This collection is not in the library.');
      if (book.error) throw new Error(`Verification failed: ${book.error}`);
      const selected = book.sections?.find(
        (section) => section.url === target.section,
      );
      if (target.section && !selected)
        throw new Error('This section is not captured in this collection.');
      lastBook = book.id;
      const view = reader(book, selected);
      opened = view.element;
      disposeReader = view.dispose;
      main.appendChild(opened);
      document.title = `${selected?.title || book.title} — Library`;
      (opened.querySelector('.control') as HTMLElement).focus();
    } catch (error) {
      library.hidden = true;
      opened = element('div', 'message');
      opened.setAttribute('role', 'alert');
      opened.appendChild(element('p', '', String(error)));
      const back = element('a', '', 'Return to Library');
      back.href = '#/';
      opened.appendChild(back);
      main.appendChild(opened);
    }
  }

  window.addEventListener('hashchange', navigate);
  navigate();
  return () => {
    disposeReader?.();
    window.removeEventListener('hashchange', navigate);
  };
}
