import Link from "next/link";

export default function OverviewPage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-3xl font-semibold text-slate-900">
          LLM Decision Reliability Lab
        </h1>
        <p className="mt-3 max-w-2xl text-slate-600">
          A lightweight evaluation tool for comparing prompt and model
          variants on a fixed task. It runs each variant repeatedly against a
          small dataset and measures schema validity, task quality,
          consistency across repeats, latency, and cost — so you have
          objective, repeatable evidence for which prompt/model combination to
          ship, instead of a spot-check.
        </p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          What it measures
        </h2>
        <ul className="mt-3 flex flex-col gap-2 text-sm text-slate-700">
          <li>
            <span className="font-medium text-slate-900">Schema validity</span>{" "}
            — whether the model&apos;s output parses as the expected structured JSON.
          </li>
          <li>
            <span className="font-medium text-slate-900">Task quality</span> —
            whether the output matches the expected category and priority.
          </li>
          <li>
            <span className="font-medium text-slate-900">Consistency</span> —
            how stable outputs are across repeated runs of the same input.
          </li>
          <li>
            <span className="font-medium text-slate-900">Latency and cost</span>{" "}
            — measured per run and aggregated per variant.
          </li>
          <li>
            <span className="font-medium text-slate-900">Reliability score</span>{" "}
            — a single comparable metric combining the above, used to
            recommend a variant.
          </li>
        </ul>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Workflow
        </h2>
        <p className="mt-3 text-sm font-medium text-slate-900">
          Dataset → Prompt Versions → Repeated Runs → Scoring → Comparison
        </p>
        <p className="mt-2 text-sm text-slate-600">
          Pick a fixed dataset and a set of prompt versions, choose a model
          and repeat count, run the experiment, then compare variants side by
          side on the metrics above.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <Link
          href="/experiments/new"
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900"
        >
          Create an experiment
        </Link>
        <Link
          href="/experiments"
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900"
        >
          View experiments
        </Link>
        <Link
          href="/datasets"
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900"
        >
          Inspect evaluation data
        </Link>
      </div>
    </div>
  );
}
