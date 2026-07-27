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
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            <Th>Prompt version</Th>
            <Th>Model</Th>
            <Th align="right">Runs</Th>
            <Th align="right">Schema validity</Th>
            <Th align="right">Category accuracy</Th>
            <Th align="right">Priority accuracy</Th>
            <Th align="right">Avg quality</Th>
            <Th align="right">Avg consistency</Th>
            <Th align="right">Avg reliability</Th>
            <Th align="right">Avg latency</Th>
            <Th align="right">Total tokens</Th>
            <Th align="right">Total cost</Th>
            <Th align="right">Failures</Th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {variants.map((variant) => (
            <tr key={`${variant.prompt_version_id}-${variant.model_name}`}>
              <Td>
                {variant.prompt_version_name} v{variant.prompt_version_version}
              </Td>
              <Td>{variant.model_name}</Td>
              <Td align="right">{formatNumber(variant.total_runs)}</Td>
              <Td align="right">{formatPercent(variant.schema_validity_rate)}</Td>
              <Td align="right">{formatPercent(variant.category_accuracy)}</Td>
              <Td align="right">{formatPercent(variant.priority_accuracy)}</Td>
              <Td align="right">{formatDecimal(variant.average_quality_score)}</Td>
              <Td align="right">{formatDecimal(variant.average_consistency_score)}</Td>
              <Td align="right">{formatDecimal(variant.average_reliability_score)}</Td>
              <Td align="right">{formatLatency(variant.average_latency_ms)}</Td>
              <Td align="right">{formatNumber(variant.total_tokens)}</Td>
              <Td align="right">{formatUsd(variant.total_estimated_cost_usd)}</Td>
              <Td align="right">{formatNumber(variant.failure_count)}</Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Th({
  children,
  align = "left",
}: {
  children: React.ReactNode;
  align?: "left" | "right";
}) {
  return (
    <th
      scope="col"
      className={`whitespace-nowrap px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500 ${
        align === "right" ? "text-right" : "text-left"
      }`}
    >
      {children}
    </th>
  );
}

function Td({
  children,
  align = "left",
}: {
  children: React.ReactNode;
  align?: "left" | "right";
}) {
  return (
    <td
      className={`whitespace-nowrap px-3 py-2 text-slate-800 ${
        align === "right" ? "text-right" : "text-left"
      }`}
    >
      {children}
    </td>
  );
}
