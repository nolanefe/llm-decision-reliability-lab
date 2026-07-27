const STATUS_STYLES: Record<string, string> = {
  draft: "bg-slate-100 text-slate-700 ring-slate-300",
  pending: "bg-blue-50 text-blue-700 ring-blue-300",
  running: "bg-amber-50 text-amber-700 ring-amber-300",
  completed: "bg-green-50 text-green-700 ring-green-300",
  failed: "bg-red-50 text-red-700 ring-red-300",
};

export function StatusBadge({ status }: { status: string }) {
  const styles = STATUS_STYLES[status] ?? "bg-slate-100 text-slate-700 ring-slate-300";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${styles}`}
    >
      {status}
    </span>
  );
}
