import { expect, test } from "@playwright/test";
import { createDraftExperiment, PRIMARY_BACKEND_URL } from "./fixtures/backend";

test.describe("Draft experiment detail", () => {
  test("displays configuration, guards auto-execution, and the confirm dialog behaves correctly", async ({
    page,
    request,
  }) => {
    const experiment = await createDraftExperiment(request, "Draft detail check");

    // Execution must only ever happen from an explicit, confirmed click.
    // Fail loudly if anything hits /execute without that.
    let executeCalled = false;
    await page.route(`${PRIMARY_BACKEND_URL}/api/v1/experiments/${experiment.id}/execute`, (route) => {
      executeCalled = true;
      route.abort();
    });

    await page.goto(`/experiments/${experiment.id}`);

    await expect(page.getByRole("heading", { name: experiment.name, level: 1 })).toBeVisible();
    await expect(page.getByText("Status: draft")).toBeVisible();

    // Dataset items: 2, prompt versions: 2, repeat count: 1 => planned runs: 4
    const configSection = page.getByRole("region", { name: "Configuration" });
    const configValues = configSection.locator("dd");
    await expect(configValues.nth(0)).toHaveText("2"); // dataset items
    await expect(configValues.nth(1)).toHaveText("2"); // prompt versions
    await expect(configValues.nth(2)).toHaveText("gpt-5-mini"); // models
    await expect(configValues.nth(3)).toHaveText("1"); // repeat count
    await expect(configValues.nth(4)).toHaveText("4"); // planned runs

    const executeButton = page.getByRole("button", { name: "Execute experiment" });
    await expect(executeButton).toBeVisible();

    const dialog = page.locator("dialog.confirmation-dialog");
    await expect(dialog).toBeHidden();

    await executeButton.click();
    await expect(dialog).toBeVisible();
    await expect(page.getByRole("heading", { name: "Execute this experiment?" })).toBeVisible();

    const cancelButton = page.getByRole("button", { name: "Cancel" });
    await expect(cancelButton).toBeFocused();

    await cancelButton.click();
    await expect(dialog).toBeHidden();

    expect(executeCalled).toBe(false);
  });
});
