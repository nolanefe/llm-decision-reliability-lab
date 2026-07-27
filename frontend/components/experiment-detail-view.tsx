"use client";

import { useEffect, useState } from "react";
import type { Experiment, ExperimentMetrics, FailureEntry, Run } from "@/lib/types";
import {
  ApiError,
  executeExperiment,
  getExperimentFailures,
  getExperimentMetrics,
  listExperimentRuns,
} from "@/lib/api";
import { formatDateTime, formatDecimal, formatLatency, formatUsd, formatPercent } from "@/lib/format";
import { StatusBadge } from "./status-badge";
import { LoadingState } from "./loading-state";
import { ErrorState } from "./error-state";
import { MetricCard } from "./metric-card";
import { RecommendationPanel } from "./recommendation-panel";
import { VariantComparisonTable } from "./variant-comparison-table";
import { RunTable } from "./run-table";
import { FailureExplorer } from "./failure-explorer";
import { ConfirmationDialog } from "./confirmation-dialog";

interface Results {
  metrics: ExperimentMetrics;
  runs: Run[];
  failures: FailureEntry[];
}

function mapExecuteError(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 409:
        return `This experiment cannot be executed right now: ${error.message}`;
      case 422:
        return `This experiment's configuration is invalid: ${error.message}`;
      case 503:
        return `The LLM provider is unavailable: ${error.message}`;
      case 0:
        return error.message;
      default:
        return `Execution failed (status ${error.status}): ${error.message}`;
    }
  }
  return "Failed to execute the experiment.";
}

