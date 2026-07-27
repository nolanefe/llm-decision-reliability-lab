import type { ReactNode } from "react";

export function EmptyState({
  title,
  description,
  action,
  variant = "default",
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  variant?: "default" | "positive";
}) {
  const isPositive = variant === "positive";

  return (
    <div
      className={`rounded-[var(--radius-lg)] border border-dashed p-8 text-center ${
        isPositive
          ? "border-[var(--color-success-border)] bg-[var(--color-success-bg)]"
          : "border-[var(--color-border-strong)] bg-[var(--color-bg-muted)]"
      }`}
    >
      <p
        className={`font-medium ${isPositive ? "text-[var(--color-success-text)]" : "text-[var(--color-text-primary)]"}`}
      >
        {title}
      </p>
      {description ? (
        <p
          className={`mt-1.5 text-sm ${isPositive ? "text-[var(--color-success-text)]" : "text-[var(--color-text-muted)]"}`}
        >
          {description}
        </p>
      ) : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
