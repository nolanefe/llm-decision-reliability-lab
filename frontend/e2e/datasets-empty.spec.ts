import { expect, test } from "@playwright/test";

// Runs against the "datasets-empty" project: a real backend with a
// migrated but otherwise empty database (see playwright.config.ts),
// so this exercises the genuine empty-state response, not a mock.
test.describe("Datasets page (empty backend)", () => {
  test("shows readable empty-state messaging for both sections", async ({ page }) => {
    await page.goto("/datasets");

    await expect(page.getByRole("heading", { name: "Evaluation data" })).toBeVisible();
    await expect(page.getByText("No dataset items", { exact: true })).toBeVisible();
    await expect(
      page.getByText("No dataset items are seeded in this backend yet."),
    ).toBeVisible();
    await expect(page.getByText("No prompt versions", { exact: true })).toBeVisible();
    await expect(
      page.getByText("No prompt versions are seeded in this backend yet."),
    ).toBeVisible();
  });
});
