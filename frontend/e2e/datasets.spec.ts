import { expect, test } from "@playwright/test";

test.describe("Datasets page", () => {
  test("renders dataset items and prompt versions", async ({ page }) => {
    await page.goto("/datasets");

    await expect(page.getByRole("heading", { name: "Evaluation data" })).toBeVisible();

    await expect(page.getByRole("heading", { name: "Dataset items" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "e2e-billing-duplicate-charge" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "e2e-account-locked-out" }),
    ).toBeVisible();

    await expect(page.getByRole("heading", { name: "Prompt versions" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "e2e-baseline-triage" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "e2e-explicit-criteria-triage" }),
    ).toBeVisible();
  });
});
