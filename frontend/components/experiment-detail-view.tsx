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
import { ReliabilityComparison } from "./reliability-comparison";
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
    <div className="page-stack">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--color-text-primary)]">
            {experiment.name}
          </h1>
          <StatusBadge status={experiment.status} />
        </div>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Experiment #{experiment.id}
        </p>
      </div>

      <section className="card card-padded" aria-labelledby="config-heading">
        <h2 id="config-heading" className="card-section-title">
          Configuration
        </h2>
        <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-4 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-[var(--color-text-muted)]">Dataset items</dt>
            <dd className="mt-0.5 font-medium tabular-nums text-[var(--color-text-primary)]">
              {experiment.dataset_item_ids.length}
            </dd>
          </div>
          <div>
            <dt className="text-[var(--color-text-muted)]">Prompt versions</dt>
            <dd className="mt-0.5 font-medium tabular-nums text-[var(--color-text-primary)]">
              {experiment.prompt_version_ids.length}
            </dd>
          </div>
          <div>
            <dt className="text-[var(--color-text-muted)]">Models</dt>
            <dd className="mt-0.5 font-medium text-[var(--color-text-primary)]">
              {experiment.model_names.join(", ")}
            </dd>
          </div>
          <div>
            <dt className="text-[var(--color-text-muted)]">Repeat count</dt>
            <dd className="mt-0.5 font-medium tabular-nums text-[var(--color-text-primary)]">
              {experiment.repeat_count}
            </dd>
          </div>
          <div>
            <dt className="text-[var(--color-text-muted)]">Planned runs</dt>
            <dd className="mt-0.5 font-semibold tabular-nums text-[var(--color-accent)]">
              {plannedRunCount}
            </dd>
          </div>
          <div>
            <dt className="text-[var(--color-text-muted)]">Created</dt>
            <dd className="mt-0.5 font-medium text-[var(--color-text-primary)]">
              {formatDateTime(experiment.created_at)}
            </dd>
          </div>
          <div>
            <dt className="text-[var(--color-text-muted)]">Started</dt>
            <dd className="mt-0.5 font-medium text-[var(--color-text-primary)]">
              {formatDateTime(experiment.started_at)}
            </dd>
          </div>
          <div>
            <dt className="text-[var(--color-text-muted)]">Completed</dt>
            <dd className="mt-0.5 font-medium text-[var(--color-text-primary)]">
              {formatDateTime(experiment.completed_at)}
            </dd>
          </div>
        </dl>
      </section>

      {experiment.status === "draft" ? (
        <section
          className="rounded-[var(--radius-lg)] border border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] p-[var(--card-padding)]"
          aria-labelledby="execute-heading"
        >
          <h2
            id="execute-heading"
            className="text-sm font-semibold uppercase tracking-wide text-[var(--color-warning-text)]"
          >
            Execute experiment
          </h2>
          <div className="mt-3 space-y-2 text-sm leading-relaxed text-[var(--color-warning-text)]">
            <p>
              Execution makes{" "}
              <strong className="font-semibold">{plannedRunCount}</strong> real,
              paid OpenAI API calls.
            </p>
            <p>
              Execution is synchronous — this page waits until every run
              completes before showing results.
            </p>
            <p>Confirmation is required before any calls are made.</p>
          </div>
          {executing ? (
            <LoadingState label="Executing… this can take a while for larger plans. Please don't close this tab." />
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
            className="btn btn-primary mt-4"
          >
            {executing ? "Executing…" : "Execute experiment"}
          </button>
          <ConfirmationDialog
            open={confirmOpen}
            title="Execute this experiment?"
            description={`This will make ${plannedRunCount} real, paid OpenAI API calls synchronously. This action cannot be undone.`}
            confirmLabel="Execute"
            cancelLabel="Cancel"
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
        <div className="flex flex-col gap-[var(--section-gap)]">
          {!results && !resultsError ? <LoadingState label="Loading results…" /> : null}
          {resultsError ? (
            <ErrorState title="Could not load results" message={resultsError} />
          ) : null}

          {results ? (
            <>
              <section aria-labelledby="summary-heading">
                <h2
                  id="summary-heading"
                  className="text-lg font-semibold text-[var(--color-text-primary)]"
                >
                  Executive summary
                </h2>
                <div className="metric-grid mt-4">
                  <MetricCard
                    label="Total runs"
                    value={String(results.metrics.total_runs)}
                    highlight
                  />
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

              <section aria-labelledby="recommendation-heading">
                <h2
                  id="recommendation-heading"
                  className="text-lg font-semibold text-[var(--color-text-primary)]"
                >
                  Recommended variant
                </h2>
                <div className="mt-4">
                  <RecommendationPanel recommendation={results.metrics.recommendation} />
                </div>
              </section>

              <section aria-labelledby="reliability-heading">
                <h2
                  id="reliability-heading"
                  className="text-lg font-semibold text-[var(--color-text-primary)]"
                >
                  Reliability comparison
                </h2>
                <div className="card card-padded mt-4">
                  <ReliabilityComparison variants={results.metrics.variant_metrics} />
                </div>
              </section>

              <section aria-labelledby="variant-heading">
                <h2
                  id="variant-heading"
                  className="text-lg font-semibold text-[var(--color-text-primary)]"
                >
                  Full variant comparison
                </h2>
                <div className="mt-4">
                  <VariantComparisonTable variants={results.metrics.variant_metrics} />
                </div>
              </section>

              <section aria-labelledby="runs-heading">
                <h2
                  id="runs-heading"
                  className="text-lg font-semibold text-[var(--color-text-primary)]"
                >
                  Run details
                  <span className="ml-2 text-base font-normal text-[var(--color-text-muted)]">
                    ({results.runs.length})
                  </span>
                </h2>
                <div className="mt-4">
                  <RunTable runs={results.runs} />
                </div>
              </section>

              <section aria-labelledby="failures-heading">
                <h2
                  id="failures-heading"
                  className="text-lg font-semibold text-[var(--color-text-primary)]"
                >
                  Failure explorer
                  <span className="ml-2 text-base font-normal text-[var(--color-text-muted)]">
                    ({results.failures.length})
                  </span>
                </h2>
                <div className="mt-4">
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
