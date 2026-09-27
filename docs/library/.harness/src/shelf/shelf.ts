import { button, element, search } from '../dom';
import { matchingBooks, route } from '../models';
import type { Book } from '../models';

export function shelf(books: Book[]): HTMLElement {
  const root = element('section', 'shelf');
  root.setAttribute('aria-label', 'Library');
  const toolbar = element('div', 'toolbar shelf-toolbar');
  const query = search('Search library');
  const sort = element('select');
  sort.setAttribute('aria-label', 'Sort by title');
  for (const [value, title] of [
    ['asc', 'Title: A–Z'],
    ['desc', 'Title: Z–A'],
  ]) {
    const option = element('option', '', title);
    option.value = value;
    sort.appendChild(option);
  }
  const items = element('ul', 'books');
  const status = element('p', 'shelf-status');
  status.setAttribute('role', 'status');
  let list = false;
  const gridButton = button('Grid', () => setView(false));
  const listButton = button('List', () => setView(true));

  function setView(value: boolean): void {
    list = value;
    items.className = list ? 'books list' : 'books';
    gridButton.setAttribute('aria-pressed', String(!list));
    listButton.setAttribute('aria-pressed', String(list));
  }

  function render(): void {
    items.textContent = '';
    const matches = matchingBooks(books, query.value, sort.value === 'desc');
    status.textContent =
      books.length === 0
        ? 'No captured collections. Add a collection containing capture.json to docs/library.'
        : matches.length === 0
          ? 'No books match your search.'
          : `${matches.length} ${matches.length === 1 ? 'book' : 'books'}`;
    for (const book of matches) {
      const item = element('li', 'book');
      const open = element('a', 'book-link');
      open.id = `book-${book.id}`;
      open.href = route(book);
      const cover = element('span', 'cover');
      cover.appendChild(element('span', 'cover-kicker', 'DOCUMENTATION'));
      cover.appendChild(
        element('span', 'cover-title', book.coverTitle || book.title),
      );
      cover.appendChild(
        element('span', 'cover-edition', book.edition || 'Captured edition'),
      );
      const caption = element('span', 'caption');
      caption.appendChild(element('span', 'book-title', book.title));
      caption.appendChild(
        element(
          'span',
          'book-detail',
          book.error
            ? 'Verification failed'
            : `${book.counts?.page || 0} sections · ${book.gaps || 0} recorded gaps`,
        ),
      );
      open.appendChild(cover);
      open.appendChild(caption);
      if (book.error) {
        open.removeAttribute('href');
        open.setAttribute('aria-disabled', 'true');
        item.appendChild(open);
        item.appendChild(element('p', 'error', book.error));
      } else item.appendChild(open);
      items.appendChild(item);
    }
  }

  query.addEventListener('input', render);
  sort.addEventListener('change', render);
  for (const control of [gridButton, listButton, sort, query])
    toolbar.appendChild(control);
  root.appendChild(toolbar);
  const scroll = element('div', 'shelf-scroll');
  scroll.appendChild(items);
  scroll.appendChild(status);
  root.appendChild(scroll);
  setView(false);
  render();
  return root;
}
