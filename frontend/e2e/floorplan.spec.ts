import { readFileSync } from 'node:fs';
import { extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Page } from '@playwright/test';

// Layout of the "Floor plan" tab of the bundled web UI, at the sizes the web
// UI gets inside the Home Assistant panel (window minus the 56 px toolbar).
// The built bundle is served as is; the JSON API is mocked.

const WEBUI_DIR = new URL('../../custom_components/unifi_people_pointer/webui/', import.meta.url);
const FIXTURES = new URL('./fixtures/', import.meta.url);
const ORIGIN = 'http://ui.test';
const CONTENT_TYPES: Record<string, string> = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
};

const VIEWPORTS = [
  { name: 'desktop', width: 1906, height: 995 - 56, sideBySide: true, fitsHeight: true },
  { name: 'tablet', width: 820, height: 1180 - 56, sideBySide: false, fitsHeight: true },
  { name: 'phone', width: 390, height: 844 - 56, sideBySide: false, fitsHeight: false },
];

const FLOORS = [
  { id: 'eg', name: 'EG', level: 0, width: 700, height: 1200, width_m: 12, image_url: '/api/floorplan/floors/eg/image?v=eg-1.png' },
  { id: 'og', name: 'OG', level: 1, width: 1000, height: 700, width_m: null, image_url: '/api/floorplan/floors/og/image?v=og-1.png' },
];
const IMAGES: Record<string, string> = { eg: 'floor-portrait.png', og: 'floor-landscape.png' };

function floorplan(locate = true) {
  return {
    floors: FLOORS,
    aps: [
      { mac: '24:5a:4c:00:00:01', name: 'AP Hall', clients: 9, floor: 'eg', x: 0.3, y: 0.45 },
      { mac: '24:5a:4c:00:00:02', name: 'AP Living', clients: 4, floor: 'eg', x: 0.75, y: 0.25 },
      { mac: '24:5a:4c:00:00:04', name: 'AP Upstairs', clients: 6, floor: 'og', x: 0.5, y: 0.5 },
      { mac: '24:5a:4c:00:00:05', name: 'AP Garage', clients: 0, floor: null, x: null, y: null },
    ],
    persons: locate
      ? [
          { id: 'alex', name: 'Alex Doe', ap_mac: '24:5a:4c:00:00:02', ap_name: 'AP Living', signal: -48, radius_m: 2, floor: 'eg', x: 0.75, y: 0.25 },
          { id: 'sam', name: 'Sam', ap_mac: '24:5a:4c:00:00:01', ap_name: 'AP Hall', signal: -60, radius_m: 4.6, floor: 'eg', x: 0.3, y: 0.45 },
          { id: 'kim', name: 'Kim Lee', ap_mac: '24:5a:4c:00:00:01', ap_name: 'AP Hall', signal: -70, radius_m: 10, floor: 'eg', x: 0.3, y: 0.45 },
        ]
      : [],
    privacy: { locate_persons: locate, persons: locate ? ['alex', 'sam', 'kim'] : [] },
  };
}

const PERSONS = ['alex', 'sam', 'kim'].map((id) => ({
  id,
  name: id,
  ha_person: null,
  device_ids: [],
  state: 'home',
  devices_online: 1,
  ap_name: null,
}));

function usage(period: string, hasBytes = true) {
  const scale = period === 'now' ? 1 : 0.5;
  const rows = [
    { mac: '24:5a:4c:00:00:01', name: 'AP Hall', clients: 8 * scale, clients_max: 9, bytes: hasBytes ? 4e8 : null, floor: 'eg', x: 0.3, y: 0.45 },
    { mac: '24:5a:4c:00:00:02', name: 'AP Living', clients: 2 * scale, clients_max: 3, bytes: hasBytes ? 1e9 : null, floor: 'eg', x: 0.75, y: 0.25 },
    { mac: '24:5a:4c:00:00:04', name: 'AP Upstairs', clients: 4 * scale, clients_max: 5, bytes: hasBytes ? 2e8 : null, floor: 'og', x: 0.5, y: 0.5 },
    { mac: '24:5a:4c:00:00:05', name: 'AP Garage', clients: 0, clients_max: 0, bytes: hasBytes ? 0 : null, floor: null, x: null, y: null },
  ];
  return {
    period,
    bytes_unit: period === 'now' ? 'B/s' : 'B',
    has_bytes: hasBytes,
    samples: 12,
    since: '2026-11-08T20:00:00',
    aps: rows,
  };
}

