import { expect, test } from "@playwright/test";
import { getErrorAlert } from "./fixtures/alerts";

// Runs against the "datasets-error" project: a frontend pointed at a
// backend port nothing listens on (see playwright.config.ts), so the
// server-side fetch genuinely fails and the route's error.tsx boundary
// renders. No mocking involved -- this is a real connection failure.
//
// This is a production build, so Next.js redacts the original thrown
// error message (by design, to avoid leaking server internals) and
// replaces it with a generic message. The hardcoded title from error.tsx
// still comes through, so the result is still readable, just not the
// literal ApiError text.
test.describe("Datasets page (unreachable backend)", () => {
  test("shows a readable error instead of crashing", async ({ page }) => {
    await page.goto("/datasets");

    const alert = getErrorAlert(page);
    await expect(alert).toBeVisible();
    await expect(alert).toContainText("Could not load evaluation data");
    await expect(alert).not.toBeEmpty();
  });
});
