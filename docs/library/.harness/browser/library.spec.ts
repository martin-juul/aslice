import { test, expect } from '@playwright/test';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const checksums = new URL(
  '../../apple-macos-hig-2018/SHA256SUMS',
  import.meta.url,
);

test.afterAll(() => {
  execFileSync(
    process.env.LIBRARY_PYTHON || 'python',
    ['-m', 'tools.library', 'verify', 'apple-macos-hig-2018'],
    {
      cwd: fileURLToPath(new URL('../../../../', import.meta.url)),
    },
  );
});

test('shelf, original navigation, sections, information, appearance and narrow reading', async ({
  page,
}) => {
  const before = createHash('sha256')
    .update(await readFile(checksums))
    .digest('hex');
  const external: string[] = [];
  const blocked = new Map<string, string>();
  const externalResponses: string[] = [];
  page.on('requestfailed', (request) => {
    blocked.set(request.url(), request.failure()?.errorText || 'unknown');
  });
  page.on('response', (response) => {
    if (
      /^https?:/.test(response.url()) &&
      new URL(response.url()).hostname !== '127.0.0.1'
    )
      externalResponses.push(response.url());
  });
  page.on('request', (request) => {
    if (
      /^https?:/.test(request.url()) &&
      new URL(request.url()).hostname !== '127.0.0.1'
    )
      external.push(request.url());
  });
  await page.goto('/');
  await expect(page.locator('.book')).toHaveCount(1);
  await expect(page.locator('html')).toHaveClass('light');
  await page.screenshot({ path: '.harness/test-results/shelf-light.png' });
  const book = page.locator('.book-link');
  await book.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('iframe')).toBeVisible();
  const frame = page.frameLocator('iframe');
  await expect(
    frame
      .getByRole('heading', {
        name: /macOS Design Themes|Visual Index|Sidebars/,
        level: 2,
        exact: true,
      })
      .last(),
  ).toContainText('Themes');
  // A source-site link stays inside the original site, on its replay origin.
  await frame.getByRole('link', { name: 'Visual Index', exact: true }).click();
  await expect(
    frame
      .getByRole('heading', {
        name: /macOS Design Themes|Visual Index|Sidebars/,
        level: 2,
        exact: true,
      })
      .last(),
  ).toContainText('Visual Index');
  await page.getByLabel('Filter contents').fill('/windows-and-views/sidebars/');
  await page.locator('.section-links a').first().click();
  await expect(
    frame
      .getByRole('heading', {
        name: /macOS Design Themes|Visual Index|Sidebars/,
        level: 2,
        exact: true,
      })
      .last(),
  ).toContainText('Sidebars');
  expect(page.url()).toContain('https%3A');
  const source = await page.locator('iframe').getAttribute('src');
  expect(
    await frame.locator('body').evaluate(() => {
      try {
        void window.parent.document.title;
        return false;
      } catch {
        return true;
      }
    }),
  ).toBe(true);
  await page.getByRole('button', { name: 'Information', exact: true }).click();
  await expect(page.getByLabel('Capture information')).toContainText(
    '100 recorded gaps',
  );
  await expect(
    page.getByRole('link', { name: 'Capture manifest', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Dark appearance' }).click();
  await expect(page.locator('html')).toHaveClass('dark');
  expect(await page.locator('iframe').getAttribute('src')).toBe(source);
  await page.screenshot({ path: '.harness/test-results/reader-dark.png' });
  await page.reload();
  await expect(page.locator('html')).toHaveClass('dark');
  await expect(
    frame
      .getByRole('heading', {
        name: /macOS Design Themes|Visual Index|Sidebars/,
        level: 2,
        exact: true,
      })
      .last(),
  ).toContainText('Sidebars');
  await page.setViewportSize({ width: 390, height: 780 });
  await expect(page.getByLabel('Captured sections')).toBeHidden();
  await page.reload();
  await expect(page.getByLabel('Captured sections')).toBeHidden();
  await expect(page.locator('iframe')).toHaveJSProperty('clientWidth', 390);
  await page.getByRole('button', { name: 'Contents', exact: true }).click();
  await expect(page.getByLabel('Captured sections')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByLabel('Captured sections')).toBeHidden();
  await page.screenshot({ path: '.harness/test-results/reader-narrow.png' });
  await page.getByRole('link', { name: 'Library', exact: true }).click();
  await expect(page.locator('.book-link')).toBeFocused();
  await page.getByLabel('Search library').fill('sidebars');
  await expect(page.locator('.book')).toHaveCount(1);
  await page.getByRole('button', { name: 'List', exact: true }).click();
  await expect(page.locator('.books')).toHaveClass('books list');
  // Chromium reports CSP-rejected attempts as request events even though they
  // never reach the network. Every external attempt must fail for that reason.
  expect(externalResponses).toEqual([]);
  for (const url of external) expect(blocked.get(url), url).toBe('csp');
  expect(
    createHash('sha256')
      .update(await readFile(checksums))
      .digest('hex'),
  ).toBe(before);
});

test('compiled viewer works without native fetch or Promise', async ({
  page,
}) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'fetch', {
      value: undefined,
      writable: true,
    });
    Object.defineProperty(window, 'Promise', {
      value: undefined,
      writable: true,
    });
  });
  await page.goto('/');
  await expect(page.locator('.book-link')).toBeVisible();
  await page.locator('.book-link').click();
  await expect(
    page
      .frameLocator('iframe')
      .getByRole('heading', { name: 'macOS Design Themes', exact: true }),
  ).toContainText('Themes');
});
