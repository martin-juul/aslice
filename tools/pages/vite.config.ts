import { defineConfig } from 'vite';
import autoprefixer from 'autoprefixer';
import { legacyBrowser } from './tooling/legacy.ts';

export default defineConfig({
  plugins: [legacyBrowser()],
  css: {
    postcss: {
      plugins: [autoprefixer({ overrideBrowserslist: ['Safari 9'] })],
    },
  },
  build: {
    target: 'esnext',
    cssTarget: 'safari9',
    cssMinify: false,
    minify: false,
    outDir: '../../build/pages-assets',
    emptyOutDir: true,
    lib: {
      entry: 'src/portal.ts',
      name: 'aslicePages',
      formats: ['iife'],
      fileName: () => 'portal.js',
      cssFileName: 'style',
    },
  },
});
