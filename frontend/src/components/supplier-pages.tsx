"use client";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
  BarChart,
  Bar,
} from "recharts";
import { useApi } from "@/lib/api/hooks";
import type { Schema } from "@/lib/api/client";
import { apiFilters, globalQuery, useUrlState } from "@/lib/url-state";
import {
  formatCount as count,
  formatMoney as money,
  formatRate as rate,
  formatDays as days,
  formatDecimal as decimal,
  formatDate as date,
} from "@/lib/format";
import { Card, Kpi, Loading, ErrorState, Tier, Probability } from "./shared/ui";
import { QueryPanel } from "./shared/query-panel";
export function Suppliers() {
  const params = useSearchParams(),
    router = useRouter();
  const { update } = useUrlState();
  const filters = apiFilters(
    new URLSearchParams(globalQuery(new URLSearchParams(params.toString()))),
  );
  filters.set("sort_by", params.get("sort") ?? "reliability_rank");
  filters.set("sort_dir", params.get("dir") ?? "asc");
  if (params.get("flagged")) filters.set("flagged_only", "true");
  const q = useApi<Schema<"SupplierList">>(`/suppliers?${filters}`);
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">Supply reliability</div>
          <h1>Supplier Performance</h1>
          <p>
            Delivery consistency, lead times, and the inventory exposed to them.
          </p>
        </div>
      </div>
      <QueryPanel<Schema<"SupplierSummary">>
        path={`/suppliers/summary?${apiFilters(new URLSearchParams(globalQuery(new URLSearchParams(params.toString()))))}`}
      >
        {(s) => (
          <div className="kpi-grid supplier-kpis">
            <Kpi
              label="Suppliers flagged"
              value={`${count(s.flagged_suppliers)} / ${count(s.suppliers)}`}
              definition="supplier"
            />
            <Kpi
              label="On-time rate · 90 days"
              value={rate(s.on_time_rate_90d)}
              definition="supplier"
            />
            <Kpi
              label="Mean lead time"
              value={days(s.mean_lead_time_days)}
              definition="supplier"
            />
            <Kpi
              label="Overdue open POs"
              value={count(s.overdue_open_pos)}
              definition="supplier"
            />
          </div>
        )}
      </QueryPanel>
      {q.isPending ? (
        <Loading />
      ) : q.isError ? (
        <ErrorState error={q.error} retry={() => void q.refetch()} />
      ) : (
        <>
          <div className="notice">{q.data.disclaimer}</div>
          <div className="stack" style={{ marginTop: 20 }}>
            <Card
              title="Reliability vs. variability"
              subtitle="90-day on-time rate × lead-time CV · bubble area indicates estimated margin exposure"
            >
              <div
                className="chart"
                role="img"
                aria-label="Supplier delivery reliability scatter"
              >
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ bottom: 20, left: 12, right: 20 }}>
                    <CartesianGrid stroke="var(--chart-grid)" />
                    <XAxis
                      type="number"
                      dataKey="on_time_rate"
                      name="On-time rate"
                      domain={[0, 1]}
                      tickFormatter={rate}
                    />
                    <YAxis
                      type="number"
                      dataKey="lead_time_cv"
                      name="Lead-time CV"
                    />
                    <ZAxis
                      dataKey="margin_at_risk_usd"
                      range={[40, 450]}
                      name="Est. margin at risk"
                    />
                    <Tooltip cursor={{ strokeDasharray: "3 3" }} />
                    <ReferenceLine
                      x={0.8}
                      stroke="var(--color-ink-400)"
                      strokeDasharray="4 4"
                    />
                    <ReferenceLine
                      y={0.35}
                      stroke="var(--color-ink-400)"
                      strokeDasharray="4 4"
                    />
                    <Scatter
                      isAnimationActive={false}
                      data={q.data.items.filter(
                        (s) =>
                          s.on_time_rate !== null && s.lead_time_cv !== null,
                      )}
                      fill="var(--color-teal-600)"
                      fillOpacity={0.7}
                      onClick={(_, i) => {
                        const supplier = q.data.items.filter(
                          (s) =>
                            s.on_time_rate !== null && s.lead_time_cv !== null,
                        )[i];
                        if (supplier)
                          router.push(`/suppliers/${supplier.supplier_id}`);
                      }}
                    />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card
              title="Ranked suppliers"
              subtitle="Received lead times: trailing 180 days · due-date KPIs: trailing 90 days"
              actions={
                <label>
                  <input
                    type="checkbox"
                    checked={params.has("flagged")}
                    onChange={(e) =>
                      update({ flagged: e.target.checked ? "true" : null })
                    }
                  />{" "}
                  Review flags only
                </label>
              }
            >
              <div className="risk-controls">
                <label>
                  Sort{" "}
                  <select
                    aria-label="Supplier sort"
                    value={params.get("sort") ?? "reliability_rank"}
                    onChange={(e) => update({ sort: e.target.value })}
                  >
                    <option value="reliability_rank">Reliability rank</option>
                    <option value="on_time_rate">On-time rate</option>
                    <option value="lead_time_cv">Lead-time variability</option>
                    <option value="margin_at_risk_usd">
                      Est. margin at risk
                    </option>
                    <option value="at_risk_positions">At-risk positions</option>
                  </select>
                </label>
                <button
                  onClick={() =>
                    update({
                      dir: params.get("dir") === "desc" ? "asc" : "desc",
                    })
                  }
                >
                  {params.get("dir") === "desc"
                    ? "Descending ↓"
                    : "Ascending ↑"}
                </button>
              </div>
              <div className="table-scroll" tabIndex={0}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Rank / Supplier</th>
                      <th>On time</th>
                      <th>In full</th>
                      <th>Lead time ± SD</th>
                      <th>Overdue</th>
                      <th>At risk</th>
                      <th>Est. GM at risk</th>
                      <th>Flag</th>
                    </tr>
                  </thead>
                  <tbody>
                    {q.data.items.map((s) => (
                      <tr key={s.supplier_id}>
                        <td className="product-cell">
                          <Link href={`/suppliers/${s.supplier_id}`}>
                            {s.reliability_rank}. {s.supplier_name}
                          </Link>
                          <small>
                            {s.supplier_code} · {s.category_name}
                          </small>
                        </td>
                        <td>{rate(s.on_time_rate)}</td>
                        <td>{rate(s.in_full_rate)}</td>
                        <td>
                          {decimal(s.mean_lead_time_days)} ±{" "}
                          {decimal(s.std_lead_time_days)} days
                        </td>
                        <td>{count(s.overdue_open_pos)}</td>
                        <td>{count(s.at_risk_positions)}</td>
                        <td>{money(s.margin_at_risk_usd)}</td>
                        <td>{s.review_flag ? "Review" : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!q.data.items.length && (
                  <p className="empty">
                    No suppliers match this scope. Clear the review-only filter
                    or change scope.
                  </p>
                )}
              </div>
            </Card>
          </div>
        </>
      )}
    </>
  );
}
export function SupplierDetail({ id }: { id: string }) {
  const q = useApi<Schema<"SupplierDetail">>(`/suppliers/${id}`);
  if (q.isPending) return <Loading />;
  if (q.isError)
    return (
      <>
        <Link href="/suppliers">← Suppliers</Link>
        <ErrorState error={q.error} retry={() => void q.refetch()} />
      </>
    );
  const d = q.data;
  return (
    <>
      <div className="breadcrumbs">
        <Link href="/suppliers">Suppliers</Link> / {d.supplier.supplier_code}
      </div>
      <div className="page-heading">
        <div>
          <h1>{d.supplier.supplier_name}</h1>
          <p>
            {d.supplier.category_name} ·{" "}
            {d.performance.review_flag
              ? "Delivery performance warrants review"
              : "Delivery performance"}
          </p>
        </div>
      </div>
      <div className="notice">{d.disclaimer}</div>
      <div className="grid-two" style={{ marginTop: 20 }}>
        <Card
          title="Weekly on-time deliveries"
          subtitle="Last 26 ISO weeks · grouped by promised date"
        >
          <div className="chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={d.weekly_on_time}>
                <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
                <XAxis
                  dataKey="week_start_date"
                  tickFormatter={(v) => date(String(v))}
                />
                <YAxis domain={[0, 1]} tickFormatter={rate} />
                <Tooltip
                  labelFormatter={(v) => date(String(v))}
                  formatter={(v, name) =>
                    name === "on_time_rate" ? rate(Number(v)) : String(v)
                  }
                />
                <Bar
                  isAnimationActive={false}
                  dataKey="on_time_rate"
                  name="On-time rate"
                  fill="var(--color-teal-600)"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <details>
            <summary>View weekly counts</summary>
            <div className="table-scroll" tabIndex={0}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Week</th>
                    <th>POs due</th>
                    <th>On-time rate</th>
                  </tr>
                </thead>
                <tbody>
                  {d.weekly_on_time.map((w) => (
                    <tr key={w.week_start_date}>
                      <td>{date(w.week_start_date)}</td>
                      <td>{count(w.pos_due)}</td>
                      <td>{rate(w.on_time_rate)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </Card>
        <Card
          title="Lead-time distribution"
          subtitle={`Received POs · mean contracted lead time ${days(d.contract_lead_time_days_avg)}`}
        >
          <div className="chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={d.lead_time_histogram}>
                <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
                <XAxis
                  type="number"
                  dataKey="lead_time_days"
                  domain={["dataMin", "dataMax"]}
                />
                <YAxis />
                <Tooltip />
                <Bar
                  isAnimationActive={false}
                  dataKey="pos"
                  name="Received POs"
                  fill="var(--color-navy)"
                />
                {d.contract_lead_time_days_avg !== null && (
                  <ReferenceLine
                    x={d.contract_lead_time_days_avg}
                    stroke="var(--color-amber-500)"
                    label="Contract"
                  />
                )}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
      <div className="stack">
        <Card title="Store lanes" subtitle="Store-level delivery performance">
          <div className="table-scroll" tabIndex={0}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Store</th>
                  <th>POs received · 180d</th>
                  <th>On time · 90d</th>
                  <th>Lead time ± SD</th>
                  <th>Overdue</th>
                </tr>
              </thead>
              <tbody>
                {d.lanes.map((l) => (
                  <tr key={l.store_id}>
                    <td>{l.store_code}</td>
                    <td>{count(l.pos_received_180d)}</td>
                    <td>{rate(l.on_time_rate)}</td>
                    <td>
                      {decimal(l.mean_lead_time_days)} ±{" "}
                      {decimal(l.std_lead_time_days)} days
                    </td>
                    <td>{count(l.overdue_open_pos)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <Card
          title="Exposed positions"
          subtitle="Moderate, High, and Critical · up to 50 positions"
        >
          <div className="table-scroll" tabIndex={0}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Store</th>
                  <th>Tier</th>
                  <th>Est. probability</th>
                  <th>Est. margin</th>
                </tr>
              </thead>
              <tbody>
                {d.exposed_positions.map((p) => (
                  <tr key={`${p.store_id}-${p.product_id}`}>
                    <td className="product-cell">
                      <Link href={`/positions/${p.store_id}/${p.product_id}`}>
                        {p.product_name}
                      </Link>
                      <small>{p.sku}</small>
                    </td>
                    <td>{p.store_id}</td>
                    <td>
                      <Tier tier={p.risk_tier} />
                    </td>
                    <td>
                      <Probability
                        value={p.stockout_probability}
                        tier={p.risk_tier}
                      />
                    </td>
                    <td>{money(p.margin_at_risk_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </>
  );
}
