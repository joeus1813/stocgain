"use client";
import Link from "next/link";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
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
  formatDate as date,
  formatDelta,
} from "@/lib/format";
import {
  Kpi,
  Card,
  Tier,
  Probability,
  Action,
  Empty,
  ErrorState,
  Loading,
} from "./shared/ui";
import { QueryPanel } from "./shared/query-panel";
import { ForecastEvaluation } from "./forecast-evaluation";
import { HealthStatus } from "./health-status";
export function OverviewDashboard() {
  const params = useSearchParams(),
    router = useRouter();
  const { update } = useUrlState();
  const [trend, setTrend] = useState<"positions" | "margin">("positions");
  const scope = globalQuery(new URLSearchParams(params.toString()));
  const filters = apiFilters(new URLSearchParams(scope)).toString();
  const endpoint = (name: string) => `/overview/${name}?${filters}`;
  const summary = useApi<Schema<"OverviewSummary">>(endpoint("summary"));
  const riskHref = (extra: Record<string, string> = {}) => {
    const p = new URLSearchParams(scope);
    for (const [k, v] of Object.entries(extra)) p.set(k, v);
    return `/risk?${p}`;
  };
  if (summary.isPending) return <Loading label="Loading inventory overview…" />;
  if (summary.isError)
    return (
      <ErrorState error={summary.error} retry={() => void summary.refetch()} />
    );
  const d = summary.data;
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">Inventory intelligence</div>
          <h1>Your inventory, in perspective.</h1>
          <p>Where risk is concentrated. What needs attention next.</p>
        </div>
        <Link
          className="button-link"
          href={riskHref({ tier: "critical,high" })}
        >
          Review at-risk positions →
        </Link>
      </div>
      {!d.active_positions ? (
        <Empty />
      ) : (
        <>
          <section aria-label="Inventory overview">
            <div className="kpi-grid">
              <Kpi
                label="Active positions"
                value={count(d.active_positions)}
                note={`${count(d.active_skus)} distinct SKUs`}
                definition="active"
              />
              <Kpi
                label="At-risk positions"
                value={count(d.at_risk_positions)}
                note={`${rate(d.at_risk_rate)} · ${count(d.critical_positions)} critical${d.at_risk_positions_change === null ? "" : ` · ${formatDelta(d.at_risk_positions_change)} vs prior week`}`}
                definition="risk"
                href={riskHref({ tier: "critical,high" })}
              />
              <Kpi
                label="Est. gross margin at risk"
                value={money(d.gross_margin_at_risk_usd, true)}
                note={`${money(d.revenue_at_risk_usd, true)} est. revenue`}
                definition="margin"
              />
              <Kpi
                label="Median days of cover"
                value={days(d.median_days_of_cover)}
                note="Across positions with demand"
                definition="cover"
              />
              <Kpi
                label="Supplier on-time rate"
                value={rate(d.supplier_on_time_rate)}
                note={`${d.supplier_on_time_window_days} days · ${count(d.supplier_pos_due)} POs`}
                definition="supplier"
              />
              <Kpi
                label="End-of-day in-stock rate"
                value={rate(d.in_stock_rate)}
                note={`${d.in_stock_window_days} days${d.in_stock_rate !== null && d.in_stock_rate_prior !== null ? ` · ${formatDelta(d.in_stock_rate - d.in_stock_rate_prior, "rate")} vs prior` : ""}`}
                definition="stock"
              />
            </div>
          </section>
          <div className="grid-main">
            <Card
              title="Priority actions"
              subtitle="Ranked by urgency and estimated exposure"
              actions={
                <Link
                  href={riskHref({
                    action: "expedite_po,reorder,monitor",
                    sort: "priority",
                  })}
                >
                  View all →
                </Link>
              }
            >
              <QueryPanel<Schema<"Recommendations">>
                path={`/recommendations?limit=10&${filters}`}
              >
                {(data) =>
                  data.items.length ? (
                    <div className="table-scroll" tabIndex={0}>
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>#</th>
                            <th>Product / store</th>
                            <th>Tier</th>
                            <th>Est. probability</th>
                            <th className="number">Est. margin</th>
                            <th>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.items.map((r) => (
                            <tr key={`${r.store_id}-${r.product_id}`}>
                              <td className="muted">{r.priority_rank}</td>
                              <td className="product-cell">
                                <Link
                                  href={`/positions/${r.store_id}/${r.product_id}?${scope}`}
                                >
                                  {r.product_name}
                                </Link>
                                <small>
                                  {r.sku} · {r.store_code}
                                </small>
                              </td>
                              <td>
                                <Tier tier={r.risk_tier} />
                              </td>
                              <td>
                                <Probability
                                  value={r.stockout_probability}
                                  tier={r.risk_tier}
                                />
                              </td>
                              <td className="number">
                                {money(r.margin_at_risk_usd)}
                              </td>
                              <td>
                                <Action
                                  action={r.action_type}
                                  units={r.recommended_order_units}
                                />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <Empty title="No actions recommended in this scope" />
                  )
                }
              </QueryPanel>
            </Card>
            <Card
              title="Risk distribution"
              subtitle="Share of positions · model estimate"
            >
              <QueryPanel<Schema<"RiskDistribution">>
                path={endpoint("risk-distribution")}
              >
                {(data) => (
                  <>
                    <div className="risk-bar">
                      {data.tiers.map((t) => (
                        <Link
                          aria-label={`${t.risk_tier} risk positions`}
                          key={t.risk_tier}
                          href={riskHref({ tier: t.risk_tier })}
                          style={{
                            width: `${t.share_of_positions * 100}%`,
                            background: `var(--${t.risk_tier})`,
                          }}
                        />
                      ))}
                    </div>
                    <div className="tier-list">
                      {data.tiers.map((t) => (
                        <Link
                          className="tier-row"
                          key={t.risk_tier}
                          href={riskHref({ tier: t.risk_tier })}
                        >
                          <Tier tier={t.risk_tier} />
                          <span className="number">{count(t.positions)}</span>
                          <small>{money(t.margin_at_risk_usd, true)}</small>
                        </Link>
                      ))}
                    </div>
                    <p className="chart-note">
                      At risk = Critical + High. Exposure is an estimate, not
                      realized loss.
                    </p>
                  </>
                )}
              </QueryPanel>
            </Card>
          </div>
          <div className="grid-main">
            <Card
              title="Risk over time"
              subtitle="Weekly historical runs · point-in-time estimates"
              actions={
                <div className="segmented">
                  <button
                    aria-pressed={trend === "positions"}
                    onClick={() => setTrend("positions")}
                  >
                    Positions
                  </button>
                  <button
                    aria-pressed={trend === "margin"}
                    onClick={() => setTrend("margin")}
                  >
                    Est. margin
                  </button>
                </div>
              }
            >
              <QueryPanel<Schema<"RiskTrend">> path={endpoint("risk-trend")}>
                {(data) => (
                  <div
                    className="chart"
                    role="img"
                    aria-label="Historical risk trend"
                  >
                    <ResponsiveContainer width="100%" height="100%">
                      {trend === "positions" ? (
                        <AreaChart data={data.points}>
                          <CartesianGrid
                            vertical={false}
                            stroke="var(--chart-grid)"
                          />
                          <XAxis
                            dataKey="as_of_date"
                            tickFormatter={(v) => date(String(v))}
                            axisLine={false}
                            tickLine={false}
                          />
                          <YAxis axisLine={false} tickLine={false} />
                          <Tooltip labelFormatter={(v) => date(String(v))} />
                          <Area
                            isAnimationActive={false}
                            dataKey="critical"
                            name="Critical"
                            stackId="risk"
                            stroke="var(--critical)"
                            fill="var(--critical)"
                            fillOpacity={0.12}
                          />
                          <Area
                            isAnimationActive={false}
                            dataKey="high"
                            name="High"
                            stackId="risk"
                            stroke="var(--high)"
                            fill="var(--high)"
                            fillOpacity={0.12}
                          />
                        </AreaChart>
                      ) : (
                        <LineChart data={data.points}>
                          <CartesianGrid
                            vertical={false}
                            stroke="var(--chart-grid)"
                          />
                          <XAxis
                            dataKey="as_of_date"
                            tickFormatter={(v) => date(String(v))}
                          />
                          <YAxis
                            tickFormatter={(v) => money(Number(v), true)}
                            width={65}
                          />
                          <Tooltip formatter={(v) => money(Number(v))} />
                          <Line
                            isAnimationActive={false}
                            type="monotone"
                            dataKey="margin_at_risk_usd"
                            name="Est. margin at risk"
                            stroke="var(--color-teal-600)"
                            strokeWidth={2}
                            dot={false}
                          />
                        </LineChart>
                      )}
                    </ResponsiveContainer>
                  </div>
                )}
              </QueryPanel>
            </Card>
            <Card
              title="Top at-risk products"
              subtitle="Exposure across the store network"
            >
              <QueryPanel<Schema<"TopProducts">>
                path={`${endpoint("top-products")}&limit=8`}
              >
                {(data) => (
                  <div className="ranked-list">
                    {data.items.map((p, i) => (
                      <Link key={p.product_id} href={riskHref({ q: p.sku })}>
                        <span className="rank">{i + 1}</span>
                        <span>
                          {p.product_name}
                          <small>
                            {p.at_risk_stores} at-risk stores ·{" "}
                            {money(p.margin_at_risk_usd, true)} est. margin
                          </small>
                        </span>
                      </Link>
                    ))}
                  </div>
                )}
              </QueryPanel>
            </Card>
          </div>
          <div className="grid-two">
            <Card
              title="Store comparison"
              subtitle="Est. gross margin at risk · click a store to focus"
            >
              <QueryPanel<Schema<"StoreComparison">>
                path={endpoint("store-comparison")}
              >
                {(data) => (
                  <>
                    <div
                      className="chart"
                      role="img"
                      aria-label="Estimated margin at risk by store"
                    >
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          layout="vertical"
                          data={data.stores}
                          margin={{ left: 0, right: 20 }}
                        >
                          <CartesianGrid
                            horizontal={false}
                            stroke="var(--chart-grid)"
                          />
                          <XAxis
                            type="number"
                            tickFormatter={(v) => money(Number(v), true)}
                            axisLine={false}
                          />
                          <YAxis
                            type="category"
                            dataKey="store_code"
                            width={40}
                            axisLine={false}
                            tickLine={false}
                          />
                          <Tooltip formatter={(v) => money(Number(v))} />
                          <Bar
                            isAnimationActive={false}
                            dataKey="margin_at_risk_usd"
                            name="Est. margin at risk"
                            fill="var(--color-teal-600)"
                            radius={[0, 3, 3, 0]}
                            onClick={(_, i) =>
                              update({ store: String(data.stores[i].store_id) })
                            }
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="store-links">
                      {data.stores.map((s) => (
                        <button
                          key={s.store_id}
                          onClick={() => update({ store: String(s.store_id) })}
                        >
                          {s.store_code} · {count(s.at_risk_positions)} at risk
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </QueryPanel>
            </Card>
            <Card
              title="Category × store"
              subtitle="At-risk positions · color indicates share of positions"
            >
              <QueryPanel<Schema<"CategoryHeatmap">>
                path={endpoint("category-heatmap")}
              >
                {(data) => (
                  <div className="table-scroll" tabIndex={0}>
                    <table className="data-table heatmap">
                      <thead>
                        <tr>
                          <th>Category</th>
                          {data.stores.map((s) => (
                            <th key={s.store_id}>{s.store_code}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {data.categories.map((c) => (
                          <tr key={c.category_id}>
                            <th>{c.category_name}</th>
                            {data.stores.map((s) => {
                              const cell = data.cells.find(
                                (x) =>
                                  x.category_id === c.category_id &&
                                  x.store_id === s.store_id,
                              );
                              if (!cell) return <td key={s.store_id}>—</td>;
                              const level = cell.at_risk_rate;
                              return (
                                <td key={s.store_id}>
                                  <button
                                    aria-label={`${c.category_name}, ${s.store_code}: ${cell.at_risk_positions} at risk`}
                                    title={`${rate(level)} at risk · ${money(cell.margin_at_risk_usd)} est. margin`}
                                    style={{
                                      background:
                                        level === 0
                                          ? "var(--color-surface)"
                                          : level < 0.1
                                            ? "var(--heat-1)"
                                            : level < 0.25
                                              ? "var(--heat-2)"
                                              : level < 0.5
                                                ? "var(--high)"
                                                : "var(--critical-fg)",
                                      color:
                                        level >= 0.5
                                          ? "var(--color-surface)"
                                          : "var(--color-ink-900)",
                                    }}
                                    onClick={() =>
                                      router.push(
                                        riskHref({
                                          store: String(s.store_id),
                                          category: String(c.category_id),
                                          tier: "critical,high",
                                        }),
                                      )
                                    }
                                  >
                                    {cell.at_risk_positions}
                                  </button>
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </QueryPanel>
            </Card>
          </div>
        </>
      )}
      <ForecastEvaluation compact />
      <details className="service-health">
        <summary>Service health</summary>
        <HealthStatus />
      </details>
    </>
  );
}
