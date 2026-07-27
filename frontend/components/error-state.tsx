export function ErrorState({
  message,
  title = "Something went wrong",
}: {
  message: string;
  title?: string;
}) {
  return (
    <div
      role="alert"
      className="rounded-[var(--radius-lg)] border border-[var(--color-error-border)] bg-[var(--color-error-bg)] p-4 text-sm text-[var(--color-error-text)]"
    >
      <p className="font-medium">{title}</p>
      <p className="mt-1">{message}</p>
    </div>
  );
}
