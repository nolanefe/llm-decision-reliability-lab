import type { Page } from "@playwright/test";
import type { ExperimentMetrics, FailureEntry, Run } from "../../lib/types";
import { PRIMARY_BACKEND_URL } from "./backend";

/**
 * Deterministic mock data for the "completed experiment" browser tests.
 *
 * The Experiment record itself (status=completed, config) is server-side
 * rendered from the real seeded backend (see backend/scripts/e2e_seed.py),
 * since Next.js Server Components fetch on the server and can't be
 * intercepted here. Metrics/Runs/Failures, however, are fetched
 * client-side by ExperimentDetailView (a "use client" component), so they
 * can -- and are -- intercepted at the browser network layer below. This
 * gives exact, stable reliability scores (75 and 40) without needing a
 * real LLM provider or a nondeterministic scoring pipeline.
 */

export const HIGH_RELIABILITY_SCORE = 75;
export const LOW_RELIABILITY_SCORE = 40;

export function buildMockMetrics(experimentId: number): ExperimentMetrics {
  return {
    experiment_id: experimentId,
    experiment_name: "Seeded completed experiment",
    status: "completed",
    total_runs: 4,
    variant_metrics: [
      {
        prompt_version_id: 1,
        prompt_version_name: "e2e-baseline-triage",
        prompt_version_version: 1,
        model_name: "gpt-5-mini",
        total_runs: 2,
        completed_runs: 2,
        failed_runs: 0,
        schema_valid_runs: 2,
        schema_validity_rate: 1,
        category_accuracy: 1,
        priority_accuracy: 1,
        average_quality_score: 0.9,
        average_consistency_score: 0.95,
        average_reliability_score: HIGH_RELIABILITY_SCORE,
        average_latency_ms: 850,
        total_prompt_tokens: 200,
        total_completion_tokens: 100,
        total_tokens: 300,
        total_estimated_cost_usd: 0.002,
        failure_count: 0,
      },
      {
        prompt_version_id: 2,
        prompt_version_name: "e2e-explicit-criteria-triage",
        prompt_version_version: 1,
        model_name: "gpt-5-nano",
        total_runs: 2,
        completed_runs: 2,
        failed_runs: 0,
        schema_valid_runs: 2,
        schema_validity_rate: 1,
        category_accuracy: 0.5,
        priority_accuracy: 0.5,
        average_quality_score: 0.6,
        average_consistency_score: 0.5,
        average_reliability_score: LOW_RELIABILITY_SCORE,
        average_latency_ms: 620,
        total_prompt_tokens: 180,
        total_completion_tokens: 90,
        total_tokens: 270,
        total_estimated_cost_usd: 0.0015,
        failure_count: 0,
      },
    ],
    recommendation: {
      recommended_prompt_version_id: 1,
      recommended_model_name: "gpt-5-mini",
      reason: "Highest average reliability score with full schema validity.",
      reliability_score: HIGH_RELIABILITY_SCORE,
      estimated_cost_usd: 0.002,
      average_latency_ms: 850,
    },
  };
}

export function buildMockRuns(experimentId: number): Run[] {
  const base = {
    experiment_id: experimentId,
    status: "completed" as const,
    raw_response: '{"category":"billing","priority":"high","summary":"...","recommended_action":"..."}',
    parsed_output: { category: "billing", priority: "high" },
    error_message: null,
    created_at: "2026-01-01T00:00:00Z",
    completed_at: "2026-01-01T00:00:05Z",
  };
  return [
    {
      ...base,
      id: 1,
      dataset_item_id: 1,
      prompt_version_id: 1,
      model_name: "gpt-5-mini",
      repetition_index: 1,
      latency_ms: 820,
      prompt_tokens: 100,
      completion_tokens: 50,
      total_tokens: 150,
      estimated_cost_usd: 0.001,
      evaluation: {
        id: 1,
        run_id: 1,
        schema_valid: true,
        category_correct: true,
        priority_correct: true,
        quality_score: 0.9,
        consistency_score: 0.95,
        failure_category: null,
        reliability_score: HIGH_RELIABILITY_SCORE,
        notes: null,
        created_at: base.created_at,
      },
    },
    {
      ...base,
      id: 2,
      dataset_item_id: 2,
      prompt_version_id: 1,
      model_name: "gpt-5-mini",
      repetition_index: 1,
      latency_ms: 880,
      prompt_tokens: 100,
      completion_tokens: 50,
      total_tokens: 150,
      estimated_cost_usd: 0.001,
      evaluation: {
        id: 2,
        run_id: 2,
        schema_valid: true,
        category_correct: true,
        priority_correct: true,
        quality_score: 0.9,
        consistency_score: 0.95,
        failure_category: null,
        reliability_score: HIGH_RELIABILITY_SCORE,
        notes: null,
        created_at: base.created_at,
      },
    },
    {
      ...base,
      id: 3,
      dataset_item_id: 1,
      prompt_version_id: 2,
      model_name: "gpt-5-nano",
      repetition_index: 1,
      latency_ms: 610,
      prompt_tokens: 90,
      completion_tokens: 45,
      total_tokens: 135,
      estimated_cost_usd: 0.00075,
      evaluation: {
        id: 3,
        run_id: 3,
        schema_valid: true,
        category_correct: false,
        priority_correct: true,
        quality_score: 0.6,
        consistency_score: 0.5,
        failure_category: null,
        reliability_score: LOW_RELIABILITY_SCORE,
        notes: null,
        created_at: base.created_at,
      },
    },
    {
      ...base,
      id: 4,
      dataset_item_id: 2,
      prompt_version_id: 2,
      model_name: "gpt-5-nano",
      repetition_index: 1,
      latency_ms: 630,
      prompt_tokens: 90,
      completion_tokens: 45,
      total_tokens: 135,
      estimated_cost_usd: 0.00075,
      evaluation: {
        id: 4,
        run_id: 4,
        schema_valid: true,
        category_correct: true,
        priority_correct: false,
        quality_score: 0.6,
        consistency_score: 0.5,
        failure_category: null,
        reliability_score: LOW_RELIABILITY_SCORE,
        notes: null,
        created_at: base.created_at,
      },
    },
  ];
}

/** Empty: this fixture models the "no failures" success state. */
export function buildMockFailures(): FailureEntry[] {
  return [];
}

export async function mockCompletedExperimentApis(
  page: Page,
  experimentId: number,
): Promise<void> {
  const metrics = buildMockMetrics(experimentId);
  const runs = buildMockRuns(experimentId);
  const failures = buildMockFailures();

  await page.route(
    `${PRIMARY_BACKEND_URL}/api/v1/experiments/${experimentId}/metrics`,
    (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        headers: { "Access-Control-Allow-Origin": "*" },
        body: JSON.stringify(metrics),
      }),
  );
  await page.route(
    `${PRIMARY_BACKEND_URL}/api/v1/experiments/${experimentId}/runs`,
    (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        headers: { "Access-Control-Allow-Origin": "*" },
        body: JSON.stringify(runs),
      }),
  );
  await page.route(
    `${PRIMARY_BACKEND_URL}/api/v1/experiments/${experimentId}/failures`,
    (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        headers: { "Access-Control-Allow-Origin": "*" },
        body: JSON.stringify(failures),
      }),
  );
}
