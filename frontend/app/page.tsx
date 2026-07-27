import Link from "next/link";

const WORKFLOW_STEPS = [
  "Dataset",
  "Prompt versions",
  "Repeated model runs",
  "Deterministic scoring",
  "Variant comparison",
];

const MEASURED_DIMENSIONS = [
  {
    name: "Schema validity",
    description: "Whether output parses as the expected structured JSON.",
  },
  {
    name: "Label accuracy",
    description: "Whether category and priority match expected labels.",
  },
  {
    name: "Consistency",
    description: "Stability of outputs across repeated runs of the same input.",
  },
  {
    name: "Reliability",
    description: "Composite score combining validity, quality, and consistency.",
  },
  {
    name: "Latency",
    description: "End-to-end response time per model call.",
  },
  {
    name: "Token cost",
    description: "Estimated spend based on prompt and completion tokens.",
  },
  {
    name: "Failure categories",
    description: "Structured classification of schema, provider, and content errors.",
  },
];

export default function OverviewPage() {
  return (
    <div className="page-stack">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--color-text-primary)] sm:text-3xl">
          LLM Decision Reliability Lab
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-[var(--color-text-secondary)]">
          Compare prompt and model variants on a fixed task with repeatable,
          deterministic scoring — so you can choose a variant with evidence
          instead of a spot-check.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/experiments/new" className="btn btn-primary">
            Create an experiment
          </Link>
          <Link href="/datasets" className="btn btn-secondary">
            Inspect datasets
          </Link>
        </div>
      </section>

      <section className="card card-padded">
        <h2 className="card-section-title">Evaluation workflow</h2>
        <div className="mt-4 workflow-steps" aria-label="Evaluation workflow steps">
          {WORKFLOW_STEPS.map((step, index) => (
            <span key={step} className="contents">
              {index > 0 ? (
                <span className="workflow-arrow" aria-hidden="true">
                  →
                </span>
              ) : null}
              <span className="workflow-step">{step}</span>
            </span>
          ))}
        </div>
        <p className="mt-4 text-sm leading-relaxed text-[var(--color-text-secondary)]">
          Select a fixed dataset and prompt versions, choose models and a repeat
          count, execute the experiment, then compare variants on measured
          dimensions.
        </p>
      </section>

      <section className="card card-padded">
        <h2 className="card-section-title">Measured dimensions</h2>
        <ul className="mt-4 grid gap-3 sm:grid-cols-2">
          {MEASURED_DIMENSIONS.map((dimension) => (
            <li
              key={dimension.name}
              className="rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-bg-muted)] px-4 py-3"
            >
              <p className="text-sm font-medium text-[var(--color-text-primary)]">
                {dimension.name}
              </p>
              <p className="mt-0.5 text-sm text-[var(--color-text-secondary)]">
                {dimension.description}
              </p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
