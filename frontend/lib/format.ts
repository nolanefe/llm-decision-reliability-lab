const EM_DASH = "—";

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return EM_DASH;
  return `${(value * 100).toFixed(1)}%`;
}

export function formatUsd(value: number | null | undefined): string {
  if (value === null || value === undefined) return EM_DASH;
  if (value === 0) return "$0.00";
  // Very small costs (fractions of a cent) need more precision than
  // Intl's default currency formatting gives, so pick precision by magnitude.
  const absValue = Math.abs(value);
  const fractionDigits = absValue < 0.01 ? 6 : 2;
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return EM_DASH;
  return value.toLocaleString("en-US");
}

export function formatDecimal(
  value: number | null | undefined,
  digits = 2,
): string {
  if (value === null || value === undefined) return EM_DASH;
  return value.toFixed(digits);
}

export function formatLatency(value: number | null | undefined): string {
  if (value === null || value === undefined) return EM_DASH;
  return `${formatDecimal(value, 0)} ms`;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return EM_DASH;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return EM_DASH;
  return date.toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function formatBoolean(value: boolean | null | undefined): string {
  if (value === null || value === undefined) return EM_DASH;
  return value ? "Yes" : "No";
}

export { EM_DASH };