export function ExperimentDetailView({ experiment: initial }: { experiment: Experiment }) {
  const [experiment, setExperiment] = useState(initial);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [executeError, setExecuteError] = useState<string | null>(null);

  const [results, setResults] = useState<Results | null>(null);
  const [resultsError, setResultsError] = useState<string | null>(null);

  const plannedRunCount =
    experiment.dataset_item_ids.length *
    experiment.prompt_version_ids.length *
    experiment.model_names.length *
    experiment.repeat_count;

  useEffect(() => {
    if (experiment.status !== "completed") return;
    let cancelled = false;
    Promise.all([
      getExperimentMetrics(experiment.id),
      listExperimentRuns(experiment.id),
      getExperimentFailures(experiment.id),
    ])
      .then(([metrics, runs, failures]) => {
        if (cancelled) return;
        setResults({ metrics, runs, failures });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setResultsError(
          error instanceof ApiError ? error.message : "Failed to load results.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [experiment.status, experiment.id]);

  async function handleExecute() {
    if (executing) return;
    setConfirmOpen(false);
    setExecuting(true);
    setExecuteError(null);
    try {
      const summary = await executeExperiment(experiment.id);
      setExperiment((current) => ({
        ...current,
        status: summary.status,
        started_at: summary.started_at,
        completed_at: summary.completed_at,
      }));
    } catch (error) {
      setExecuteError(mapExecuteError(error));
    } finally {
      setExecuting(false);
    }
  }

  const recommendedVariant = results?.metrics.recommendation
    ? results.metrics.variant_metrics.find(
        (variant) =>
          variant.prompt_version_id ===
            results.metrics.recommendation!.recommended_prompt_version_id &&
          variant.model_name === results.metrics.recommendation!.recommended_model_name,
      ) ?? null
    : null;

  const bestReliabilityScore = results
    ? results.metrics.variant_metrics.reduce<number | null>((best, variant) => {
        if (variant.average_reliability_score === null) return best;
        if (best === null) return variant.average_reliability_score;
        return Math.max(best, variant.average_reliability_score);
      }, null)
    : null;

  return (
    <div className="flex flex-col gap-8">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold text-slate-900">{experiment.name}</h1>
          <StatusBadge status={experiment.status} />
        </div>
        <p className="mt-1 text-sm text-slate-500">Experiment #{experiment.id}</p>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Configuration
        </h2>
        <dl className="mt-3 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-slate-500">Dataset items</dt>
            <dd className="font-medium text-slate-900">
              {experiment.dataset_item_ids.length}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Prompt versions</dt>
            <dd className="font-medium text-slate-900">
              {experiment.prompt_version_ids.length}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Models</dt>
            <dd className="font-medium text-slate-900">
              {experiment.model_names.join(", ")}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Repeat count</dt>
            <dd className="font-medium text-slate-900">{experiment.repeat_count}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Planned runs</dt>
            <dd className="font-medium text-slate-900">{plannedRunCount}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Created</dt>
            <dd className="font-medium text-slate-900">
              {formatDateTime(experiment.created_at)}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Started</dt>
            <dd className="font-medium text-slate-900">
              {formatDateTime(experiment.started_at)}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Completed</dt>
            <dd className="font-medium text-slate-900">
              {formatDateTime(experiment.completed_at)}
            </dd>
          </div>
        </dl>
      </section>

      {experiment.status === "draft" ? (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-amber-800">
            Execute experiment
          </h2>
          <p className="mt-2 text-sm text-amber-900">
            Executing this experiment makes {plannedRunCount} real, paid OpenAI
            API calls. Execution runs synchronously in the backend — the page
            will wait until every run is complete before showing results.
          </p>
          {executing ? (
            <p className="mt-3 text-sm font-medium text-amber-900">
              Executing… this can take a while for larger plans. Please don&apos;t
              close this tab.
            </p>
          ) : null}
          {executeError ? (
            <div className="mt-3">
              <ErrorState title="Execution failed" message={executeError} />
            </div>
          ) : null}
          <button
            type="button"
            disabled={executing}
            onClick={() => setConfirmOpen(true)}
            className="mt-4 rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900"
          >
            {executing ? "Executing…" : "Execute experiment"}
          </button>
          <ConfirmationDialog
            open={confirmOpen}
            title="Execute this experiment?"
            description={`This makes ${plannedRunCount} real, paid OpenAI API calls and cannot be undone. Continue?`}
            confirmLabel="Execute"
            onConfirm={handleExecute}
            onCancel={() => setConfirmOpen(false)}
          />
        </section>
      ) : null}

      {experiment.status === "failed" ? (
        <ErrorState
          title="Experiment failed"
          message="This experiment's execution failed. Check the backend logs for details."
        />
      ) : null}

      {experiment.status === "pending" || experiment.status === "running" ? (
        <LoadingState label="This experiment is currently executing." />
      ) : null}

      {experiment.status === "completed" ? (
        <div className="flex flex-col gap-8">
          {!results && !resultsError ? <LoadingState label="Loading results…" /> : null}
          {resultsError ? (
            <ErrorState title="Could not load results" message={resultsError} />
          ) : null}

          {results ? (
            <>
              <section>
                <h2 className="text-lg font-semibold text-slate-900">
                  Execution summary
                </h2>
                <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <MetricCard label="Total runs" value={String(results.metrics.total_runs)} />
                  <MetricCard
                    label="Best avg reliability"
                    value={formatDecimal(bestReliabilityScore)}
                  />
                  <MetricCard
                    label="Recommended schema validity"
                    value={formatPercent(recommendedVariant?.schema_validity_rate ?? null)}
                  />
                  <MetricCard
                    label="Recommended total cost"
                    value={formatUsd(results.metrics.recommendation?.estimated_cost_usd ?? null)}
                  />
                  <MetricCard
                    label="Recommended avg latency"
                    value={formatLatency(results.metrics.recommendation?.average_latency_ms ?? null)}
                  />
                </div>
              </section>

              <section>
                <h2 className="text-lg font-semibold text-slate-900">Recommendation</h2>
                <div className="mt-3">
                  <RecommendationPanel recommendation={results.metrics.recommendation} />
                </div>
              </section>

              <section>
                <h2 className="text-lg font-semibold text-slate-900">
                  Variant comparison
                </h2>
                <div className="mt-3">
                  <VariantComparisonTable variants={results.metrics.variant_metrics} />
                </div>
              </section>

              <section>
                <h2 className="text-lg font-semibold text-slate-900">
                  Runs ({results.runs.length})
                </h2>
                <div className="mt-3">
                  <RunTable runs={results.runs} />
                </div>
              </section>

              <section>
                <h2 className="text-lg font-semibold text-slate-900">
                  Failure explorer ({results.failures.length})
                </h2>
                <div className="mt-3">
                  <FailureExplorer failures={results.failures} />
                </div>
              </section>
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
