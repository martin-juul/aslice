import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  outputDir: '../../build/pages-test-results',
  use: { baseURL: 'http://127.0.0.1:8768/aslice/' },
  webServer: {
    command: 'python preview.py --port 8768',
    url: 'http://127.0.0.1:8768/aslice/',
    reuseExistingServer: false,
  },
});
