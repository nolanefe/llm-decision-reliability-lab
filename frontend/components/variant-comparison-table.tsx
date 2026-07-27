import type { VariantMetrics } from "@/lib/types";
import {
  formatDecimal,
  formatLatency,
  formatNumber,
  formatPercent,
  formatUsd,
} from "@/lib/format";

export function VariantComparisonTable({
  variants,
}: {
  variants: VariantMetrics[];
}) {
  return (
    <div className="table-wrap max-h-[32rem] overflow-y-auto">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Prompt version</th>
            <th scope="col">Model</th>
            <th scope="col" className="num">
              Runs
            </th>
            <th scope="col" className="num">
              Schema validity
            </th>
            <th scope="col" className="num">
              Category accuracy
            </th>
            <th scope="col" className="num">
              Priority accuracy
            </th>
            <th scope="col" className="num">
              Avg quality
            </th>
            <th scope="col" className="num">
              Avg consistency
            </th>
            <th scope="col" className="num">
              Avg reliability
            </th>
            <th scope="col" className="num">
              Avg latency
            </th>
            <th scope="col" className="num">
              Total tokens
            </th>
            <th scope="col" className="num">
              Total cost
            </th>
            <th scope="col" className="num">
              Failures
            </th>
          </tr>
        </thead>
        <tbody>
          {variants.map((variant) => (
            <tr key={`${variant.prompt_version_id}-${variant.model_name}`}>
              <td>
                {variant.prompt_version_name}{" "}
                <span className="text-[var(--color-text-muted)]">
                  v{variant.prompt_version_version}
                </span>
              </td>
              <td>{variant.model_name}</td>
              <td className="num">{formatNumber(variant.total_runs)}</td>
              <td className="num">{formatPercent(variant.schema_validity_rate)}</td>
              <td className="num">{formatPercent(variant.category_accuracy)}</td>
              <td className="num">{formatPercent(variant.priority_accuracy)}</td>
              <td className="num">{formatDecimal(variant.average_quality_score)}</td>
              <td className="num">{formatDecimal(variant.average_consistency_score)}</td>
              <td className="num">{formatDecimal(variant.average_reliability_score)}</td>
              <td className="num">{formatLatency(variant.average_latency_ms)}</td>
              <td className="num">{formatNumber(variant.total_tokens)}</td>
              <td className="num">{formatUsd(variant.total_estimated_cost_usd)}</td>
              <td className="num">{formatNumber(variant.failure_count)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
