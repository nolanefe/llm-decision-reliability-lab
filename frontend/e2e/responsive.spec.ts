import { expect, test } from "@playwright/test";
import { SEEDED_COMPLETED_EXPERIMENT_NAME } from "./fixtures/backend";
import { mockCompletedExperimentApis } from "./fixtures/completed-experiment";
import { expectNoHorizontalOverflow, MOBILE_VIEWPORT } from "./fixtures/viewport";

test.describe("Responsive smoke checks", () => {
  test.use({ viewport: MOBILE_VIEWPORT });

  test("homepage has no page-level horizontal overflow at ~375px", async ({ page }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { level: 1, name: "LLM Decision Reliability Lab" }),
    ).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });

  test("new experiment form has no page-level horizontal overflow at ~375px", async ({
    page,
  }) => {
    await page.goto("/experiments/new");
    await expect(page.getByRole("heading", { name: "Create experiment" })).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });

  test("completed experiment page has no page-level horizontal overflow at ~375px", async ({
    page,
  }) => {
    await page.goto("/experiments");
    const link = page.getByRole("link", { name: SEEDED_COMPLETED_EXPERIMENT_NAME });
    const href = await link.getAttribute("href");
    const match = href?.match(/\/experiments\/(\d+)/);
    if (!match) throw new Error(`Could not resolve experiment id from href: ${href}`);
    const experimentId = Number(match[1]);

    await mockCompletedExperimentApis(page, experimentId);
    await page.goto(`/experiments/${experimentId}`);
    await expect(
      page.getByRole("heading", { name: SEEDED_COMPLETED_EXPERIMENT_NAME, level: 1 }),
    ).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });
});
