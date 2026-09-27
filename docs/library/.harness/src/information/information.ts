import { element } from '../dom';
import type { Book } from '../models';

export function information(book: Book): HTMLElement {
  const panel = element('aside', 'information');
  panel.id = 'information';
  panel.setAttribute('aria-label', 'Capture information');
  panel.appendChild(element('h2', '', 'Capture information'));
  panel.appendChild(element('p', '', book.title));
  panel.appendChild(element('p', 'metadata', book.edition));
  panel.appendChild(
    element(
      'p',
      '',
      `${book.counts?.page || 0} captured pages · ${book.counts?.asset || 0} assets · ${book.gaps || 0} recorded gaps.`,
    ),
  );
  panel.appendChild(
    element(
      'p',
      '',
      'Verified against the collection’s SHA256SUMS before opening. Historical dates and retrieval provenance vary by resource; see the manifest for each response.',
    ),
  );
  panel.appendChild(
    element('p', 'metadata', `Original entry: ${book.entry_url}`),
  );
  for (const [path, label] of [
    ['gaps/', 'Recorded gaps and provenance'],
    ['manifest.json', 'Capture manifest'],
    ['SHA256SUMS', 'File checksums'],
  ]) {
    const row = element('p');
    const link = element('a', '', label);
    link.href = `${book.origin}/__library/${path}`;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    row.appendChild(link);
    panel.appendChild(row);
  }
  panel.appendChild(
    element(
      'p',
      '',
      'Preserved responses remain unchanged. Missing resources show local gap pages; browsing never downloads replacements.',
    ),
  );
  return panel;
}
