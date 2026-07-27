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
    <div className="page-stack">
      <PageHeading
        title="Experiments"
        description="All experiments created against this backend, newest first."
        action={
          <Link href="/experiments/new" className="btn btn-primary">
            Create experiment
          </Link>
        }
      />

      {sorted.length === 0 ? (
        <EmptyState
          title="No experiments yet"
          description="Create an experiment to compare prompt and model variants on the fixed evaluation dataset."
          action={
            <Link href="/experiments/new" className="btn btn-primary">
              Create experiment
            </Link>
          }
        />
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">ID</th>
                <th scope="col">Name</th>
                <th scope="col">Status</th>
                <th scope="col" className="num">
                  Repeats
                </th>
                <th scope="col" className="num">
                  Dataset
                </th>
                <th scope="col" className="num">
                  Prompts
                </th>
                <th scope="col" className="num">
                  Models
                </th>
                <th scope="col">Created</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((experiment) => (
                <tr key={experiment.id}>
                  <td className="tabular-nums text-[var(--color-text-muted)]">
                    #{experiment.id}
                  </td>
                  <td>
                    <Link
                      href={`/experiments/${experiment.id}`}
                      className="font-medium text-[var(--color-accent)] no-underline hover:underline"
                    >
                      {experiment.name}
                    </Link>
                  </td>
                  <td>
                    <StatusBadge status={experiment.status} />
                  </td>
                  <td className="num">{experiment.repeat_count}</td>
                  <td className="num">{experiment.dataset_item_ids.length}</td>
                  <td className="num">{experiment.prompt_version_ids.length}</td>
                  <td className="num">{experiment.model_names.length}</td>
                  <td className="whitespace-nowrap text-[var(--color-text-secondary)]">
                    {formatDateTime(experiment.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
