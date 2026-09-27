import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { defineConfig } from 'vitest/config';
import { licenses } from './tooling/licenses.ts';
import { legacyBrowser } from './tooling/legacy.ts';
import autoprefixer from 'autoprefixer';
import { cssCompatibility } from './tooling/css-compatibility.ts';

const root = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig(({ command, mode, isPreview }) => {
  let target = process.env.SIMULATOR_CONTROLLER_URL;
  if (target) {
    const url = new URL(target);
    if (
      url.protocol !== 'http:' ||
      !['127.0.0.1', 'localhost'].includes(url.hostname) ||
      url.username ||
      url.password ||
      url.pathname !== '/' ||
      url.search ||
      url.hash
    ) {
      throw new Error(
        'SIMULATOR_CONTROLLER_URL must be a loopback HTTP origin.',
      );
    }
    url.hostname = '127.0.0.1';
    target = url.origin;
  }
  return {
    base: command === 'build' || isPreview ? '/static/' : '/',
    plugins: [licenses(root), legacyBrowser(root)],
    css: {
      postcss: {
        plugins: [
          cssCompatibility(),
          autoprefixer({ overrideBrowserslist: ['Safari 9'] }),
        ],
      },
    },
    server: {
      host: '127.0.0.1',
      port: 5173,
      strictPort: true,
      proxy:
        mode === 'live' && target
          ? {
              '/v1': {
                target,
                changeOrigin: true,
                ws: true,
                configure(proxy) {
                  const origin = 'http://127.0.0.1:5173';
                  proxy.on('proxyReq', (request, incoming) => {
                    if (incoming.headers.origin === origin) {
                      request.setHeader('Origin', target);
                    }
                  });
                  proxy.on('proxyReqWs', (request, incoming) => {
                    if (incoming.headers.origin === origin) {
                      request.setHeader('Origin', target);
                    }
                  });
                },
              },
            }
          : {},
    },
    preview: { host: '127.0.0.1', port: 4173, strictPort: true },
    build: {
      target: 'esnext',
      cssTarget: 'safari9',
      cssMinify: false,
      cssCodeSplit: false,
      minify: false,
      modulePreload: false,
      outDir: resolve(
        root,
        `../../../build/simulator-web${mode === 'demo' ? '-demo' : ''}`,
      ),
      emptyOutDir: true,
      rolldownOptions: {
        output: {
          format: 'iife',
          codeSplitting: false,
          entryFileNames: 'app.js',
          chunkFileNames: 'chunks/[name]-[hash].js',
          assetFileNames: (asset) =>
            asset.names.some((name) => name.endsWith('.css'))
              ? 'app.css'
              : 'assets/[name]-[hash][extname]',
        },
      },
    },
    test: {
      environment: 'node',
      include: ['src/**/*.test.ts'],
      coverage: {
        provider: 'v8',
        include: ['src/**/*.ts'],
        exclude: ['src/**/*.test.ts', 'src/**/*.d.ts'],
        reportsDirectory: '../../../build/simulator-web-coverage',
        reporter: ['text', 'html'],
      },
    },
  };
});
