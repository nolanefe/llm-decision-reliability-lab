import { listDatasetItems, listPromptVersions } from "@/lib/api";
import { PageHeading } from "@/components/page-heading";
import { ExperimentForm } from "@/components/experiment-form";
import { EmptyState } from "@/components/empty-state";

export const dynamic = "force-dynamic";

export default async function NewExperimentPage() {
  const [datasetItems, promptVersions] = await Promise.all([
    listDatasetItems(),
    listPromptVersions(),
  ]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeading
        title="Create experiment"
        description="Select the dataset items, prompt versions, models, and repeat count to compare. Execution is a separate, explicit step."
      />

      {datasetItems.length === 0 || promptVersions.length === 0 ? (
        <EmptyState
          title="Not enough evaluation data"
          description="At least one dataset item and one prompt version are required to create an experiment."
        />
      ) : (
        <ExperimentForm datasetItems={datasetItems} promptVersions={promptVersions} />
      )}
    </div>
  );
}
