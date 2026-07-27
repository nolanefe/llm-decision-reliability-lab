import { notFound } from "next/navigation";
import { ApiError, getExperiment } from "@/lib/api";
import { ExperimentDetailView } from "@/components/experiment-detail-view";

export const dynamic = "force-dynamic";

export default async function ExperimentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const experimentId = Number(id);
  if (!Number.isInteger(experimentId)) {
    notFound();
  }

  let experiment;
  try {
    experiment = await getExperiment(experimentId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  return <ExperimentDetailView experiment={experiment} />;
}
