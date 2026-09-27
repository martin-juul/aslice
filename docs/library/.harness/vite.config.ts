import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';
import autoprefixer from 'autoprefixer';
import { legacyBrowser } from './tooling/legacy.ts';
import type { ProxyOptions } from 'vite';

const root = fileURLToPath(new URL('.', import.meta.url));
const proxy: Record<string, ProxyOptions> = process.env.LIBRARY_BACKEND
  ? { '/api': { target: process.env.LIBRARY_BACKEND } }
  : {};
const headers = {
  'Content-Security-Policy':
    "frame-ancestors 'none'; object-src 'none'; frame-src http://127.0.0.1:*",
  'X-Content-Type-Options': 'nosniff',
};

export default defineConfig({
  root,
  plugins: [legacyBrowser()],
  css: {
    postcss: {
      plugins: [autoprefixer({ overrideBrowserslist: ['Safari 9'] })],
    },
  },
  server: {
    host: '127.0.0.1',
    strictPort: true,
    proxy,
    headers,
    fs: {
      strict: true,
      allow: [root, fileURLToPath(new URL('../node_modules', import.meta.url))],
    },
  },
  preview: { host: '127.0.0.1', strictPort: true, proxy, headers },
  build: {
    target: 'esnext',
    cssTarget: 'safari9',
    cssMinify: false,
    cssCodeSplit: false,
    minify: false,
    modulePreload: false,
    outDir: 'dist',
    emptyOutDir: true,
    rolldownOptions: {
      output: {
        format: 'iife',
        codeSplitting: false,
        entryFileNames: 'app.js',
        assetFileNames: (asset) =>
          asset.names.some((name) => name.endsWith('.css'))
            ? 'app.css'
            : 'assets/[name]-[hash][extname]',
      },
    },
  },
  test: { environment: 'jsdom', include: ['src/**/*.test.ts'] },
});
