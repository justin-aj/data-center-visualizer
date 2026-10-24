import { readFile } from 'node:fs/promises';

import { expect, test } from '@playwright/test';

test('downloads an attributed PNG matching app state', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Scene ready.')).toBeVisible();
  await page.getByLabel('current').check();

  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download PNG' }).click();
  const download = await downloadPromise;
  const path = await download.path();
  if (!path) throw new Error('PNG download has no saved path.');
  const bytes = await readFile(path);

  expect(download.suggestedFilename()).toBe('data-center-visualizer.png');
  expect([...bytes.subarray(0, 8)]).toEqual([137, 80, 78, 71, 13, 10, 26, 10]);
  const summary = page.locator('[data-testid="export-summary"]');
  await expect(summary).toContainText('current');
  await expect(summary).toContainText('Ground shown flat');
  await expect(summary).toContainText('Synthetic fixture');
});

test('shows a retry message after WebGL context loss', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Scene ready.')).toBeVisible();

  await page.locator('canvas').dispatchEvent('webglcontextlost');

  await expect(page.locator('[data-context-loss-message]')).toContainText(
    'retry the PNG export',
  );
});
