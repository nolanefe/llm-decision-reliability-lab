import type { Recommendation } from "@/lib/types";
import { formatDecimal, formatLatency, formatUsd } from "@/lib/format";

export function RecommendationPanel({
  recommendation,
}: {
  recommendation: Recommendation | null;
}) {
  if (!recommendation) {
    return (
      <div className="card card-padded text-sm text-[var(--color-text-secondary)]">
        No recommendation is available for this experiment yet.
      </div>
    );
  }

  return (
    <div className="card card-padded border-[var(--color-accent-border)] bg-[var(--color-accent-subtle)]">
      <p className="card-section-title text-[var(--color-accent)]">
        Recommended variant
      </p>
      <p className="mt-2 text-lg font-semibold text-[var(--color-text-primary)]">
        Prompt version #{recommendation.recommended_prompt_version_id}
        <span className="mx-2 text-[var(--color-text-muted)]">·</span>
        {recommendation.recommended_model_name}
      </p>
      <dl className="mt-4 grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-[var(--color-text-muted)]">Reliability score</dt>
          <dd className="mt-0.5 font-semibold tabular-nums text-[var(--color-text-primary)]">
            {formatDecimal(recommendation.reliability_score)}
          </dd>
        </div>
        <div>
          <dt className="text-[var(--color-text-muted)]">Estimated cost</dt>
          <dd className="mt-0.5 font-semibold tabular-nums text-[var(--color-text-primary)]">
            {formatUsd(recommendation.estimated_cost_usd)}
          </dd>
        </div>
        <div>
          <dt className="text-[var(--color-text-muted)]">Average latency</dt>
          <dd className="mt-0.5 font-semibold tabular-nums text-[var(--color-text-primary)]">
            {formatLatency(recommendation.average_latency_ms)}
          </dd>
        </div>
      </dl>
      <p className="mt-4 text-sm leading-relaxed text-[var(--color-text-secondary)]">
        {recommendation.reason}
      </p>
      <p className="mt-3 text-xs text-[var(--color-text-muted)]">
        This is an evaluation recommendation based on the runs in this
        experiment, not proof of production suitability.
      </p>
    </div>
  );
}
