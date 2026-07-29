import { expect, test } from "@playwright/test";
import { SEEDED_COMPLETED_EXPERIMENT_NAME } from "./fixtures/backend";
import {
  HIGH_RELIABILITY_SCORE,
  LOW_RELIABILITY_SCORE,
  mockCompletedExperimentApis,
} from "./fixtures/completed-experiment";

async function gotoSeededCompletedExperiment(page: import("@playwright/test").Page) {
  // The experiment record itself (status=completed) is server-rendered
  // from the real seeded backend; find its id via the experiments list
  // rather than hardcoding it.
  await page.goto("/experiments");
  const link = page.getByRole("link", { name: SEEDED_COMPLETED_EXPERIMENT_NAME });
  const href = await link.getAttribute("href");
  const match = href?.match(/\/experiments\/(\d+)/);
  if (!match) throw new Error(`Could not resolve experiment id from href: ${href}`);
  const experimentId = Number(match[1]);

  await mockCompletedExperimentApis(page, experimentId);
  await page.goto(`/experiments/${experimentId}`);
  return experimentId;
}

test.describe("Completed experiment", () => {
  test("displays summary metrics, recommendation, reliability bars, tables, and the no-failures state", async ({
    page,
  }) => {
    await gotoSeededCompletedExperiment(page);

    await expect(
      page.getByRole("heading", { name: SEEDED_COMPLETED_EXPERIMENT_NAME, level: 1 }),
    ).toBeVisible();

    // Summary metrics
    await expect(page.getByRole("heading", { name: "Executive summary" })).toBeVisible();
    const totalRunsCard = page.locator(".metric-grid > div", { hasText: "Total runs" });
    await expect(totalRunsCard).toContainText("4");

    // Recommendation
    await expect(page.getByRole("heading", { name: "Recommended variant" })).toBeVisible();
    await expect(page.getByText("Prompt version #1")).toBeVisible();
    await expect(
      page.getByText("Highest average reliability score with full schema validity."),
    ).toBeVisible();

    // Reliability bars: verify exact widths for both variants.
    const chart = page.getByRole("img", {
      name: "Horizontal bar chart comparing average reliability scores on a 0 to 100 scale across prompt and model variants",
    });
    await expect(chart).toBeVisible();
    const bars = chart.locator(".reliability-bar-fill");
    await expect(bars).toHaveCount(2);
    const widths = await bars.evaluateAll((elements) =>
      elements.map((element) => (element as HTMLElement).style.width),
    );
    expect(widths).toContain(`${HIGH_RELIABILITY_SCORE}%`);
    expect(widths).toContain(`${LOW_RELIABILITY_SCORE}%`);

    // Variant + run tables
    await expect(page.getByRole("heading", { name: "Full variant comparison" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "e2e-baseline-triage" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "e2e-explicit-criteria-triage" })).toBeVisible();

    await expect(page.getByRole("heading", { name: /Run details/ })).toBeVisible();
    await expect(page.getByRole("cell", { name: "#1" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "#4" })).toBeVisible();

    // No-failures success state
    await expect(page.getByText("No failures detected")).toBeVisible();
    await expect(
      page.getByText(
        "Every run in this experiment produced a schema-valid, correctly labeled result.",
      ),
    ).toBeVisible();
  });
});
