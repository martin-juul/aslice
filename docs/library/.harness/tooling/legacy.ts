import { transformAsync } from '@babel/core';
import { parse } from 'acorn';
import type { Plugin } from 'vite';

/** Lower the complete bundle, including dependencies, to a classic ES5 script. */
export function legacyBrowser(): Plugin {
  return {
    name: 'library-safari-nine',
    enforce: 'post',
    async generateBundle(_options, bundle) {
      for (const entry of Object.values(bundle)) {
        if (entry.type === 'chunk') {
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
            compact: true,
            comments: false,
          });
          if (!result?.code) throw new Error('Unable to compile for Safari 9.');
          parse(result.code, { ecmaVersion: 5, sourceType: 'script' });
          entry.code = result.code;
        } else if (entry.fileName === 'index.html') {
          entry.source = String(entry.source).replace(
            /<script type="module" crossorigin src="([^"]+)"><\/script>/g,
            '<script defer src="$1"></script>',
          );
        }
      }
    },
  };
}
