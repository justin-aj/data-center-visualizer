import { expect, test } from '@playwright/test';

test('loads the Lowell H2 context-only demo', async ({ page }) => {
  await page.goto('/');

  await expect(
    page.getByRole('heading', { name: 'Data Center Visualizer' }),
  ).toBeVisible();
  await expect(
    page.getByText('Context-only scene ready. No proposal is shown.'),
  ).toBeVisible();
  await expect(page.getByRole('group', { name: 'View' })).toHaveCount(0);
  await expect(
    page.getByRole('group', { name: 'Visible categories' }),
  ).toHaveCount(0);
  const inventory = page.getByRole('table', { name: 'Visible context layers' });
  await expect(inventory).toBeVisible();
  await expect(inventory).toContainText('3319');
  await expect(inventory).toContainText('786');
  await expect(page.locator('canvas')).toBeVisible();
});

test('exports truthful Lowell context-only wording', async ({ page }) => {
  await page.goto('/');
  await expect(
    page.getByText('Context-only scene ready. No proposal is shown.'),
  ).toBeVisible();

  const pending = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download PNG' }).click();
  await pending;
  const summary = page.locator('[data-testid="export-summary"]');
  await expect(summary).toContainText('Lowell Markley Area Context');
  await expect(summary).toContainText('context only');
  await expect(summary).toContainText('No proposal is shown.');
  await expect(summary).not.toContainText('Confidence:');
});
