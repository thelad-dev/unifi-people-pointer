import { defineConfig, devices } from '@playwright/test';

// Browser layout tests for the Home Assistant sidebar panel
// (custom_components/unifi_people_pointer/panel/upp-panel.js).
export default defineConfig({
  testDir: './e2e',
  forbidOnly: !!process.env.CI,
  reporter: 'list',
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
