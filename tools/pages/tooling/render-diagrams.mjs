import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';

const packages = fileURLToPath(new URL('../node_modules/', import.meta.url));
const font = await readFile(
  resolve(packages, '@fontsource/geist/files/geist-latin-400-normal.woff'),
);
const fontCSS = `@font-face { font-family: Geist; src: url(data:font/woff;base64,${font.toString('base64')}) format('woff'); font-weight: 400; }`;
let input = '';
for await (const chunk of process.stdin) {
  input += chunk;
}
const diagrams = JSON.parse(input);
const destination = process.argv[2];
await mkdir(destination, { recursive: true });
const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  await page.route(/^https?:/, (route) => route.abort());
  await page.setContent(
    '<!doctype html><html><head></head><body></body></html>',
  );
  await page.addStyleTag({ content: fontCSS });
  await page.evaluate(() => document.fonts.load('16px Geist'));
  await page.addScriptTag({
    path: resolve(packages, 'mermaid/dist/mermaid.js'),
  });
  for (const [key, definition] of Object.entries(diagrams)) {
    for (const appearance of ['light', 'dark']) {
      try {
        const svg = await page.evaluate(
          async ({ definition, appearance, fontCSS }) => {
            window.mermaid.initialize({
              startOnLoad: false,
              securityLevel: 'strict',
              theme: appearance === 'dark' ? 'dark' : 'default',
              fontFamily: 'Geist, Arial, sans-serif',
              htmlLabels: false,
            });
            const { svg } = await window.mermaid.render('diagram', definition);
            const document = new DOMParser().parseFromString(
              svg,
              'image/svg+xml',
            );
            const root = document.documentElement;
            // Mermaid sanitizes font URLs in themeCSS; embed our local font after rendering.
            const style = document.createElementNS(
              'http://www.w3.org/2000/svg',
              'style',
            );
            style.textContent = fontCSS;
            root.insertBefore(style, root.firstChild);
            const [, , width, height] = root
              .getAttribute('viewBox')
              .split(/\s+/)
              .map(Number);
            root.setAttribute('width', String(Math.ceil(width)));
            root.setAttribute('height', String(Math.ceil(height)));
            root.removeAttribute('style');
            return new XMLSerializer().serializeToString(root);
          },
          { definition, appearance, fontCSS },
        );
        await writeFile(resolve(destination, `${key}-${appearance}.svg`), svg);
      } catch (error) {
        throw new Error(
          `Cannot render Mermaid diagram ${key} (${appearance})`,
          { cause: error },
        );
      }
    }
  }
  console.log(
    `Rendered ${Object.keys(diagrams).length} Mermaid diagrams in both appearances.`,
  );
} finally {
  await browser.close();
}
