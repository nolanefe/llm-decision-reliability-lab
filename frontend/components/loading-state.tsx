export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <p role="status" className="py-8 text-sm text-slate-500">
      {label}
    </p>
  );
}
