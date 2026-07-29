import { expect, test, type Page } from "@playwright/test";
import { getErrorAlert } from "./fixtures/alerts";
import { PRIMARY_BACKEND_URL } from "./fixtures/backend";

async function selectDataset(page: Page) {
  await page.getByRole("checkbox", { name: /e2e-billing-duplicate-charge/ }).check();
  await page.getByRole("checkbox", { name: /e2e-account-locked-out/ }).check();
  await page.getByRole("checkbox", { name: /e2e-baseline-triage/ }).check();
  await page.getByRole("checkbox", { name: /e2e-explicit-criteria-triage/ }).check();
  await page.getByRole("checkbox", { name: "gpt-5-mini" }).check();
  await page.getByRole("checkbox", { name: "gpt-5-nano" }).check();
}

test.describe("New experiment form", () => {
  test("validates required selections before allowing submit", async ({ page }) => {
    await page.goto("/experiments/new");

    await page.getByRole("button", { name: "Create experiment" }).click();
    await expect(getErrorAlert(page)).toContainText("Experiment name is required.");

    await page.locator("#experiment-name").fill("Validation check");
    await page.getByRole("button", { name: "Create experiment" }).click();
    await expect(getErrorAlert(page)).toContainText("Select at least one dataset item.");
  });

  test("calculates the planned run count correctly", async ({ page }) => {
    await page.goto("/experiments/new");
    await selectDataset(page);
    await page.locator("#repeat-count").fill("3");

    // 2 dataset items x 2 prompt versions x 2 models x 3 repeats = 24
    const summary = page.getByRole("complementary", { name: "Planned run summary" });
    await expect(summary).toContainText("24");
  });

  test("disables submission while a create request is in flight", async ({ page }) => {
    await page.goto("/experiments/new");
    await selectDataset(page);
    await page.locator("#experiment-name").fill("Submitting state check");

    await page.route(`${PRIMARY_BACKEND_URL}/api/v1/experiments`, async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 800));
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        headers: { "Access-Control-Allow-Origin": "*" },
        body: JSON.stringify({
          id: 999999,
          name: "Submitting state check",
          status: "draft",
          repeat_count: 1,
          dataset_item_ids: [1, 2],
          prompt_version_ids: [1, 2],
          model_names: ["gpt-5-mini", "gpt-5-nano"],
          created_at: new Date().toISOString(),
          started_at: null,
          completed_at: null,
        }),
      });
    });

    const submitButton = page.getByRole("button", { name: "Create experiment" });
    await submitButton.click();

    const submittingButton = page.getByRole("button", { name: "Creating…" });
    await expect(submittingButton).toBeVisible();
    await expect(submittingButton).toBeDisabled();
  });

  test("displays a readable API validation error", async ({ page }) => {
    await page.goto("/experiments/new");
    await selectDataset(page);
    await page.locator("#experiment-name").fill("API error check");

    await page.route(`${PRIMARY_BACKEND_URL}/api/v1/experiments`, async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }
      await route.fulfill({
        status: 422,
        contentType: "application/json",
        headers: { "Access-Control-Allow-Origin": "*" },
        body: JSON.stringify({ detail: "Unknown dataset_item_ids: [999]" }),
      });
    });

    await page.getByRole("button", { name: "Create experiment" }).click();

    const alert = getErrorAlert(page);
    await expect(alert).toContainText("Could not create experiment");
    await expect(alert).toContainText("Unknown dataset_item_ids: [999]");
  });

  test("successfully redirects to the new experiment after creation", async ({ page }) => {
    const experimentName = `New e2e experiment ${Date.now()}`;
    await page.goto("/experiments/new");
    await selectDataset(page);
    await page.locator("#experiment-name").fill(experimentName);

    await page.getByRole("button", { name: "Create experiment" }).click();

    await expect(page).toHaveURL(/\/experiments\/\d+$/);
    await expect(page.getByRole("heading", { name: experimentName, level: 1 })).toBeVisible();
  });
});
