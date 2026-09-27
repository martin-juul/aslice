import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './browser',
  outputDir: './test-results',
  timeout: 60000,
  use: {
    baseURL: 'http://127.0.0.1:8876',
    viewport: { width: 1280, height: 850 },
  },
  webServer: {
    command: 'node .harness/launch.mjs --built --no-open --port 8876',
    cwd: '..',
    url: 'http://127.0.0.1:8876/api/catalog',
    reuseExistingServer: false,
    timeout: 90000,
  },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
});
