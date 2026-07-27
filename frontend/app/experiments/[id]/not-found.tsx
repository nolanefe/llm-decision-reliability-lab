import { EmptyState } from "@/components/empty-state";

export default function NotFound() {
  return (
    <EmptyState
      title="Experiment not found"
      description="No experiment exists with this ID."
    />
  );
}
