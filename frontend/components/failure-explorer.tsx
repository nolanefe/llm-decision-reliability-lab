import type { FailureEntry } from "@/lib/types";
import { formatBoolean } from "@/lib/format";
import { EmptyState } from "./empty-state";
import { StatusBadge } from "./status-badge";

function formatFailureCategory(category: string): string {
  return category.replace(/_/g, " ");
}

export function FailureExplorer({ failures }: { failures: FailureEntry[] }) {
  if (failures.length === 0) {
    return (
      <EmptyState
        variant="positive"
        title="No failures detected"
        description="Every run in this experiment produced a schema-valid, correctly labeled result."
      />
    );
  }

  return (
    <ul className="flex flex-col gap-3" role="list">
      {failures.map((failure) => (
        <li key={failure.run_id} className="card card-padded">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="badge border-[var(--color-error-border)] bg-[var(--color-error-bg)] text-[var(--color-error-text)]">
                {formatFailureCategory(failure.failure_category)}
              </span>
              <StatusBadge status={failure.run_status} />
              <span className="text-xs text-[var(--color-text-muted)]">
                Run #{failure.run_id}
              </span>
            </div>
            <span className="text-xs tabular-nums text-[var(--color-text-muted)]">
              Repetition {failure.repetition_index}
            </span>
          </div>

          <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-xs text-[var(--color-text-muted)]">Dataset item</dt>
              <dd className="mt-0.5 text-[var(--color-text-primary)]">
                {failure.dataset_item_name}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-[var(--color-text-muted)]">Prompt version</dt>
              <dd className="mt-0.5 text-[var(--color-text-primary)]">
                {failure.prompt_version_name}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-[var(--color-text-muted)]">Model</dt>
              <dd className="mt-0.5 text-[var(--color-text-primary)]">
                {failure.model_name}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-[var(--color-text-muted)]">Schema valid</dt>
              <dd className="mt-0.5 text-[var(--color-text-primary)]">
                {formatBoolean(failure.schema_valid)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-[var(--color-text-muted)]">Category correct</dt>
              <dd className="mt-0.5 text-[var(--color-text-primary)]">
                {formatBoolean(failure.category_correct)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-[var(--color-text-muted)]">Priority correct</dt>
              <dd className="mt-0.5 text-[var(--color-text-primary)]">
                {formatBoolean(failure.priority_correct)}
              </dd>
            </div>
          </dl>

          {failure.sanitized_error_message ? (
            <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--color-error-border)] bg-[var(--color-error-bg)] px-3 py-2">
              <p className="text-xs font-medium text-[var(--color-error-text)]">Error</p>
              <p className="mt-0.5 text-sm text-[var(--color-error-text)]">
                {failure.sanitized_error_message}
              </p>
            </div>
          ) : null}

          {failure.raw_response_preview ? (
            <div className="mt-3">
              <p className="text-xs font-medium text-[var(--color-text-muted)]">
                Response preview
              </p>
              <pre className="code-preview mt-1 max-h-24 text-xs">
                {failure.raw_response_preview}
              </pre>
            </div>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
