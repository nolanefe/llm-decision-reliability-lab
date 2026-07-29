import { expect, test } from "@playwright/test";

test.describe("Homepage", () => {
  test("renders the project title and purpose", async ({ page }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { level: 1, name: "LLM Decision Reliability Lab" }),
    ).toBeVisible();
    await expect(
      page.getByText(/Compare prompt and model variants on a fixed task/i),
    ).toBeVisible();
  });

  test("navigation links work", async ({ page }) => {
    await page.goto("/");
    const primaryNav = page.getByRole("navigation", { name: "Primary" });

    await primaryNav.getByRole("link", { name: "Datasets", exact: true }).click();
    await expect(page).toHaveURL(/\/datasets$/);
    await expect(page.getByRole("heading", { name: "Evaluation data" })).toBeVisible();

    await primaryNav.getByRole("link", { name: "Experiments", exact: true }).click();
    await expect(page).toHaveURL(/\/experiments$/);
    await expect(page.getByRole("heading", { name: "Experiments" })).toBeVisible();

    await page.getByRole("link", { name: "LLM Decision Reliability Lab" }).click();
    await expect(page).toHaveURL(/\/$/);
    await expect(
      page.getByRole("heading", { level: 1, name: "LLM Decision Reliability Lab" }),
    ).toBeVisible();
  });
});