async function serve(
  page: Page,
  data: ReturnType<typeof floorplan>,
  puts: unknown[] = [],
  usageRequests: string[] = [],
  hasBytes = true,
) {
  await page.addInitScript(() => localStorage.setItem('upp-ha-token', 'test-token'));
  await page.route(`${ORIGIN}/**`, (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    if (path.startsWith('/api/')) {
      expect(request.headers()['authorization']).toBe('Bearer test-token');
      const image = path.match(/^\/api\/floorplan\/floors\/(\w+)\/image$/);
      if (image) {
        return route.fulfill({ contentType: 'image/png', body: readFileSync(new URL(IMAGES[image[1]], FIXTURES)) });
      }
      if (path === '/api/floorplan') return route.fulfill({ json: data });
      if (path === '/api/floorplan/usage') {
        const period = url.searchParams.get('period') || 'now';
        usageRequests.push(period);
        return route.fulfill({ json: usage(period, hasBytes) });
      }
      if (path === '/api/persons') return route.fulfill({ json: PERSONS });
      if (path.startsWith('/api/floorplan/aps/') && request.method() === 'PUT') {
        puts.push({ path, body: request.postDataJSON() });
        return route.fulfill({ json: request.postDataJSON() });
      }
      return route.fulfill({ status: 404, json: { error: 'not found' } });
    }
    const file = path === '/' ? 'index.html' : path.slice(1);
    return route.fulfill({
      contentType: CONTENT_TYPES[extname(file)] || 'application/octet-stream',
      body: readFileSync(fileURLToPath(new URL(file, WEBUI_DIR))),
    });
  });
}

async function box(page: Page, selector: string) {
  const result = await page.locator(selector).first().boundingBox();
  expect(result, selector).not.toBeNull();
  return result!;
}

