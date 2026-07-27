import type { VariantMetrics } from "@/lib/types";
import { formatDecimal } from "@/lib/format";

function clampReliabilityScore(score: number): number {
  return Math.min(100, Math.max(0, score));
}

export function ReliabilityComparison({
  variants,
}: {
  variants: VariantMetrics[];
}) {
  const withScores = variants.filter(
    (v) => v.average_reliability_score !== null,
  );

  if (withScores.length === 0) {
    return (
      <p className="text-sm text-[var(--color-text-muted)]">
        No reliability scores available for comparison.
      </p>
    );
  }

  return (
    <div>
      {/* Screen-reader accessible text summary */}
      <p className="sr-only">
        Reliability comparison by variant on a 0 to 100 scale, ordered as
        returned by the backend:{" "}
        {withScores
          .map(
            (v) =>
              `${v.prompt_version_name} v${v.prompt_version_version} with ${v.model_name}: ${formatDecimal(v.average_reliability_score)} out of 100`,
          )
          .join("; ")}
      </p>

      <div
        className="reliability-chart"
        role="img"
        aria-label="Horizontal bar chart comparing average reliability scores on a 0 to 100 scale across prompt and model variants"
      >
        {variants.map((variant) => {
          const score = variant.average_reliability_score;
          const label = `${variant.prompt_version_name} v${variant.prompt_version_version} · ${variant.model_name}`;
          const widthPercent =
            score !== null ? clampReliabilityScore(score) : 0;

          return (
            <div
              key={`${variant.prompt_version_id}-${variant.model_name}`}
              className="reliability-bar-row"
              aria-hidden="true"
            >
              <span className="reliability-bar-label truncate" title={label}>
                {label}
              </span>
              <div className="reliability-bar-track">
                {score !== null ? (
                  <div
                    className="reliability-bar-fill"
                    style={{ width: `${widthPercent}%` }}
                  />
                ) : null}
              </div>
              <span className="reliability-bar-value">
                {formatDecimal(score)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
