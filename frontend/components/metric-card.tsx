export function MetricCard({
  label,
  value,
  hint,
  highlight,
}: {
  label: string;
  value: string;
  hint?: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`card card-padded ${highlight ? "border-[var(--color-accent-border)] bg-[var(--color-accent-subtle)]" : ""}`}
    >
      <p className="card-section-title">{label}</p>
      <p className="mt-1.5 text-2xl font-semibold tabular-nums tracking-tight text-[var(--color-text-primary)]">
        {value}
      </p>
      {hint ? (
        <p className="mt-1 text-xs text-[var(--color-text-muted)]">{hint}</p>
      ) : null}
    </div>
  );
}
