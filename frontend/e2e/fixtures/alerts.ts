import type { Locator, Page } from "@playwright/test";

/**
 * Next.js always renders an empty `role="alert"` route announcer
 * (`#__next-route-announcer__`) for accessibility. Exclude it so
 * `getByRole("alert")` resolves to the app's actual ErrorState banner.
 */
export function getErrorAlert(page: Page): Locator {
  return page.locator('[role="alert"]:not(#__next-route-announcer__)');
}
