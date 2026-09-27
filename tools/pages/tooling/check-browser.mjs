import { readFile } from 'node:fs/promises';
import { parse } from 'acorn';
import postcss from 'postcss';

const root = new URL('../../../build/pages-assets/', import.meta.url);
parse(await readFile(new URL('portal.js', root), 'utf8'), {
  ecmaVersion: 5,
  sourceType: 'script',
});
const css = postcss.parse(await readFile(new URL('style.css', root), 'utf8'));
css.walkDecls((declaration) => {
  if (
    declaration.prop.startsWith('--') ||
    /^(grid|gap|row-gap|column-gap)/.test(declaration.prop) ||
    /var\(|\bdvh\b|\bgrid\b/.test(declaration.value)
  ) {
    throw declaration.error('CSS requires a feature unavailable in Safari 9.');
  }
});
css.walkRules((rule) => {
  if (
    /:(has|is|where)\(/.test(rule.selector) ||
    rule.selector.includes(':focus-visible')
  ) {
    throw rule.error('Selector requires a feature unavailable in Safari 9.');
  }
});
if (
  !css.toString().includes("format('woff')") &&
  !css.toString().includes('format("woff")')
) {
  throw new Error('Static WOFF font fallbacks are missing.');
}
process.stdout.write(
  'ES5 syntax, Safari 9 CSS checks, and WOFF fonts passed.\n',
);
