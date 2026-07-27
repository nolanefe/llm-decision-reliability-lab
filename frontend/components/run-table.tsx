import type { Run } from "@/lib/types";
import { formatBoolean, formatDecimal, formatLatency, formatNumber, formatUsd } from "@/lib/format";
import { StatusBadge } from "./status-badge";

export function RunTable({ runs }: { runs: Run[] }) {
  return (
    <div className="table-wrap max-h-[28rem] overflow-y-auto">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Run</th>
            <th scope="col">Dataset item</th>
            <th scope="col">Prompt version</th>
            <th scope="col">Model</th>
            <th scope="col" className="num">
              Rep
            </th>
            <th scope="col">Status</th>
            <th scope="col">Schema valid</th>
            <th scope="col">Category</th>
            <th scope="col">Priority</th>
            <th scope="col" className="num">
              Latency
            </th>
            <th scope="col" className="num">
              Tokens
            </th>
            <th scope="col" className="num">
              Cost
            </th>
            <th scope="col" className="num">
              Reliability
            </th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              <td className="tabular-nums">#{run.id}</td>
              <td>{run.dataset_item_id}</td>
              <td>{run.prompt_version_id}</td>
              <td>{run.model_name}</td>
              <td className="num">{run.repetition_index}</td>
              <td>
                <StatusBadge status={run.status} />
              </td>
              <td>{formatBoolean(run.evaluation?.schema_valid ?? null)}</td>
              <td>{formatBoolean(run.evaluation?.category_correct ?? null)}</td>
              <td>{formatBoolean(run.evaluation?.priority_correct ?? null)}</td>
              <td className="num">{formatLatency(run.latency_ms)}</td>
              <td className="num">{formatNumber(run.total_tokens)}</td>
              <td className="num">{formatUsd(run.estimated_cost_usd)}</td>
              <td className="num">{formatDecimal(run.evaluation?.reliability_score ?? null)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
