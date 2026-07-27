import Link from "next/link";
import { listExperiments } from "@/lib/api";
import { PageHeading } from "@/components/page-heading";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { formatDateTime } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function ExperimentsPage() {
  const experiments = await listExperiments();
  const sorted = [...experiments].sort((a, b) => b.id - a.id);

  return (
    <div className="flex flex-col gap-6">
      <PageHeading
        title="Experiments"
        description="Every experiment created against this backend, newest first."
        action={
          <Link
            href="/experiments/new"
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900"
          >
            Create experiment
          </Link>
        }
      />

      {sorted.length === 0 ? (
        <EmptyState
          title="No experiments yet"
          description="Create an experiment to compare prompt and model variants."
          action={
            <Link
              href="/experiments/new"
              className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900"
            >
              Create experiment
            </Link>
          }
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <Th>ID</Th>
                <Th>Name</Th>
                <Th>Status</Th>
                <Th align="right">Repeat count</Th>
                <Th align="right">Dataset items</Th>
                <Th align="right">Prompt versions</Th>
                <Th align="right">Models</Th>
                <Th>Created</Th>
                <Th>{""}</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {sorted.map((experiment) => (
                <tr key={experiment.id}>
                  <Td>#{experiment.id}</Td>
                  <Td>{experiment.name}</Td>
                  <Td>
                    <StatusBadge status={experiment.status} />
                  </Td>
                  <Td align="right">{experiment.repeat_count}</Td>
                  <Td align="right">{experiment.dataset_item_ids.length}</Td>
                  <Td align="right">{experiment.prompt_version_ids.length}</Td>
                  <Td align="right">{experiment.model_names.length}</Td>
                  <Td>{formatDateTime(experiment.created_at)}</Td>
                  <Td>
                    <Link
                      href={`/experiments/${experiment.id}`}
                      className="font-medium text-slate-900 underline underline-offset-2 hover:text-slate-700"
                    >
                      View
                    </Link>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
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
