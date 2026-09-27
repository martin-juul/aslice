import { transformAsync } from '@babel/core';
import { parse } from 'acorn';
import type { Plugin } from 'vite';

/** Match the console's TypeScript/Vite -> Babel -> ES5 verification pipeline. */
export function legacyBrowser(): Plugin {
  return {
    name: 'pages-safari-nine',
    enforce: 'post',
    async generateBundle(_options, bundle) {
      for (const entry of Object.values(bundle)) {
        if (entry.type !== 'chunk') {
          continue;
        }
        const result = await transformAsync(entry.code, {
          babelrc: false,
          configFile: false,
          sourceType: 'script',
          presets: [
            [
              '@babel/preset-env',
              {
                targets: { safari: '9' },
                forceAllTransforms: true,
                modules: false,
              },
            ],
          ],
          comments: false,
        });
        if (!result?.code) {
          throw new Error('Unable to compile portal JavaScript for Safari 9.');
        }
        parse(result.code, { ecmaVersion: 5, sourceType: 'script' });
        entry.code = result.code;
      }
    },
  };
}
