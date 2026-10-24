import { expect, test } from '@playwright/test';

test('loads the production app', async ({ page }) => {
  await page.goto('/');

  await expect(page).toHaveTitle('Data Center Visualizer');
  await expect(
    page.getByRole('heading', { name: 'Data Center Visualizer' }),
  ).toBeVisible();
  await expect(page.getByText('The 3D scene is being prepared.')).toBeVisible();
});
