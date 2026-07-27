import { listDatasetItems, listPromptVersions } from "@/lib/api";
import { PageHeading } from "@/components/page-heading";
import { EmptyState } from "@/components/empty-state";
import { CategoryBadge, PriorityBadge } from "@/components/category-badge";

export const dynamic = "force-dynamic";

export default async function DatasetsPage() {
  const [datasetItems, promptVersions] = await Promise.all([
    listDatasetItems(),
    listPromptVersions(),
  ]);

  return (
    <div className="page-stack">
      <PageHeading
        title="Evaluation data"
        description="Fixed dataset items and prompt versions used to build experiments. Read-only in v0.1."
      />

      <section aria-labelledby="dataset-items-heading">
        <div className="flex items-baseline justify-between gap-4">
          <h2
            id="dataset-items-heading"
            className="text-lg font-semibold text-[var(--color-text-primary)]"
          >
            Dataset items
          </h2>
          <span className="text-sm text-[var(--color-text-muted)]">
            {datasetItems.length} item{datasetItems.length === 1 ? "" : "s"}
          </span>
        </div>
        {datasetItems.length === 0 ? (
          <div className="mt-4">
            <EmptyState
              title="No dataset items"
              description="No dataset items are seeded in this backend yet."
            />
          </div>
        ) : (
          <div className="mt-4 flex flex-col gap-3">
            {datasetItems.map((item) => (
              <article key={item.id} className="card card-padded">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <h3 className="font-medium text-[var(--color-text-primary)]">
                    {item.name}
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    <CategoryBadge category={item.expected_category} />
                    <PriorityBadge priority={item.expected_priority} />
                  </div>
                </div>
                <div className="mt-3">
                  <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
                    Ticket text
                  </p>
                  <div className="text-preview mt-1">{item.input_text}</div>
                </div>
                {item.reference_summary || item.reference_action ? (
                  <div className="mt-3 grid gap-2 border-t border-[var(--color-border)] pt-3 sm:grid-cols-2">
                    {item.reference_summary ? (
                      <div>
                        <p className="text-xs font-medium text-[var(--color-text-muted)]">
                          Reference summary
                        </p>
                        <p className="mt-0.5 text-sm text-[var(--color-text-secondary)]">
                          {item.reference_summary}
                        </p>
                      </div>
                    ) : null}
                    {item.reference_action ? (
                      <div>
                        <p className="text-xs font-medium text-[var(--color-text-muted)]">
                          Reference action
                        </p>
                        <p className="mt-0.5 text-sm text-[var(--color-text-secondary)]">
                          {item.reference_action}
                        </p>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </section>

      <section
        aria-labelledby="prompt-versions-heading"
        className="border-t border-[var(--color-border)] pt-[var(--section-gap)]"
      >
        <div className="flex items-baseline justify-between gap-4">
          <h2
            id="prompt-versions-heading"
            className="text-lg font-semibold text-[var(--color-text-primary)]"
          >
            Prompt versions
          </h2>
          <span className="text-sm text-[var(--color-text-muted)]">
            {promptVersions.length} version
            {promptVersions.length === 1 ? "" : "s"}
          </span>
        </div>
        {promptVersions.length === 0 ? (
          <div className="mt-4">
            <EmptyState
              title="No prompt versions"
              description="No prompt versions are seeded in this backend yet."
            />
          </div>
        ) : (
          <div className="mt-4 flex flex-col gap-3">
            {promptVersions.map((version) => (
              <article key={version.id} className="card card-padded">
                <div className="flex flex-wrap items-baseline gap-2">
                  <h3 className="font-medium text-[var(--color-text-primary)]">
                    {version.name}
                  </h3>
                  <span className="badge badge-neutral">v{version.version}</span>
                </div>
                {version.description ? (
                  <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
                    {version.description}
                  </p>
                ) : null}
                <div className="mt-3">
                  <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
                    Template preview
                  </p>
                  <pre className="code-preview mt-1.5">{version.template_text}</pre>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
