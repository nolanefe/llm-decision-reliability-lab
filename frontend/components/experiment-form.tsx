"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { DatasetItem, PromptVersion } from "@/lib/types";
import { SUPPORTED_MODELS } from "@/lib/types";
import { ApiError, createExperiment } from "@/lib/api";
import { ErrorState } from "./error-state";

function toggle(values: number[], value: number): number[] {
  return values.includes(value)
    ? values.filter((existing) => existing !== value)
    : [...values, value];
}

function toggleString(values: string[], value: string): string[] {
  return values.includes(value)
    ? values.filter((existing) => existing !== value)
    : [...values, value];
}

function PlannedRunSummary({ count }: { count: number }) {
  return (
    <div className="card card-padded border-[var(--color-accent-border)] bg-[var(--color-accent-subtle)]">
      <p className="card-section-title">Planned run summary</p>
      <p className="mt-2 text-3xl font-semibold tabular-nums text-[var(--color-text-primary)]">
        {count}
      </p>
      <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
        dataset items × prompt versions × models × repeat count
      </p>
      <p className="mt-2 text-xs text-[var(--color-text-muted)]">
        The backend validates this count against the configured run limit before
        execution.
      </p>
    </div>
  );
}

export function ExperimentForm({
  datasetItems,
  promptVersions,
}: {
  datasetItems: DatasetItem[];
  promptVersions: PromptVersion[];
}) {
  const router = useRouter();

  const [name, setName] = useState("");
  const [datasetItemIds, setDatasetItemIds] = useState<number[]>([]);
  const [promptVersionIds, setPromptVersionIds] = useState<number[]>([]);
  const [modelNames, setModelNames] = useState<string[]>([]);
  const [repeatCount, setRepeatCount] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const plannedRunCount = useMemo(
    () =>
      datasetItemIds.length *
      promptVersionIds.length *
      modelNames.length *
      repeatCount,
    [datasetItemIds, promptVersionIds, modelNames, repeatCount],
  );

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    if (name.trim().length === 0) {
      setValidationError("Experiment name is required.");
      return;
    }
    if (datasetItemIds.length === 0) {
      setValidationError("Select at least one dataset item.");
      return;
    }
    if (promptVersionIds.length === 0) {
      setValidationError("Select at least one prompt version.");
      return;
    }
    if (modelNames.length === 0) {
      setValidationError("Select at least one model.");
      return;
    }

    setValidationError(null);
    setApiError(null);
    setSubmitting(true);
    try {
      const experiment = await createExperiment({
        name: name.trim(),
        dataset_item_ids: datasetItemIds,
        prompt_version_ids: promptVersionIds,
        model_names: modelNames,
        repeat_count: repeatCount,
      });
      router.push(`/experiments/${experiment.id}`);
    } catch (error) {
      setApiError(
        error instanceof ApiError ? error.message : "Failed to create experiment.",
      );
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6 lg:flex-row lg:items-start lg:gap-8">
      <div className="flex min-w-0 flex-1 flex-col gap-6">
        <section className="form-section" aria-labelledby="section-name">
          <h2 id="section-name" className="form-section-title">
            1. Experiment name
          </h2>
          <p className="form-section-desc">
            A descriptive label to identify this comparison run.
          </p>
          <label htmlFor="experiment-name" className="form-label">
            Name
          </label>
          <input
            id="experiment-name"
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="input-field max-w-md"
            placeholder="e.g. baseline vs explicit-criteria triage"
          />
        </section>

        <section className="form-section" aria-labelledby="section-dataset">
          <h2 id="section-dataset" className="form-section-title">
            2. Dataset selection
          </h2>
          <p className="form-section-desc">
            {datasetItemIds.length} of {datasetItems.length} items selected.
          </p>
          <div className="flex max-h-64 flex-col gap-1 overflow-y-auto">
            {datasetItems.map((item) => {
              const selected = datasetItemIds.includes(item.id);
              return (
                <label
                  key={item.id}
                  className={`selection-item ${selected ? "selection-item-selected" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={() =>
                      setDatasetItemIds((current) => toggle(current, item.id))
                    }
                  />
                  <span className="text-sm">
                    <span className="font-medium text-[var(--color-text-primary)]">
                      {item.name}
                    </span>{" "}
                    <span className="text-[var(--color-text-muted)]">
                      ({item.expected_category} / {item.expected_priority})
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        </section>

        <section className="form-section" aria-labelledby="section-prompts">
          <h2 id="section-prompts" className="form-section-title">
            3. Prompt-version selection
          </h2>
          <p className="form-section-desc">
            {promptVersionIds.length} of {promptVersions.length} versions
            selected.
          </p>
          <div className="flex flex-col gap-1">
            {promptVersions.map((version) => {
              const selected = promptVersionIds.includes(version.id);
              return (
                <label
                  key={version.id}
                  className={`selection-item ${selected ? "selection-item-selected" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={() =>
                      setPromptVersionIds((current) => toggle(current, version.id))
                    }
                  />
                  <span className="text-sm">
                    <span className="font-medium text-[var(--color-text-primary)]">
                      {version.name}
                    </span>{" "}
                    <span className="text-[var(--color-text-muted)]">
                      v{version.version}
                    </span>
                    {version.description ? (
                      <span className="mt-0.5 block text-[var(--color-text-muted)]">
                        {version.description}
                      </span>
                    ) : null}
                  </span>
                </label>
              );
            })}
          </div>
        </section>

        <section className="form-section" aria-labelledby="section-models">
          <h2 id="section-models" className="form-section-title">
            4. Model selection
          </h2>
          <p className="form-section-desc">
            {modelNames.length} of {SUPPORTED_MODELS.length} models selected.
          </p>
          <div className="flex flex-col gap-1">
            {SUPPORTED_MODELS.map((model) => {
              const selected = modelNames.includes(model);
              return (
                <label
                  key={model}
                  className={`selection-item ${selected ? "selection-item-selected" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={() =>
                      setModelNames((current) => toggleString(current, model))
                    }
                  />
                  <span className="text-sm text-[var(--color-text-primary)]">
                    {model}
                  </span>
                </label>
              );
            })}
          </div>
        </section>

        <section className="form-section" aria-labelledby="section-repeat">
          <h2 id="section-repeat" className="form-section-title">
            5. Repeat count
          </h2>
          <p className="form-section-desc">
            Number of times each (dataset item, prompt version, model) tuple is
            executed.
          </p>
          <label htmlFor="repeat-count" className="form-label">
            Repeats per combination
          </label>
          <input
            id="repeat-count"
            type="number"
            min={1}
            max={10}
            value={repeatCount}
            onChange={(event) =>
              setRepeatCount(
                Math.min(10, Math.max(1, Number(event.target.value) || 1)),
              )
            }
            className="input-field w-24"
          />
        </section>

        {/* Mobile-only summary */}
        <div className="lg:hidden">
          <PlannedRunSummary count={plannedRunCount} />
        </div>

        {validationError ? (
          <ErrorState title="Check the form" message={validationError} />
        ) : null}
        {apiError ? (
          <ErrorState title="Could not create experiment" message={apiError} />
        ) : null}

        <div>
          <button type="submit" disabled={submitting} className="btn btn-primary">
            {submitting ? "Creating…" : "Create experiment"}
          </button>
        </div>
      </div>

      {/* Desktop sticky summary */}
      <aside
        className="hidden w-72 shrink-0 lg:block"
        aria-label="Planned run summary"
      >
        <div className="sticky top-20">
          <PlannedRunSummary count={plannedRunCount} />
        </div>
      </aside>
    </form>
  );
}
