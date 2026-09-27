import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { app } from './app';
import { matchingBooks, readRoute, route } from './models';
import type { Book } from './models';

const books: Book[] = [
  {
    id: 'alpha',
    title: 'Alpha guide',
    error: null,
    edition: '2018',
    entry: 'http://127.0.0.1:9901/start/',
    origin: 'http://127.0.0.1:9901',
    sections: [
      {
        title: 'Windows',
        path: '/windows/',
        url: 'https://example.test/windows/',
        replay: 'http://127.0.0.1:9901/windows/',
      },
    ],
  },
  { id: 'broken', title: 'Broken guide', error: 'Checksum mismatch' },
  { id: 'zeta', title: 'Zeta guide', error: null, sections: [] },
];
let cleanup: () => void;

beforeEach(() => {
  history.replaceState(null, '', '/');
  localStorage.clear();
  document.body.innerHTML = '<div id="app"></div>';
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({
      matches: false,
      addListener: vi.fn(),
      removeListener: vi.fn(),
    })),
  );
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({ ok: true, json: async () => books })),
  );
});

afterEach(() => {
  cleanup?.();
  vi.unstubAllGlobals();
});

async function mount(): Promise<void> {
  cleanup = await app(document.getElementById('app')!);
}

function navigate(hash: string): void {
  history.replaceState(null, '', hash);
  window.dispatchEvent(new HashChangeEvent('hashchange'));
}

describe('library', () => {
  it('searches metadata and section paths, and sorts titles', () => {
    expect(matchingBooks(books, '2018', false).map((book) => book.id)).toEqual([
      'alpha',
    ]);
    expect(
      matchingBooks(books, '/windows', false).map((book) => book.id),
    ).toEqual(['alpha']);
    expect(matchingBooks(books, '', true)[0].id).toBe('zeta');
  });

  it('roundtrips bookmark routes and rejects malformed routes', () => {
    expect(readRoute(route(books[0], books[0].sections![0]))).toEqual({
      id: 'alpha',
      section: 'https://example.test/windows/',
    });
    expect(readRoute('#/')).toBeNull();
    expect(() => readRoute('#/wrong')).toThrow();
    expect(() => readRoute('#/book/%zz')).toThrow();
  });

  it('shows search empty states, view controls and failed verification', async () => {
    await mount();
    expect(document.querySelector('#book-broken')?.hasAttribute('href')).toBe(
      false,
    );
    const input = document.querySelector('input')!;
    input.value = 'nothing';
    input.dispatchEvent(new Event('input'));
    expect(document.querySelector('[role=status]')?.textContent).toBe(
      'No books match your search.',
    );
    Array.from(document.querySelectorAll('button'))
      .find((button) => button.textContent === 'List')!
      .click();
    expect(document.querySelector('.books')?.className).toContain('list');
  });

  it('opens bookmarks, discloses information, handles Escape and restores shelf focus and scroll', async () => {
    await mount();
    const scroll = document.querySelector('.shelf-scroll')!;
    scroll.scrollTop = 180;
    navigate(route(books[0], books[0].sections![0]));
    expect(document.querySelector('iframe')?.src).toBe(
      books[0].sections![0].replay,
    );
    expect(document.querySelector('iframe')?.getAttribute('sandbox')).toBe(
      'allow-scripts allow-same-origin',
    );
    const info = document.querySelector(
      '[aria-controls=information]',
    ) as HTMLButtonElement;
    info.click();
    expect(document.getElementById('information')?.hidden).toBe(false);
    info.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }),
    );
    expect(info.getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement).toBe(info);
    navigate('#/');
    expect(document.activeElement?.id).toBe('book-alpha');
    expect(scroll.scrollTop).toBe(180);
  });

  it('defaults to light and persists explicit dark appearance without changing iframe source', async () => {
    await mount();
    expect(document.documentElement.className).toBe('light');
    navigate(route(books[0]));
    const frame = document.querySelector('iframe');
    (document.querySelector('.titlebar button') as HTMLButtonElement).click();
    expect(localStorage.getItem('library-appearance')).toBe('dark');
    expect(document.querySelector('iframe')).toBe(frame);
    cleanup();
    await mount();
    expect(document.documentElement.className).toBe('dark');
  });

  it('collapses contents at narrow widths and filters sections', async () => {
    vi.stubGlobal('matchMedia', () => ({
      matches: true,
      addListener: vi.fn(),
      removeListener: vi.fn(),
    }));
    await mount();
    navigate(route(books[0]));
    expect(document.getElementById('contents')?.hidden).toBe(true);
    (
      document.querySelector('[aria-controls=contents]') as HTMLButtonElement
    ).click();
    const input = document.querySelector('.contents input') as HTMLInputElement;
    input.value = 'missing';
    input.dispatchEvent(new Event('input'));
    expect(document.querySelector('.section-links')?.textContent).toBe(
      'No sections match.',
    );
  });

  it('reports missing collections, missing sections and blocked books', async () => {
    await mount();
    for (const address of [
      '#/book/absent',
      '#/book/broken',
      '#/book/alpha/missing',
    ]) {
      navigate(address);
      expect(document.querySelector('[role=alert]')).not.toBeNull();
      expect(document.querySelector('iframe')).toBeNull();
    }
  });

  it('shows an empty library and recoverable backend failures', async () => {
    vi.stubGlobal('fetch', async () => ({ ok: true, json: async () => [] }));
    await mount();
    expect(document.querySelector('[role=status]')?.textContent).toContain(
      'No captured collections',
    );
    cleanup();
    vi.stubGlobal('fetch', async () => {
      throw new Error('offline');
    });
    await mount();
    expect(document.querySelector('[role=alert]')?.textContent).toContain(
      'Unable to open the library',
    );
    expect(document.querySelector('[role=alert] button')?.textContent).toBe(
      'Retry',
    );
  });
});
