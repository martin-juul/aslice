import { createHash } from 'node:crypto';
import { readFile, readdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import type { Plugin } from 'vite';

export function licenses(root: string): Plugin {
  return {
    name: 'console-dependency-notices',
    async generateBundle() {
      const files = new Map([
        ['@fontsource/geist/LICENSE', 'geist.txt'],
        ['@fontsource/geist-mono/LICENSE', 'geist-mono.txt'],
        ['@fontsource/space-grotesk/LICENSE', 'space-grotesk.txt'],
        ['@xterm/xterm/LICENSE', 'xterm.txt'],
        ['@xterm/addon-fit/LICENSE', 'xterm-fit.txt'],
        ['@novnc/novnc/LICENSE.txt', 'novnc.txt'],
        ['@novnc/novnc/AUTHORS', 'novnc-authors.txt'],
        ['@novnc/novnc/vendor/pako/LICENSE', 'novnc-pako.txt'],
        ['zod/LICENSE', 'zod.txt'],
        ['core-js/LICENSE', 'core-js.txt'],
        ['whatwg-fetch/LICENSE', 'fetch.txt'],
        ['abortcontroller-polyfill/LICENSE', 'abort-controller.txt'],
        ['resize-observer-polyfill/LICENSE', 'resize-observer.txt'],
        ['fast-text-encoding/LICENSE', 'text-encoding.txt'],
        ['pepjs/LICENSE.txt', 'pointer-events.txt'],
        ['jsbi/LICENSE', 'jsbi.txt'],
        ['js-sha256/LICENSE.txt', 'sha256.txt'],
      ]);
      // addon-serialize publishes no separate LICENSE; its bundled notices use
      // the root xterm MIT license, already included as xterm.txt.
      for (const addon of ['webgl', 'unicode11', 'image', 'progress']) {
        files.set(`@xterm/addon-${addon}/LICENSE`, `xterm-${addon}.txt`);
      }
      for (const name of await readdir(
        resolve(root, 'node_modules/@novnc/novnc/docs'),
      )) {
        if (name.startsWith('LICENSE')) {
          files.set(`@novnc/novnc/docs/${name}`, name);
        }
      }
      for (const [source, name] of files) {
        this.emitFile({
          type: 'asset',
          fileName: `licenses/${name}`,
          source: await readFile(resolve(root, 'node_modules', source)),
        });
      }
      const lock = await readFile(resolve(root, 'package-lock.json'));
      this.emitFile({
        type: 'asset',
        fileName: 'dependencies.json',
        source: JSON.stringify(
          {
            lock_sha256: createHash('sha256').update(lock).digest('hex'),
            packages: JSON.parse(lock.toString()).packages,
          },
          null,
          2,
        ),
      });
    },
  };
}
