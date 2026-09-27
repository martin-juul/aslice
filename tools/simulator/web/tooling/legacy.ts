import { transformAsync } from '@babel/core';
import { parse } from 'acorn';
import { resolve } from 'node:path';
import type { Plugin } from 'vite';

/** Vite bundles dependencies; Babel lowers the entire result, including vendors. */
export function legacyBrowser(root: string): Plugin {
  return {
    name: 'console-safari-nine',
    enforce: 'post',
    transform(code, id) {
      if (id.replaceAll('\\', '/').endsWith('/zod/v4/core/util.js')) {
        const ranges = /export const BIGINT_FORMAT_RANGES = (\{[\s\S]*?\n\});/;
        if (!ranges.test(code)) {
          throw new Error(
            'Review Zod integer range initialization for this version.',
          );
        }
        // The control protocol uses JSON numbers, never bigint schemas. Avoid
        // initializing unused bigint limits on an engine without that type.
        return code.replace(
          ranges,
          "export const BIGINT_FORMAT_RANGES = typeof BigInt === 'function' ? $1 : {};",
        );
      }
      if (
        id.replaceAll('\\', '/').endsWith('/@novnc/novnc/core/util/browser.js')
      ) {
        const probe =
          'supportsWebCodecsH264Decode = await _checkWebCodecsH264DecodeSupport();';
        if (!code.includes(probe)) {
          throw new Error(
            'Review the noVNC WebCodecs probe for this dependency version.',
          );
        }
        // Safari 9 has no WebCodecs. Negotiate the ordinary VNC encodings instead;
        // this also removes the dependency's top-level await from the classic bundle.
        return code.replace(probe, 'supportsWebCodecsH264Decode = false;');
      }
      return undefined;
    },
    resolveId: {
      order: 'pre',
      handler(source, importer) {
        if (
          source === './bigint.js' &&
          importer?.replaceAll('\\', '/').includes('/@novnc/novnc/core/crypto/')
        ) {
          return resolve(root, 'src/compatibility/novnc-integers.ts');
        }
        return undefined;
      },
    },
    async generateBundle(_options, bundle) {
      for (const entry of Object.values(bundle)) {
        if (entry.type === 'chunk') {
          const transformed = await transformAsync(entry.code, {
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
          if (!transformed?.code) {
            throw new Error(
              `Unable to compile ${entry.fileName} for Safari 9.`,
            );
          }
          // Fail the build if a dependency introduces syntax Babel cannot lower.
          parse(transformed.code, { ecmaVersion: 5, sourceType: 'script' });
          entry.code = transformed.code;
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
