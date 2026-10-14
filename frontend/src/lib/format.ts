/** Minimal Phase 4 presentation boundary; complete UI formatting belongs to Phase 5. */
export function formatCount(value: number): string {
  return value.toLocaleString("en-US");
}
export function formatMoney(value: number): string {
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}
export function formatRate(value: number | null): string {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}
export function formatDays(value: number | null): string {
  return value === null ? "—" : `${value.toFixed(1)} days`;
}
