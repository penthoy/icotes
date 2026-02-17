// @ts-check
import { defineConfig, devices } from '@playwright/test';

/**
 * icotes E2E Test Configuration
 * 
 * Override with SITE_URL env var for local testing:
 *   SITE_URL=http://localhost:8000 bun run e2e
 */

const BASE_URL = process.env.SITE_URL

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // Sequential — panels share WebSocket state
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: 1, // Single worker — icotes is a stateful single-session app
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
  ],
  timeout: 60_000, // 60s per test — remote server may be slow
  expect: {
    timeout: 15_000, // 15s for assertions (WebSocket init, panel loading)
  },

  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
    // Ignore HTTPS errors for self-signed certs in dev
    ignoreHTTPSErrors: true,
  },

  /* Only Chromium — sufficient for icotes panel-based UI */
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
      },
    },
  ],
});

