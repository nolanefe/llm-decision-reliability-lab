import { expect, type Page } from "@playwright/test";

export const MOBILE_VIEWPORT = { width: 375, height: 812 };

/** Fails if the page is wider than its own viewport (page-level horizontal overflow). */
export async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  const { scrollWidth, clientWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
}
