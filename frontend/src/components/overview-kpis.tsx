"use client";

import { useQuery } from "@tanstack/react-query";
import type { components } from "@/lib/api/schema";
import { formatCount, formatMoney, formatRate, formatDays } from "@/lib/format";

type Summary = components["schemas"]["OverviewSummary"];

async function fetchSummary(signal: AbortSignal): Promise<Summary> {
  const base =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  const response = await fetch(`${base.replace(/\/$/, "")}/overview/summary`, {
    signal,
  });
  if (!response.ok)
    throw new Error(
      response.status === 503
        ? "Analytics are not ready. Run make analytics."
        : "Unable to load inventory metrics.",
    );
  return response.json() as Promise<Summary>;
}

export function OverviewKpis() {
  const query = useQuery({
    queryKey: ["overview-summary"],
    queryFn: ({ signal }) => fetchSummary(signal),
    retry: false,
  });
  if (query.isPending) return <p role="status">Loading inventory metrics…</p>;
  if (query.isError)
    return (
      <div role="alert">
        <p>{query.error.message}</p>
        <button
          onClick={() => void query.refetch()}
          disabled={query.isFetching}
        >
          Retry
        </button>
      </div>
    );
  const data = query.data;
  const metrics = [
    ["At-risk positions", formatCount(data.at_risk_positions)],
    ["Est. gross margin at risk", formatMoney(data.gross_margin_at_risk_usd)],
    ["Median days of cover", formatDays(data.median_days_of_cover)],
    ["Supplier on-time rate", formatRate(data.supplier_on_time_rate)],
    ["End-of-day in-stock rate", formatRate(data.in_stock_rate)],
    ["Active positions", formatCount(data.active_positions)],
  ];
  return (
    <section aria-label="Inventory overview">
      <p>
        As of {data.as_of_date} · Run {data.run_id}
      </p>
      <dl>
        {metrics.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <p>Exposure is a model estimate from the simulated dataset.</p>
    </section>
  );
}
