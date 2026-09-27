import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { parse } from 'acorn';
import postcss from 'postcss';

for (const directory of ['simulator-web', 'simulator-web-demo']) {
  const root = resolve('../../../build', directory);
  const script = await readFile(resolve(root, 'app.js'), 'utf8');
  parse(script, { ecmaVersion: 5, sourceType: 'script' });
  const html = await readFile(resolve(root, 'index.html'), 'utf8');
  if (
    html.includes('type="module"') ||
    !html.includes('<script defer src="/static/app.js"')
  ) {
    throw new Error(`${directory}: missing classic script entry.`);
  }
  const css = postcss.parse(await readFile(resolve(root, 'app.css'), 'utf8'));
  css.walkDecls((declaration) => {
    if (
      declaration.prop.startsWith('--') ||
      /^(grid|gap|row-gap|column-gap)/.test(declaration.prop) ||
      /var\(|\bdvh\b|\bgrid\b/.test(declaration.value)
    ) {
      throw declaration.error(
        'CSS requires a feature unavailable in Safari 9.',
      );
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
    !css.toString().includes('.woff)') &&
    !css.toString().includes('.woff"')
  ) {
    throw new Error(`${directory}: static WOFF font fallback is missing.`);
  }
  process.stdout.write(
    `${directory}: ES5 entry, Safari 9 CSS checks and WOFF fonts passed.\n`,
  );
}
