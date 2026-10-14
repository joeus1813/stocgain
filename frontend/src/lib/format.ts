/** Presentation units from docs/07 §4.6. Date-only values use UTC. */
export function formatCount(v: number): string {
  return Math.round(v).toLocaleString("en-US");
}
export function formatDecimal(v: number | null): string {
  return v === null
    ? "—"
    : v.toLocaleString("en-US", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      });
}
export function formatMoney(v: number, compact = false): string {
  const a = Math.abs(v);
  if (compact && a >= 1000000)
    return `${v < 0 ? "−" : ""}$${(a / 1000000).toFixed(2)}M`;
  if (compact && a >= 10000)
    return `${v < 0 ? "−" : ""}$${(a / 1000).toFixed(1)}K`;
  return v.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}
export function formatPrice(v: number): string {
  return v.toLocaleString("en-US", { style: "currency", currency: "USD" });
}
export function formatRate(v: number | null): string {
  return v === null ? "—" : `${(v * 100).toFixed(1)}%`;
}
export function formatProbability(v: number): string {
  return v > 0 && v < 0.001
    ? "<0.1%"
    : v > 0.999 && v < 1
      ? ">99.9%"
      : formatRate(v);
}
export function formatDays(v: number | null): string {
  return v === null ? "—" : `${formatDecimal(v)} days`;
}
export function formatDate(v: string | null, full = false): string {
  return v === null
    ? "—"
    : new Date(`${v}T12:00:00Z`).toLocaleDateString("en-US", {
        timeZone: "UTC",
        month: "short",
        day: "numeric",
        ...(full ? ({ weekday: "short", year: "numeric" } as const) : {}),
      });
}
export function formatDelta(
  v: number,
  kind: "count" | "money" | "rate" = "count",
): string {
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${kind === "money" ? formatMoney(Math.abs(v), true) : kind === "rate" ? `${(Math.abs(v) * 100).toFixed(1)} pts` : formatCount(Math.abs(v))}`;
}
export function formatLabel(v: string): string {
  return v.replaceAll("_", " ").replace(/^./, (x) => x.toUpperCase());
}
