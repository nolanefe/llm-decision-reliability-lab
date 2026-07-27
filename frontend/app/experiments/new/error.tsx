"use client";

import { ErrorState } from "@/components/error-state";

export default function Error({ error }: { error: Error & { digest?: string } }) {
  return (
    <ErrorState
      title="Could not load the data needed to create an experiment"
      message={error.message || "The API request failed."}
    />
  );
}
