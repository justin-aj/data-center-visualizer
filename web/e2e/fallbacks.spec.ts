import { expect, test } from '@playwright/test';

import manifestContextOnly from '../../contracts/fixtures/synthetic-site/manifest.context-only.json' with { type: 'json' };

test('shows loading before the package is ready', async ({ page }) => {
  await page.route(
    '**/fixtures/synthetic-site/manifest.json',
    async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 250));
      await route.continue();
    },
  );
  await page.goto('/?fixture=synthetic-site');
  await expect(page.getByText(/loading manifest/i)).toBeVisible();
  await expect(page.getByText('Scene ready.')).toBeVisible();
});

test('keeps proposal geometry when context fails', async ({ page }) => {
  await page.route('**/fixtures/synthetic-site/context.json', (route) =>
    route.fulfill({ status: 503, body: 'unavailable' }),
  );
  await page.goto('/?fixture=synthetic-site');

  await expect(
    page.getByText('Neighborhood context unavailable. Proposal loaded.'),
  ).toBeVisible();
  await expect(page.locator('[data-fallback="context-missing"]')).toBeVisible();
  await expect(page.locator('canvas')).toBeVisible();
});

test('shows the static scene and inventory without WebGL', async ({ page }) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (
      this: HTMLCanvasElement,
      kind,
      options,
    ) {
      if (String(kind).startsWith('webgl') || kind === 'experimental-webgl')
        return null;
      return original.call(this, kind, options);
    } as typeof original;
  });
  await page.goto('/?fixture=synthetic-site');

  const fallback = page.locator('[data-fallback="no-webgl"]');
  await expect(fallback).toBeVisible();
  await expect(fallback.getByRole('img')).toBeVisible();
  await expect(fallback.getByRole('table')).toBeVisible();
});

test('keeps unknown and estimated states distinct', async ({ page }) => {
  await page.goto('/?fixture=synthetic-site');
  const inventory = page.getByRole('table', { name: 'Visible scene features' });
  await expect(inventory).toContainText('height unknown');
  await expect(inventory).toContainText('height estimated');
});

test('uses context-only controls, inventory, export, and fallback wording', async ({
  page,
}) => {
  await page.route('**/fixtures/synthetic-site/manifest.json', (route) =>
    route.fulfill({ json: manifestContextOnly }),
  );
  await page.route('**/fixtures/synthetic-site/proposal.json', (route) =>
    route.fulfill({ json: { features: [] } }),
  );
  await page.goto('/?fixture=synthetic-site');

  await expect(
    page.getByText('Context-only scene ready. No proposal is shown.'),
  ).toBeVisible();
  await expect(page.getByRole('group', { name: 'View' })).toHaveCount(0);
  await expect(
    page.getByRole('group', { name: 'Visible categories' }),
  ).toHaveCount(0);
  await expect(
    page.getByRole('table', { name: 'Visible context layers' }),
  ).toBeVisible();

  const pending = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download PNG' }).click();
  await pending;
  const summary = page.locator('[data-testid="export-summary"]');
  await expect(summary).toContainText('context only');
  await expect(summary).toContainText('No proposal is shown.');
  await expect(summary).not.toContainText('Confidence:');
});

test('uses truthful context-only no-WebGL fallback wording', async ({
  page,
}) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (
      this: HTMLCanvasElement,
      kind,
      options,
    ) {
      if (String(kind).startsWith('webgl') || kind === 'experimental-webgl')
        return null;
      return original.call(this, kind, options);
    } as typeof original;
  });
  await page.route('**/fixtures/synthetic-site/manifest.json', (route) =>
    route.fulfill({ json: manifestContextOnly }),
  );
  await page.route('**/fixtures/synthetic-site/proposal.json', (route) =>
    route.fulfill({ json: { features: [] } }),
  );
  await page.goto('/?fixture=synthetic-site');

  const fallback = page.locator('[data-fallback="no-webgl"]');
  await expect(fallback).toContainText('context only and no proposal');
  await expect(
    fallback.getByRole('table', { name: 'Visible context layers' }),
  ).toBeVisible();
  await expect(fallback.getByRole('img')).toHaveCount(0);
});
