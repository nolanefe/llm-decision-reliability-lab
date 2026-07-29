import { expect, test } from "@playwright/test";
import { SEEDED_COMPLETED_EXPERIMENT_NAME } from "./fixtures/backend";

test.describe("Experiments list", () => {
  test("renders an experiment and links to its detail page", async ({ page }) => {
    await page.goto("/experiments");
    await expect(page.getByRole("heading", { name: "Experiments", level: 1 })).toBeVisible();

    const link = page.getByRole("link", { name: SEEDED_COMPLETED_EXPERIMENT_NAME });
    await expect(link).toBeVisible();
    await link.click();

    await expect(page).toHaveURL(/\/experiments\/\d+$/);
    await expect(
      page.getByRole("heading", { name: SEEDED_COMPLETED_EXPERIMENT_NAME, level: 1 }),
    ).toBeVisible();
  });
});
