import { defineConfig, devices } from '@playwright/test';

const CI = !!process.env['CI'];

/**
 * End-to-end tests: the 5 journeys of requirements.md §2 with real clicks, on a desktop and
 * on a phone. They run against the production build and their own Django and database
 * (e2e/backend.mjs), on ports 4300 and 8001: the development servers can stay open.
 */
export default defineConfig({
  testDir: 'e2e',
  testMatch: '*.e2e.ts', // *.spec.ts are the Vitest unit tests
  fullyParallel: true,
  forbidOnly: CI,
  retries: CI ? 1 : 0,
  workers: CI ? 2 : undefined,
  reporter: CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  // Sign-up hashes the password and signs in: slower with every test hitting one runserver.
  expect: { timeout: 10_000 },
  use: {
    baseURL: 'http://localhost:4300',
    locale: 'es-ES',
    timezoneId: 'Europe/Madrid',
    trace: 'retain-on-failure',
    // The service worker would serve cached app files between tests: always the network here.
    serviceWorkers: 'block',
  },
  projects: [
    {
      name: 'escritorio',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 } },
    },
    { name: 'movil', use: { ...devices['Pixel 7'] } },
  ],
  webServer: [
    {
      command: 'node e2e/backend.mjs',
      url: 'http://127.0.0.1:8001/api/v1/health/',
      reuseExistingServer: !CI,
      timeout: 120_000,
    },
    {
      command:
        'npx ng serve --configuration production --port 4300 --proxy-config e2e/proxy.e2e.json',
      url: 'http://localhost:4300',
      reuseExistingServer: !CI,
      timeout: 240_000,
    },
  ],
});
