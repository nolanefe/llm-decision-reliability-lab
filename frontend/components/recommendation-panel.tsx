import type { Recommendation } from "@/lib/types";
import { formatDecimal, formatLatency, formatUsd } from "@/lib/format";

export function RecommendationPanel({
  recommendation,
}: {
  recommendation: Recommendation | null;
}) {
  if (!recommendation) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600">
        No recommendation is available for this experiment yet.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-indigo-700">
        Recommended variant
      </p>
      <p className="mt-1 text-lg font-semibold text-slate-900">
        Prompt version #{recommendation.recommended_prompt_version_id} —{" "}
        {recommendation.recommended_model_name}
      </p>
      <dl className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-slate-500">Reliability score</dt>
          <dd className="font-medium text-slate-900">
            {formatDecimal(recommendation.reliability_score)}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Estimated cost</dt>
          <dd className="font-medium text-slate-900">
            {formatUsd(recommendation.estimated_cost_usd)}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Average latency</dt>
          <dd className="font-medium text-slate-900">
            {formatLatency(recommendation.average_latency_ms)}
          </dd>
        </div>
      </dl>
      <p className="mt-3 text-sm text-slate-700">{recommendation.reason}</p>
      <p className="mt-3 text-xs text-slate-500">
        This is an evaluation recommendation based on the runs in this
        experiment, not proof of production suitability.
      </p>
    </div>
  );
}
