import { existsSync, readFileSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Page } from '@playwright/test';

// Layout of the Networks page in the built web UI bundle (run `npm run build`
// first; CI builds before the e2e step). The API is mocked.
const WEBUI_DIR = fileURLToPath(
  new URL('../../custom_components/unifi_people_pointer/webui/', import.meta.url),
);
const ORIGIN = 'http://upp.test:8765';
const TYPES: Record<string, string> = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
};

const NETWORKS = {
  selected: [],
  include_unassigned_clients: true,
  active: false,
  unassigned_clients: 1,
  networks: [
    {
      key: 'network:net-main',
      kind: 'unifi',
      name: 'Main',
      vlan: null,
      subnets: ['192.0.2.0/24', '2001:db8:1:0:1234:5678:9abc:0/112'],
      clients: 23,
      selected: false,
    },
    {
      key: 'network:net-iot',
      kind: 'unifi',
      name: 'Internet of Things with a long network name',
      vlan: 20,
      subnets: ['203.0.113.0/24'],
      clients: 1,
      selected: false,
    },
    {
      key: '198.51.100.0/24',
      kind: 'observed',
      name: '198.51.100.0/24',
      vlan: null,
      subnets: ['198.51.100.0/24'],
      clients: 4,
      selected: false,
    },
  ],
};

const VIEWPORTS = [
  { name: 'desktop', width: 1906, height: 995 },
  { name: 'tablet', width: 820, height: 1180 },
  { name: 'phone', width: 390, height: 844 },
];

// The mocked server: keeps the last saved selection like the integration does.
function networksState(selected: string[]) {
  const known = NETWORKS.networks.map((n) => n.key);
  const custom = selected
    .filter((key) => !known.includes(key))
    .map((key) => ({ key, kind: 'custom', name: key, vlan: null, subnets: [key], clients: 0 }));
  return {
    ...NETWORKS,
    selected,
    active: selected.length > 0,
    networks: [...NETWORKS.networks, ...custom].map((n) => ({ ...n, selected: selected.includes(n.key) })),
  };
}

async function openNetworks(page: Page, puts: unknown[]) {
  let saved: string[] = [];
  await page.route(`${ORIGIN}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path === '/api/networks') {
      if (request.method() === 'PUT') {
        const body = request.postDataJSON();
        puts.push(body);
        saved = body.networks as string[];
      }
      return route.fulfill({ json: networksState(saved) });
    }
    if (path.startsWith('/api/')) return route.fulfill({ json: [] });
    const file = normalize(join(WEBUI_DIR, path === '/' ? 'index.html' : path));
    if (!file.startsWith(WEBUI_DIR) || !existsSync(file)) {
      return route.fulfill({ status: 404, body: 'not found' });
    }
    return route.fulfill({
      contentType: TYPES[extname(file)] || 'application/octet-stream',
      body: readFileSync(file),
    });
  });
  await page.addInitScript(() => localStorage.setItem('upp-ha-token', 'test-token'));
  await page.goto(`${ORIGIN}/#/networks`);
  await expect(page.locator('.network-row')).toHaveCount(4);
}

for (const viewport of VIEWPORTS) {
  test(`networks page fits the window (${viewport.name} ${viewport.width}x${viewport.height})`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await openNetworks(page, []);

    // No horizontal page scroll.
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBe(viewport.width);

    const main = (await page.locator('.main-content').boundingBox())!;
    const rows = page.locator('.network-row');
    const checkboxes = page.locator('.network-row input[type="checkbox"]');
    const counts = page.locator('.network-count');
    const first = (await rows.first().boundingBox())!;
    const firstBox = (await checkboxes.first().boundingBox())!;
    const firstCount = (await counts.first().boundingBox())!;
    for (let i = 0; i < 4; i += 1) {
      const row = (await rows.nth(i).boundingBox())!;
      const box = (await checkboxes.nth(i).boundingBox())!;
      const count = (await counts.nth(i).boundingBox())!;
      // Rows stay inside the content column and share their left/right edges.
      expect(row.x).toBeGreaterThanOrEqual(main.x);
      expect(row.x + row.width).toBeLessThanOrEqual(main.x + main.width);
      expect(row.x).toBe(first.x);
      expect(row.width).toBe(first.width);
      // Checkboxes in one column, centered on their row; counts right-aligned.
      expect(box.x).toBe(firstBox.x);
      expect(box.width).toBe(20);
      expect(box.height).toBe(20);
      expect(Math.abs(box.y + box.height / 2 - (row.y + row.height / 2))).toBeLessThanOrEqual(1);
      expect(count.x + count.width).toBeCloseTo(firstCount.x + firstCount.width, 0);
    }

    // Subnet input and its button share one line inside the card.
    const input = (await page.locator('#cidr-input').boundingBox())!;
    const add = (await page.getByRole('button', { name: 'Add' }).boundingBox())!;
    expect(add.y).toBe(input.y);
    expect(add.height).toBeCloseTo(input.height, 0);
    expect(add.x).toBeGreaterThan(input.x + input.width);
    expect(add.x + add.width).toBeLessThanOrEqual(first.x + first.width);

    // Every navigation tab is reachable without scrolling sideways.
    for (const link of await page.locator('.navbar-menu a').all()) {
      const box = (await link.boundingBox())!;
      expect(box.x + box.width).toBeLessThanOrEqual(viewport.width);
    }

    if (process.env.UPP_SHOTS) {
      await page.screenshot({
        path: join(process.env.UPP_SHOTS, `networks-${viewport.width}.png`),
        fullPage: true,
      });
    }
  });
}

test('invalid subnet shows an error, a valid one is added and saved', async ({ page }) => {
  const puts: unknown[] = [];
  await page.setViewportSize({ width: 820, height: 1180 });
  await openNetworks(page, puts);

  const input = page.locator('#cidr-input');
  await input.fill('192.0.2.0/33');
  await page.getByRole('button', { name: 'Add' }).click();
  await expect(page.locator('.cidr-form .field-error')).toHaveText(
    'The prefix length must be between 0 and 32.',
  );
  await expect(input).toHaveAttribute('aria-invalid', 'true');

  await input.fill('192.0.2.17/24');
  await page.getByRole('button', { name: 'Add' }).click();
  await expect(page.locator('.cidr-form .field-error')).toHaveCount(0);
  const added = page.locator('.network-row', { hasText: '192.0.2.0/24' }).last();
  await expect(added.locator('.network-count')).toHaveText('new');
  await expect(added.locator('input')).toBeChecked();

  await page.locator('.network-row', { hasText: '198.51.100.0/24' }).locator('input').check();
  await page.getByRole('button', { name: 'Save' }).click();
  await expect(page.locator('.save-ok')).toBeVisible();
  expect(puts).toEqual([
    { networks: ['192.0.2.0/24', '198.51.100.0/24'], include_unassigned_clients: true },
  ]);
  await expect(page.locator('.filter-status-on')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save' })).toBeDisabled();
  await expect(added.locator('.network-count')).toHaveText('0 clients');
  await expect(added.locator('input')).toBeChecked();
  // Filled and outlined action buttons line up.
  const saveBox = (await page.getByRole('button', { name: 'Save' }).boundingBox())!;
  const clearBox = (await page.getByRole('button', { name: 'Clear selection' }).boundingBox())!;
  expect(clearBox.y).toBe(saveBox.y);
  expect(clearBox.height).toBe(saveBox.height);
  if (process.env.UPP_SHOTS) {
    await page.screenshot({ path: join(process.env.UPP_SHOTS, 'networks-saved-820.png'), fullPage: true });
  }
});