for (const viewport of VIEWPORTS) {
  test(`floor plan fits the panel (${viewport.name} ${viewport.width}x${viewport.height})`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await serve(page, floorplan());
    await page.goto(`${ORIGIN}/#/floor-plan`);
    await expect(page.getByRole('img', { name: 'Floor plan EG' })).toBeVisible();

    const main = await box(page, '.main-content');
    const padding = viewport.width <= 640 ? 16 : 32;
    const stage = await box(page, '[data-testid=map-stage]');

    // Same aspect as the image, whole pixels, inside the content column.
    expect(Math.abs(stage.width / stage.height - 700 / 1200)).toBeLessThan(0.005);
    expect(Number.isInteger(stage.width) && Number.isInteger(stage.height)).toBe(true);
    expect(stage.x).toBeGreaterThanOrEqual(main.x + padding);
    expect(stage.x + stage.width).toBeLessThanOrEqual(main.x + main.width - padding);
    if (viewport.fitsHeight) {
      // The whole plan is visible without scrolling.
      expect(stage.y + stage.height).toBeLessThanOrEqual(viewport.height - padding);
    } else {
      expect(stage.width).toBe(viewport.width - 2 * padding);
    }

    // No horizontal scrolling anywhere.
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBe(viewport.width);

    // Markers sit on their fractions of the image.
    const ap = await box(page, '[data-testid="ap-24:5a:4c:00:00:02"] .ap-dot');
    expect(Math.abs(ap.x + ap.width / 2 - (stage.x + 0.75 * stage.width))).toBeLessThanOrEqual(0.5);
    expect(Math.abs(ap.y + ap.height / 2 - (stage.y + 0.25 * stage.height))).toBeLessThanOrEqual(0.5);
    // A single person sits on the AP; two at one AP fan out around it.
    const alex = await box(page, '[data-testid=person-alex] .person-badge');
    expect(Math.abs(alex.x + alex.width / 2 - (ap.x + ap.width / 2))).toBeLessThanOrEqual(0.5);
    expect(Math.abs(alex.y + alex.height / 2 - (ap.y + ap.height / 2))).toBeLessThanOrEqual(0.5);
    const sam = await box(page, '[data-testid=person-sam] .person-badge');
    const kim = await box(page, '[data-testid=person-kim] .person-badge');
    const hallX = stage.x + 0.3 * stage.width;
    const hallY = stage.y + 0.45 * stage.height;
    expect(Math.abs(sam.x + sam.width / 2 - hallX)).toBeLessThanOrEqual(0.5);
    expect(Math.abs(sam.y + sam.height / 2 - (hallY - 26))).toBeLessThanOrEqual(0.5);
    expect(Math.abs(kim.y + kim.height / 2 - (hallY + 26))).toBeLessThanOrEqual(0.5);

    // Uncertainty circles scale with the plan: radius in meters over 12 m width.
    const circles = page.locator('.map-overlay circle');
    await expect(circles).toHaveCount(3);
    const kimCircle = await circles.nth(2).boundingBox();
    expect(Math.abs(kimCircle!.width / 2 - (10 * stage.width) / 12)).toBeLessThanOrEqual(1);

    // Side panel: next to the map on desktop, below it on smaller screens.
    const side = await box(page, '.floorplan-side .side-card');
    if (viewport.sideBySide) {
      expect(side.x).toBeGreaterThanOrEqual(stage.x + stage.width);
      expect(side.y).toBe(stage.y);
    } else {
      expect(side.y).toBeGreaterThanOrEqual(stage.y + stage.height);
    }
  });
}

test('landscape floor fills the column width on desktop', async ({ page }) => {
  await page.setViewportSize({ width: 1906, height: 939 });
  await serve(page, floorplan());
  await page.goto(`${ORIGIN}/#/floor-plan`);
  await page.getByRole('tab', { name: 'OG' }).click();
  await expect(page.getByRole('img', { name: 'Floor plan OG' })).toBeVisible();
  const stage = await box(page, '[data-testid=map-stage]');
  const wrap = await box(page, '.map-wrap');
  expect(Math.abs(stage.width / stage.height - 1000 / 700)).toBeLessThan(0.005);
  expect(stage.width).toBeLessThanOrEqual(wrap.width);
  expect(stage.y + stage.height).toBeLessThanOrEqual(939 - 32);
  // No released person is on this floor.
  await expect(page.locator('.person-marker')).toHaveCount(0);
});

test('without the privacy release no person is drawn', async ({ page }) => {
  await page.setViewportSize({ width: 820, height: 1124 });
  await serve(page, floorplan(false));
  await page.goto(`${ORIGIN}/#/floor-plan`);
  await expect(page.getByRole('img', { name: 'Floor plan EG' })).toBeVisible();
  await expect(page.locator('.person-marker')).toHaveCount(0);
  await expect(page.locator('.map-overlay circle')).toHaveCount(0);
  await expect(page.getByText('Locating persons is off.')).toBeVisible();
});

test('placing an access point stores its fraction of the image', async ({ page }) => {
  const puts: { path: string; body: { floor: string; x: number; y: number } }[] = [];
  await page.setViewportSize({ width: 1906, height: 939 });
  await serve(page, floorplan(), puts);
  await page.goto(`${ORIGIN}/#/floor-plan`);
  await page.getByRole('button', { name: 'Edit' }).click();
  await page.getByRole('button', { name: 'Place' }).click();
  const stage = await box(page, '[data-testid=map-stage]');
  await page.mouse.click(stage.x + stage.width * 0.2, stage.y + stage.height * 0.8);
  await expect.poll(() => puts.length).toBe(1);
  expect(puts[0].path).toBe('/api/floorplan/aps/24%3A5a%3A4c%3A00%3A00%3A05');
  expect(puts[0].body.floor).toBe('eg');
  expect(Math.abs(puts[0].body.x - 0.2)).toBeLessThan(0.003);
  expect(Math.abs(puts[0].body.y - 0.8)).toBeLessThan(0.003);
});

