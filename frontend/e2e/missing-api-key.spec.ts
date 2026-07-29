import { expect, test } from "@playwright/test";
import { getErrorAlert } from "./fixtures/alerts";
import { createDraftExperiment, PRIMARY_BACKEND_URL } from "./fixtures/backend";

// The primary backend is always started with OPENAI_API_KEY unset (see
// playwright.config.ts), so a confirmed execution genuinely reaches the
// real executor and gets a real 503 -- no mocking involved, and OpenAI is
// never called.
test.describe("Missing API key behavior", () => {
  test("confirmed execution gets a readable 503 and the experiment stays draft", async ({
    page,
    request,
  }) => {
    const experiment = await createDraftExperiment(request, "Missing key check");

    await page.goto(`/experiments/${experiment.id}`);
    await page.getByRole("button", { name: "Execute experiment" }).click();
    await page.getByRole("dialog").waitFor({ state: "visible" });
    await page.getByRole("button", { name: "Execute", exact: true }).click();

    const alert = getErrorAlert(page);
    await expect(alert).toContainText("Execution failed");
    await expect(alert).toContainText("The LLM provider is unavailable");
    await expect(alert).toContainText("OPENAI_API_KEY is not configured");

    // Experiment remains draft: reload and confirm via a fresh server render.
    await page.reload();
    await expect(page.getByText("Status: draft")).toBeVisible();
    await expect(page.getByRole("button", { name: "Execute experiment" })).toBeVisible();

    const runsResponse = await request.get(
      `${PRIMARY_BACKEND_URL}/api/v1/experiments/${experiment.id}/runs`,
    );
    expect(runsResponse.ok()).toBe(true);
    expect(await runsResponse.json()).toEqual([]);
  });
});
