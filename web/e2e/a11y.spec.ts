import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test('supports the main keyboard workflow at 320 pixels', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto('/');
  await expect(page.getByText('Scene ready.')).toBeVisible();
  await expect(
    page.getByRole('table', { name: 'Visible scene features' }),
  ).toBeVisible();

  await page.keyboard.press('Tab');
  await page.keyboard.press('Tab');
  await page.getByLabel('split').focus();
  await page.keyboard.press('Space');
  await expect(page.getByText('split view.')).toBeVisible();
  await page.getByLabel('generator').focus();
  await page.keyboard.press('Space');
  await expect(page.getByText('generator hidden.')).toBeAttached();
  await page.locator('canvas').focus();
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('+');
  await page.keyboard.press(']');
  await expect(page.locator('canvas')).toBeVisible();
});

test('has no serious or critical axe findings', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Scene ready.')).toBeVisible();

  const results = await new AxeBuilder({ page }).analyze();
  const severe = results.violations.filter((finding) =>
    ['serious', 'critical'].includes(finding.impact ?? ''),
  );
  expect(severe).toEqual([]);
});
