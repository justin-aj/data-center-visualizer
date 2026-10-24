import { expect, test } from '@playwright/test';

test('shows loading before the package is ready', async ({ page }) => {
  await page.route(
    '**/fixtures/synthetic-site/manifest.json',
    async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 250));
      await route.continue();
    },
  );
  await page.goto('/');
  await expect(page.getByText(/loading manifest/i)).toBeVisible();
  await expect(page.getByText('Scene ready.')).toBeVisible();
});

test('keeps proposal geometry when context fails', async ({ page }) => {
  await page.route('**/fixtures/synthetic-site/context.json', (route) =>
    route.fulfill({ status: 503, body: 'unavailable' }),
  );
  await page.goto('/');

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
  await page.goto('/');

  const fallback = page.locator('[data-fallback="no-webgl"]');
  await expect(fallback).toBeVisible();
  await expect(fallback.getByRole('img')).toBeVisible();
  await expect(fallback.getByRole('table')).toBeVisible();
});

test('keeps unknown and estimated states distinct', async ({ page }) => {
  await page.goto('/');
  const inventory = page.getByRole('table', { name: 'Visible scene features' });
  await expect(inventory).toContainText('height unknown');
  await expect(inventory).toContainText('height estimated');
});
