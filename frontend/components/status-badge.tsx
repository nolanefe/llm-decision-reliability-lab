const STATUS_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  draft: {
    bg: "var(--color-bg-muted)",
    text: "var(--color-text-secondary)",
    border: "var(--color-border)",
  },
  pending: {
    bg: "#eff6ff",
    text: "#1e40af",
    border: "#bfdbfe",
  },
  running: {
    bg: "var(--color-warning-bg)",
    text: "var(--color-warning-text)",
    border: "var(--color-warning-border)",
  },
  completed: {
    bg: "var(--color-success-bg)",
    text: "var(--color-success-text)",
    border: "var(--color-success-border)",
  },
  failed: {
    bg: "var(--color-error-bg)",
    text: "var(--color-error-text)",
    border: "var(--color-error-border)",
  },
};

export function StatusBadge({ status }: { status: string }) {
  const styles = STATUS_STYLES[status] ?? STATUS_STYLES.draft;
  return (
    <span
      className="badge"
      style={{
        background: styles.bg,
        color: styles.text,
        borderColor: styles.border,
      }}
    >
      <span className="sr-only">Status: </span>
      {status}
    </span>
  );
}
