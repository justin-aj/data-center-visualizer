import { expect, test } from '@playwright/test';

test('loads the production app', async ({ page }) => {
  await page.goto('/?fixture=synthetic-site');

  await expect(page).toHaveTitle('Data Center Visualizer');
  await expect(
    page.getByRole('heading', { name: 'Data Center Visualizer' }),
  ).toBeVisible();
  await expect(page.getByText('Scene ready.')).toBeVisible();
});
