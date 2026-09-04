import { expect, test } from '@playwright/test';

test('hash navigation works without horizontal overflow', async ({ page }) => {
  await page.goto('/#news');
  await expect(page.locator('nav')).toBeVisible();
  await page.getByRole('link', { name: /games/i }).click();
  await expect(page).toHaveURL(/#games$/);
  await page.getByRole('tab', { name: 'Strands' }).click();
  await expect(page.locator('.strands')).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBe(false);
});

test('Strands pointer path updates and page remains fixed during drag', async ({ page }) => {
  await page.goto('/#games');
  await page.getByRole('tab', { name: 'Strands' }).click();
  const cells = page.locator('.strand-cell');
  if (await cells.count() > 1) {
    const first = await cells.nth(0).boundingBox(); const second = await cells.nth(1).boundingBox();
    if (first && second) {
      const before = await page.evaluate(() => scrollY);
      await page.mouse.move(first.x + first.width / 2, first.y + first.height / 2);
      await page.mouse.down();
      await page.mouse.move(second.x + second.width / 2, second.y + second.height / 2, { steps: 3 });
      await expect(page.locator('.strand-word')).not.toBeEmpty();
      expect(await page.evaluate(() => scrollY)).toBe(before);
      await page.mouse.up();
    }
  }
});