for (const viewport of VIEWPORTS) {
  test(`heatmap colors the access points (${viewport.name} ${viewport.width}x${viewport.height})`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await serve(page, floorplan());
    await page.goto(`${ORIGIN}/#/floor-plan`);
    await expect(page.getByRole('img', { name: 'Floor plan EG' })).toBeVisible();
    await page.getByLabel('Heatmap').check();
    const spots = page.locator('.map-heat circle.heat-spot');
    await expect(spots).toHaveCount(2);

    const stage = await box(page, '[data-testid=map-stage]');
    if (viewport.fitsHeight) {
      // The period and measure row does not push the plan out of view.
      expect(stage.y + stage.height).toBeLessThanOrEqual(viewport.height - 32);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(viewport.width);

    // Spots sit on their APs; the busiest AP of the house is the hottest.
    const hall = await spots.nth(0).boundingBox();
    expect(Math.abs(hall!.x + hall!.width / 2 - (stage.x + 0.3 * stage.width))).toBeLessThanOrEqual(1);
    expect(Math.abs(hall!.y + hall!.height / 2 - (stage.y + 0.45 * stage.height))).toBeLessThanOrEqual(1);
    expect(Math.abs(hall!.width / 2 - (5 * stage.width) / 12)).toBeLessThanOrEqual(1);
    await expect(spots.nth(0)).toHaveAttribute('data-level', '1.000');
    await expect(spots.nth(1)).toHaveAttribute('data-level', '0.250');

    const panel = page.getByTestId('heatmap-panel');
    await expect(panel.locator('.usage-list li').first()).toContainText('AP Hall');
    await expect(panel.locator('.usage-list li').first()).toContainText('8');
    await expect(panel.locator('.heat-legend-scale span')).toHaveText(['0', '8']);
  });
}

test('heatmap periods and data volume', async ({ page }) => {
  const requests: string[] = [];
  await page.setViewportSize({ width: 1906, height: 939 });
  await serve(page, floorplan(), [], requests);
  await page.goto(`${ORIGIN}/#/floor-plan`);
  await page.getByLabel('Heatmap').check();
  await page.getByRole('button', { name: '24 h' }).click();
  await expect.poll(() => requests.includes('24h')).toBe(true);
  await page.getByRole('button', { name: 'Data' }).click();
  const spots = page.locator('.map-heat circle.heat-spot');
  // Living moved the most data: it is the hottest now.
  await expect(spots.nth(1)).toHaveAttribute('data-level', '1.000');
  await expect(page.getByTestId('heatmap-panel').locator('.usage-list li').first()).toContainText('1.0 GB');
  await expect(page.locator('.heat-label').first()).toBeVisible();
  // Scaled against the whole house, not per floor: OG is not automatically hot.
  await page.getByRole('tab', { name: 'OG' }).click();
  await expect(spots).toHaveCount(1);
  await expect(spots.nth(0)).toHaveAttribute('data-level', '0.200');
});

test('without client rates only clients can be shown', async ({ page }) => {
  await page.setViewportSize({ width: 820, height: 1124 });
  await serve(page, floorplan(false), [], [], false);
  await page.goto(`${ORIGIN}/#/floor-plan`);
  await page.getByLabel('Heatmap').check();
  await expect(page.locator('.map-heat circle.heat-spot')).toHaveCount(2);
  await expect(page.getByRole('button', { name: 'Data' })).toBeDisabled();
});
