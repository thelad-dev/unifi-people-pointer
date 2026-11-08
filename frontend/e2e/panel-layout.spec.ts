import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';

const PANEL_JS = readFileSync(
  fileURLToPath(
    new URL('../../custom_components/unifi_people_pointer/panel/upp-panel.js', import.meta.url),
  ),
  'utf8',
);

const HA_ORIGIN = 'http://ha.test:8123';
const UI_PORT = 8765;
const HEADER_HEIGHT = 56;

// Same height chain as the Home Assistant frontend: the panel resolver spans
// the window, while ha-panel-custom (which hosts a custom panel element) is a
// plain block whose height is auto.
const HA_PAGE = `<!DOCTYPE html>
<html>
<head>
  <style>
    html, body { margin: 0; height: 100%; }
    partial-panel-resolver { display: block; height: 100%; }
    ha-panel-custom { display: block; }
  </style>
</head>
<body>
  <partial-panel-resolver><ha-panel-custom></ha-panel-custom></partial-panel-resolver>
  <script>
    customElements.define('ha-menu-button', class extends HTMLElement {});
  </script>
  <script src="/upp-panel.js"></script>
  <script>
    const panel = document.createElement('unifi-people-pointer-panel');
    panel.hass = { auth: { data: { access_token: 'test-token' } } };
    panel.narrow = false;
    panel.panel = { config: { port: ${UI_PORT} } };
    document.querySelector('ha-panel-custom').appendChild(panel);
  </script>
</body>
</html>`;

const VIEWPORTS = [
  { name: 'desktop', width: 1906, height: 995 },
  { name: 'tablet', width: 820, height: 1180 },
  { name: 'phone', width: 390, height: 844 },
];

for (const viewport of VIEWPORTS) {
  test(`panel fills the window below its toolbar (${viewport.name} ${viewport.width}x${viewport.height})`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.route(`${HA_ORIGIN}/**`, (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path === '/upp-panel.js') {
        return route.fulfill({ contentType: 'text/javascript', body: PANEL_JS });
      }
      return route.fulfill({ contentType: 'text/html', body: HA_PAGE });
    });
    await page.route(`http://ha.test:${UI_PORT}/**`, (route) =>
      route.fulfill({ contentType: 'text/html', body: '<!DOCTYPE html><title>web UI</title>' }),
    );

    await page.goto(`${HA_ORIGIN}/unifi-people-pointer`);

    const toolbar = page.locator('unifi-people-pointer-panel .toolbar');
    const frame = page.locator('unifi-people-pointer-panel iframe');
    await expect(frame).toHaveAttribute('src', `http://ha.test:${UI_PORT}/`);

    const toolbarBox = await toolbar.boundingBox();
    const frameBox = await frame.boundingBox();
    expect(toolbarBox).toEqual({ x: 0, y: 0, width: viewport.width, height: HEADER_HEIGHT });
    expect(frameBox).toEqual({
      x: 0,
      y: HEADER_HEIGHT,
      width: viewport.width,
      height: viewport.height - HEADER_HEIGHT,
    });

    // No second, outer scrollbar next to the one inside the web UI.
    const scrollHeight = await page.evaluate(() => document.documentElement.scrollHeight);
    expect(scrollHeight).toBe(viewport.height);
  });
}
