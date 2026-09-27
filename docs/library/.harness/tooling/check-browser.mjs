import { readFile } from 'node:fs/promises';
import { parse } from 'acorn';
import postcss from 'postcss';

const root = new URL('../dist/', import.meta.url);
parse(await readFile(new URL('app.js', root), 'utf8'), {
  ecmaVersion: 5,
  sourceType: 'script',
});
const html = await readFile(new URL('index.html', root), 'utf8');
if (
  html.includes('type="module"') ||
  !html.includes('<script defer src="/app.js"')
)
  throw new Error('Missing classic script entry.');
const css = postcss.parse(await readFile(new URL('app.css', root), 'utf8'));
css.walkDecls((declaration) => {
  if (
    declaration.prop.startsWith('--') ||
    /^(grid|gap|row-gap|column-gap)/.test(declaration.prop) ||
    /var\(|\bdvh\b|\bgrid\b/.test(declaration.value)
  )
    throw declaration.error('CSS requires a feature unavailable in Safari 9.');
});
css.walkRules((rule) => {
  if (
    /:(has|is|where)\(/.test(rule.selector) ||
    rule.selector.includes(':focus-visible')
  )
    throw rule.error('Selector requires a feature unavailable in Safari 9.');
});
if (!/\.woff["')]/.test(css.toString()))
  throw new Error('Static WOFF fonts are missing.');
console.log(
  'ES5 syntax, classic entry, Safari 9 CSS and WOFF checks passed. Actual OS X qualification is separate.',
);
