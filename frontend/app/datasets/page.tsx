import { listDatasetItems, listPromptVersions } from "@/lib/api";
import { PageHeading } from "@/components/page-heading";
import { EmptyState } from "@/components/empty-state";

export const dynamic = "force-dynamic";

export default async function DatasetsPage() {
  const [datasetItems, promptVersions] = await Promise.all([
    listDatasetItems(),
    listPromptVersions(),
  ]);

  return (
    <div className="flex flex-col gap-10">
      <PageHeading
        title="Evaluation data"
        description="The fixed dataset items and prompt versions available to build experiments from. Read-only in v0.1."
      />

      <section>
        <h2 className="text-lg font-semibold text-slate-900">
          Dataset items ({datasetItems.length})
        </h2>
        {datasetItems.length === 0 ? (
          <div className="mt-3">
            <EmptyState
              title="No dataset items"
              description="No dataset items are seeded in this backend yet."
            />
          </div>
        ) : (
          <div className="mt-3 flex flex-col gap-3">
            {datasetItems.map((item) => (
              <article
                key={item.id}
                className="rounded-lg border border-slate-200 bg-white p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-medium text-slate-900">{item.name}</h3>
                  <div className="flex gap-2 text-xs">
                    <span className="rounded-full bg-slate-100 px-2.5 py-0.5 font-medium text-slate-700">
                      {item.expected_category}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2.5 py-0.5 font-medium text-slate-700">
                      {item.expected_priority}
                    </span>
                  </div>
                </div>
                <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">
                  {item.input_text}
                </p>
                {item.reference_summary ? (
                  <p className="mt-2 text-sm text-slate-500">
                    <span className="font-medium text-slate-600">
                      Reference summary:
                    </span>{" "}
                    {item.reference_summary}
                  </p>
                ) : null}
                {item.reference_action ? (
                  <p className="mt-1 text-sm text-slate-500">
                    <span className="font-medium text-slate-600">
                      Reference action:
                    </span>{" "}
                    {item.reference_action}
                  </p>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold text-slate-900">
          Prompt versions ({promptVersions.length})
        </h2>
        {promptVersions.length === 0 ? (
          <div className="mt-3">
            <EmptyState
              title="No prompt versions"
              description="No prompt versions are seeded in this backend yet."
            />
          </div>
        ) : (
          <div className="mt-3 flex flex-col gap-3">
            {promptVersions.map((version) => (
              <article
                key={version.id}
                className="rounded-lg border border-slate-200 bg-white p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-medium text-slate-900">
                    {version.name}{" "}
                    <span className="text-slate-500">v{version.version}</span>
                  </h3>
                </div>
                {version.description ? (
                  <p className="mt-1 text-sm text-slate-600">{version.description}</p>
                ) : null}
                <pre className="mt-3 max-h-48 overflow-y-auto whitespace-pre-wrap rounded bg-slate-50 p-3 font-mono text-xs text-slate-700">
                  {version.template_text}
                </pre>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
