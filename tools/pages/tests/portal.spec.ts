import { expect, test } from '@playwright/test';

test('navigation, keyboard, appearance persistence and narrow reading', async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.goto('./');
  await expect(page.locator('html')).not.toHaveClass('dark');
  await page.keyboard.press('Tab');
  await expect(page.getByText('Skip to content')).toBeFocused();
  const appearance = page.getByRole('button', { name: 'Dark appearance' });
  await appearance.focus();
  await page.keyboard.press('Space');
  await expect(appearance).toHaveAttribute('aria-pressed', 'true');
  await page.reload();
  await expect(page.locator('html')).toHaveClass('dark');
  await page.getByRole('navigation').getByText('Commands').click();
  await page
    .getByRole('link', { name: 'aslice-install(1)', exact: true })
    .click();
  await expect(
    page.getByRole('heading', { name: 'SYNOPSIS', exact: true }),
  ).toBeVisible();
  await expect(page.locator('body')).toContainText('--');
  await page.setViewportSize({ width: 375, height: 812 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await appearance.click();
  await expect(page.locator('html')).not.toHaveClass('dark');
});

test('full static reader stays local, supports bookmarks, and keeps source appearance', async ({
  page,
}) => {
  const outside: string[] = [];
  page.on('request', (request) => {
    if (
      !request.url().startsWith('http://127.0.0.1:8768/') &&
      !request.url().startsWith('data:')
    ) {
      outside.push(request.url());
    }
  });
  await page.goto('library/');
  await page.locator('.card').click();
  const frame = page.frameLocator('#capture');
  await expect(frame.locator('body')).toContainText('Themes');
  await expect(page.locator('#capture')).toHaveAttribute(
    'sandbox',
    'allow-same-origin',
  );
  const before = await frame
    .locator('body')
    .evaluate((el) => getComputedStyle(el).backgroundColor);
  await page.getByRole('button', { name: 'Dark appearance' }).click();
  expect(
    await frame
      .locator('body')
      .evaluate((el) => getComputedStyle(el).backgroundColor),
  ).toBe(before);
  await page.getByLabel('Find a section').fill('Buttons');
  await page.locator('.contents li:visible a').first().click();
  await expect(frame.locator('body')).toContainText('Buttons');
  const bookmark = page.url();
  await page.reload();
  await expect(frame.locator('body')).toContainText('Buttons');
  expect(page.url()).toBe(bookmark);
  await page.getByLabel('Find a section').fill('');
  const link = frame.locator('a[href$=".html"]:visible').first();
  await link.click();
  await expect(page).not.toHaveURL(bookmark);
  await page.setViewportSize({ width: 375, height: 812 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await expect(page.locator('#capture')).toBeVisible();
  await page
    .getByRole('link', { name: 'Capture information and gaps' })
    .click();
  await expect(
    page.getByRole('heading', { name: 'Recorded gaps' }),
  ).toBeVisible();
  expect(outside).toEqual([]);
});

test('simulator introduction contains static screenshots only', async ({
  page,
}) => {
  await page.goto('simulator/');
  for (const [name, href] of [
    ['simulator guide', '../tools/simulator/README.html'],
    ['console build guide', '../tools/simulator/web/README.html'],
    ['Developing', '../docs/DEVELOPING.html'],
    ['design specification', '../docs/DESIGN.html'],
  ]) {
    await expect(page.getByRole('link', { name, exact: true })).toHaveAttribute(
      'href',
      href,
    );
  }
  await expect(page.locator('main img')).toHaveCount(2);
  for (const img of await page.locator('main img').all()) {
    expect(
      await img.evaluate(
        (el: HTMLImageElement) => el.complete && el.naturalWidth > 0,
      ),
    ).toBe(true);
  }
  await expect(page.locator('iframe, canvas')).toHaveCount(0);
  await expect(page.locator('main')).toContainText(
    'not evidence of a running Darwin guest',
  );
});

test('portal controls work without newer browser APIs or storage', async ({
  page,
}) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'fetch', { value: undefined });
    Object.defineProperty(window, 'Promise', { value: undefined });
    Object.defineProperty(window, 'localStorage', {
      get() {
        throw new Error('Storage unavailable');
      },
    });
  });
  await page.goto('./');
  await page.getByRole('button', { name: 'Dark appearance' }).click();
  await expect(page.locator('html')).toHaveClass('dark');
});
