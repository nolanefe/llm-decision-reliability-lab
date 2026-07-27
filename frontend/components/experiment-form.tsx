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
    <form onSubmit={handleSubmit} className="flex flex-col gap-6">
      <div>
        <label htmlFor="experiment-name" className="block text-sm font-medium text-slate-700">
          Experiment name
        </label>
        <input
          id="experiment-name"
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="mt-1 block w-full max-w-md rounded-md border border-slate-300 px-3 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900"
          placeholder="e.g. baseline vs explicit-criteria triage"
        />
      </div>

      <fieldset className="rounded-lg border border-slate-200 p-4">
        <legend className="px-1 text-sm font-medium text-slate-700">
          Dataset items ({datasetItemIds.length} selected)
        </legend>
        <div className="mt-2 flex max-h-64 flex-col gap-2 overflow-y-auto">
          {datasetItems.map((item) => (
            <label key={item.id} className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={datasetItemIds.includes(item.id)}
                onChange={() => setDatasetItemIds((current) => toggle(current, item.id))}
              />
              <span>
                <span className="font-medium text-slate-900">{item.name}</span>{" "}
                <span className="text-slate-500">
                  ({item.expected_category} / {item.expected_priority})
                </span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="rounded-lg border border-slate-200 p-4">
        <legend className="px-1 text-sm font-medium text-slate-700">
          Prompt versions ({promptVersionIds.length} selected)
        </legend>
        <div className="mt-2 flex flex-col gap-2">
          {promptVersions.map((version) => (
            <label key={version.id} className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={promptVersionIds.includes(version.id)}
                onChange={() =>
                  setPromptVersionIds((current) => toggle(current, version.id))
                }
              />
              <span>
                <span className="font-medium text-slate-900">{version.name}</span>{" "}
                <span className="text-slate-500">v{version.version}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="rounded-lg border border-slate-200 p-4">
        <legend className="px-1 text-sm font-medium text-slate-700">
          Models ({modelNames.length} selected)
        </legend>
        <div className="mt-2 flex flex-col gap-2">
          {SUPPORTED_MODELS.map((model) => (
            <label key={model} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={modelNames.includes(model)}
                onChange={() => setModelNames((current) => toggleString(current, model))}
              />
              <span className="text-slate-900">{model}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <div>
        <label htmlFor="repeat-count" className="block text-sm font-medium text-slate-700">
          Repeat count per (dataset item, prompt version, model)
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
          className="mt-1 block w-24 rounded-md border border-slate-300 px-3 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900"
        />
      </div>

      <div className="rounded-lg bg-slate-50 p-4 text-sm text-slate-700">
        Planned run count:{" "}
        <span className="font-semibold text-slate-900">{plannedRunCount}</span>{" "}
        (dataset items × prompt versions × models × repeat count)
      </div>

      {validationError ? <ErrorState title="Check the form" message={validationError} /> : null}
      {apiError ? <ErrorState title="Could not create experiment" message={apiError} /> : null}

      <div>
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900"
        >
          {submitting ? "Creating…" : "Create experiment"}
        </button>
      </div>
    </form>
  );
}
