import type { APIRequestContext } from "@playwright/test";

/** Base URL of the seeded "primary" backend (see playwright.config.ts). */
export const PRIMARY_BACKEND_URL = "http://127.0.0.1:8000";

export const SEEDED_COMPLETED_EXPERIMENT_NAME = "Seeded completed experiment";

interface DatasetItemLike {
  id: number;
}
interface PromptVersionLike {
  id: number;
}

/** Reads the fixture dataset items / prompt versions seeded by e2e_seed.py. */
export async function getSeededFixtureIds(request: APIRequestContext): Promise<{
  datasetItemIds: number[];
  promptVersionIds: number[];
}> {
  const [datasetItemsResponse, promptVersionsResponse] = await Promise.all([
    request.get(`${PRIMARY_BACKEND_URL}/api/v1/dataset-items`),
    request.get(`${PRIMARY_BACKEND_URL}/api/v1/prompt-versions`),
  ]);
  const datasetItems = (await datasetItemsResponse.json()) as DatasetItemLike[];
  const promptVersions = (await promptVersionsResponse.json()) as PromptVersionLike[];
  return {
    datasetItemIds: datasetItems.map((item) => item.id),
    promptVersionIds: promptVersions.map((version) => version.id),
  };
}

/**
 * Creates a brand-new draft experiment directly against the real backend
 * (bypassing the UI), so tests that only care about the *detail page*
 * behavior don't depend on the "create experiment" form also being
 * correct. Never touches OpenAI -- this only reaches the create endpoint.
 */
export async function createDraftExperiment(
  request: APIRequestContext,
  namePrefix: string,
): Promise<{ id: number; name: string }> {
  const { datasetItemIds, promptVersionIds } = await getSeededFixtureIds(request);
  const name = `${namePrefix} ${Date.now()}`;
  const response = await request.post(`${PRIMARY_BACKEND_URL}/api/v1/experiments`, {
    data: {
      name,
      dataset_item_ids: datasetItemIds,
      prompt_version_ids: promptVersionIds,
      model_names: ["gpt-5-mini"],
      repeat_count: 1,
    },
  });
  if (!response.ok()) {
    throw new Error(
      `Failed to seed draft experiment via API: ${response.status()} ${await response.text()}`,
    );
  }
  const experiment = (await response.json()) as { id: number; name: string };
  return experiment;
}
