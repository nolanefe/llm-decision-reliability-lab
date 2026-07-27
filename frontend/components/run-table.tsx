import type { Run } from "@/lib/types";
import { formatBoolean, formatDecimal, formatLatency, formatNumber, formatUsd } from "@/lib/format";
import { StatusBadge } from "./status-badge";

export function RunTable({ runs }: { runs: Run[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            <Th>Run</Th>
            <Th>Dataset item</Th>
            <Th>Prompt version</Th>
            <Th>Model</Th>
            <Th align="right">Rep</Th>
            <Th>Status</Th>
            <Th>Schema valid</Th>
            <Th>Category</Th>
            <Th>Priority</Th>
            <Th align="right">Latency</Th>
            <Th align="right">Tokens</Th>
            <Th align="right">Cost</Th>
            <Th align="right">Reliability</Th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {runs.map((run) => (
            <tr key={run.id}>
              <Td>#{run.id}</Td>
              <Td>{run.dataset_item_id}</Td>
              <Td>{run.prompt_version_id}</Td>
              <Td>{run.model_name}</Td>
              <Td align="right">{run.repetition_index}</Td>
              <Td>
                <StatusBadge status={run.status} />
              </Td>
              <Td>{formatBoolean(run.evaluation?.schema_valid ?? null)}</Td>
              <Td>{formatBoolean(run.evaluation?.category_correct ?? null)}</Td>
              <Td>{formatBoolean(run.evaluation?.priority_correct ?? null)}</Td>
              <Td align="right">{formatLatency(run.latency_ms)}</Td>
              <Td align="right">{formatNumber(run.total_tokens)}</Td>
              <Td align="right">{formatUsd(run.estimated_cost_usd)}</Td>
              <Td align="right">{formatDecimal(run.evaluation?.reliability_score ?? null)}</Td>
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
