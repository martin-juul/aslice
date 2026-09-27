export interface Section {
  title: string;
  path: string;
  url: string;
  replay: string;
}

export interface Book {
  id: string;
  title: string;
  error: string | null;
  coverTitle?: string;
  edition?: string;
  origin?: string;
  entry?: string;
  entry_url?: string;
  sections?: Section[];
  counts?: Record<string, number>;
  gaps?: number;
}

export function matchingBooks(
  books: Book[],
  query: string,
  descending: boolean,
): Book[] {
  const needle = query.trim().toLowerCase();
  return books
    .filter((book) =>
      [
        book.title,
        book.edition || '',
        ...(book.sections || []).map(
          (section) => `${section.title} ${section.path}`,
        ),
      ]
        .join(' ')
        .toLowerCase()
        .includes(needle),
    )
    .sort((a, b) => a.title.localeCompare(b.title) * (descending ? -1 : 1));
}

export function route(book: Book, section?: Section): string {
  return `#/book/${encodeURIComponent(book.id)}${section ? `/${encodeURIComponent(section.url)}` : ''}`;
}

export function readRoute(
  hash: string,
): { id: string; section?: string } | null {
  if (!hash || hash === '#/' || hash === '#') return null;
  const match = /^#\/book\/([^/]+)(?:\/(.+))?$/.exec(hash);
  if (!match) throw new Error('This library address is not recognized.');
  try {
    return {
      id: decodeURIComponent(match[1]),
      section: match[2] ? decodeURIComponent(match[2]) : undefined,
    };
  } catch {
    throw new Error('This library address is not valid.');
  }
}
