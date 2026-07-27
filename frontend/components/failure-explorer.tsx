import type { FailureEntry } from "@/lib/types";
import { formatBoolean } from "@/lib/format";
import { EmptyState } from "./empty-state";
import { StatusBadge } from "./status-badge";

export function FailureExplorer({ failures }: { failures: FailureEntry[] }) {
  if (failures.length === 0) {
    return (
      <EmptyState
        title="No failures"
        description="Every run in this experiment produced a schema-valid, correctly labeled result."
      />
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {failures.map((failure) => (
        <li
          key={failure.run_id}
          className="rounded-lg border border-slate-200 bg-white p-4"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-700 ring-1 ring-inset ring-red-300">
                {failure.failure_category.replace(/_/g, " ")}
              </span>
              <StatusBadge status={failure.run_status} />
              <span className="text-xs text-slate-500">Run #{failure.run_id}</span>
            </div>
            <span className="text-xs text-slate-500">
              Repetition {failure.repetition_index}
            </span>
          </div>

          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-slate-500">Dataset item</dt>
              <dd className="text-slate-900">{failure.dataset_item_name}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Prompt version</dt>
              <dd className="text-slate-900">{failure.prompt_version_name}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Model</dt>
              <dd className="text-slate-900">{failure.model_name}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Schema valid</dt>
              <dd className="text-slate-900">{formatBoolean(failure.schema_valid)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Category correct</dt>
              <dd className="text-slate-900">
                {formatBoolean(failure.category_correct)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Priority correct</dt>
              <dd className="text-slate-900">
                {formatBoolean(failure.priority_correct)}
              </dd>
            </div>
          </dl>

          {failure.sanitized_error_message ? (
            <p className="mt-3 text-sm text-slate-700">
              <span className="font-medium">Error: </span>
              {failure.sanitized_error_message}
            </p>
          ) : null}

          {failure.raw_response_preview ? (
            <p className="mt-2 rounded bg-slate-50 p-2 font-mono text-xs text-slate-600">
              {failure.raw_response_preview}
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
