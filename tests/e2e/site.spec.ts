import { expect, test } from '@playwright/test';

test('hash navigation works without horizontal overflow', async ({ page }) => {
  await page.goto('/#news');
  await expect(page.locator('nav')).toBeVisible();
  await page.getByRole('link', { name: /games/i }).click();
  await expect(page).toHaveURL(/#games$/);
  await page.getByRole('button', { name: 'Daily Mini Crossword' }).click();
  await expect(page.locator('iframe[title="Daily Mini Crossword"]')).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBe(false);
});
