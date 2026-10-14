"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";
import { useApi } from "@/lib/api/hooks";
import { ApiError, type Schema } from "@/lib/api/client";
import {
  formatCount as count,
  formatMoney as money,
  formatPrice,
  formatRate as rate,
  formatProbability as probability,
  formatDays as days,
  formatDecimal as decimal,
  formatDate as date,
  formatLabel as label,
} from "@/lib/format";
import {
  Card,
  Tier,
  Probability,
  Action,
  Kpi,
  Loading,
  ErrorState,
} from "./shared/ui";
import { QueryPanel } from "./shared/query-panel";
function Breakdown({ values }: { values: Record<string, string> }) {
  return (
    <dl>
      {Object.entries(values).map(([k, v]) => (
        <div className="breakdown-row" key={k}>
          <dt>{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}
export function PositionDetail({
  storeId,
  productId,
}: {
  storeId: string;
  productId: string;
}) {
  const base = `/positions/${storeId}/${productId}`;
  const q = useApi<Schema<"PositionDetail">>(base);
  const params = useSearchParams();
  const [copied, setCopied] = useState("Copy summary");
  const returnPath = params.get("return");
  const back = returnPath?.startsWith("/risk?") ? returnPath : "/risk";
  if (q.isPending)
    return <Loading label="Loading position and recommendation…" />;
  if (q.isError)
    return (
      <>
        <Link href={back}>← Back to Risk Monitor</Link>
        {q.error instanceof ApiError && q.error.status === 404 ? (
          <div className="empty">
            <h1>Position not found</h1>
            <p>This store–SKU position is not part of the current run.</p>
          </div>
        ) : (
          <ErrorState error={q.error} retry={() => void q.refetch()} />
        )}
      </>
    );
  const d = q.data;
  return (
    <>
      <div className="breadcrumbs">
        <Link href={back}>Risk Monitor</Link>
        <span>/</span>
        <span>
          {d.store.store_code} {d.store.store_name}
        </span>
        <span>/</span>
        <code>{d.product.sku}</code>
      </div>
      <div className="page-heading">
        <div>
          <h1>{d.product.product_name}</h1>
          <p>
            <code>{d.product.sku}</code> · {d.product.category_name} ·{" "}
            {d.supplier.supplier_name} · {formatPrice(d.product.unit_price_usd)}{" "}
            / unit
          </p>
        </div>
        <div className="detail-actions">
          <Tier tier={d.risk.risk_tier} />
          <button
            onClick={() =>
              void navigator.clipboard
                .writeText(
                  `${d.product.product_name} · ${d.store.store_code}\n${d.risk.explanation}\n${d.recommendation.rationale}`,
                )
                .then(() => setCopied("Copied"))
                .catch(() => setCopied("Copy unavailable"))
            }
          >
            {copied}
          </button>
        </div>
      </div>
      <div className="grid-main">
        <Card
          title={
            d.risk.risk_tier === "low"
              ? "Current risk assessment"
              : "Why this is at risk"
          }
          subtitle="Model estimate · descriptive associations"
        >
          <p className="explanation">{d.risk.explanation}</p>
          <div className="driver-list">
            {d.risk.drivers.map((x) => (
              <span key={x.code} title={x.description}>
                {x.label}
              </span>
            ))}
          </div>
          <div className="callout">
            <h3>
              Recommended:{" "}
              <Action
                action={d.recommendation.action_type}
                units={d.recommendation.recommended_order_units}
              />
            </h3>
            {d.recommendation.recommended_order_units !== null && (
              <p>
                {d.recommendation.action_type === "expedite_po"
                  ? "Additional reorder: "
                  : "Order: "}
                {count(d.recommendation.recommended_order_units)} units ·{" "}
                {count(d.recommendation.recommended_order_cases ?? 0)} cases ·{" "}
                {money(d.recommendation.recommended_order_cost_usd ?? 0)}{" "}
                estimated purchase cost
              </p>
            )}
            {d.recommendation.related_purchase_order && (
              <p>
                Existing purchase order:{" "}
                <code>{d.recommendation.related_purchase_order.po_number}</code>
              </p>
            )}
            <p>{d.recommendation.rationale}</p>
          </div>
        </Card>
        <Card title="Key numbers" subtitle="As-of inventory and estimated risk">
          <div className="detail-kpis">
            <Kpi
              label="Est. stockout probability"
              value={probability(d.risk.stockout_probability)}
              definition="probability"
            />
            <Kpi
              label="Est. gross margin at risk"
              value={money(d.exposure.margin_at_risk_usd)}
              definition="margin"
            />
            <Kpi
              label="Days of cover"
              value={days(d.inventory.days_of_cover)}
              definition="cover"
            />
          </div>
          <p className="chart-note">
            Next replenishment:{" "}
            {d.inventory.next_receipt
              ? `${date(d.inventory.next_receipt.date)} · ${d.inventory.next_receipt.po_number}${d.inventory.next_receipt.overdue ? " · Overdue" : ""}`
              : "None on order"}
          </p>
        </Card>
      </div>
      <div className="stack">
        <Card
          title="Inventory projection"
          subtitle="Observed inventory → estimated stock · approximate 80% demand band"
        >
          <QueryPanel<Schema<"PositionProjection">> path={`${base}/projection`}>
            {(p) => {
              const points = p.points.map((x) =>
                x.kind === "actual"
                  ? { date: x.date, actual: x.on_hand_units }
                  : {
                      date: x.date,
                      expected: x.expected_on_hand_units,
                      band: [x.band_low_units, x.band_high_units],
                    },
              );
              return (
                <>
                  <div
                    className="chart"
                    role="img"
                    aria-label="Inventory projection with reorder point, safety stock, and stockout date"
                  >
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={points}>
                        <CartesianGrid
                          vertical={false}
                          stroke="var(--chart-grid)"
                        />
                        <XAxis
                          dataKey="date"
                          tickFormatter={(v) => date(String(v))}
                          minTickGap={45}
                        />
                        <YAxis
                          domain={[
                            0,
                            (max: number) =>
                              Math.max(
                                max,
                                p.reorder_point_units,
                                p.safety_stock_units,
                              ),
                          ]}
                        />
                        <Tooltip labelFormatter={(v) => date(String(v))} />
                        <Area
                          isAnimationActive={false}
                          dataKey="band"
                          name="Approx. 80% band"
                          fill="var(--color-teal-600)"
                          fillOpacity={0.12}
                          stroke="none"
                        />
                        <Line
                          isAnimationActive={false}
                          dataKey="actual"
                          name="Actual on hand"
                          type="stepAfter"
                          dot={false}
                          stroke="var(--color-navy)"
                          strokeWidth={2}
                        />
                        <Line
                          isAnimationActive={false}
                          dataKey="expected"
                          name="Est. on hand"
                          dot={false}
                          stroke="var(--color-teal-600)"
                          strokeDasharray="5 3"
                          strokeWidth={2}
                        />
                        <ReferenceLine
                          x={p.as_of_date}
                          stroke="var(--color-ink-400)"
                          label="As of"
                        />
                        <ReferenceLine
                          y={p.reorder_point_units}
                          stroke="var(--color-ink-400)"
                          strokeDasharray="4 4"
                          label="Reorder point"
                        />
                        <ReferenceLine
                          y={p.safety_stock_units}
                          stroke="var(--color-amber-500)"
                          strokeDasharray="4 4"
                          label="Safety stock"
                        />
                        {p.projected_stockout_date && (
                          <ReferenceLine
                            x={p.projected_stockout_date}
                            stroke="var(--critical)"
                            label="Est. stockout"
                          />
                        )}
                        {p.receipts.map((r) => (
                          <ReferenceLine
                            key={`${r.date}-${r.purchase_order_id}`}
                            x={r.date}
                            stroke="var(--color-teal-600)"
                            strokeDasharray="2 6"
                          />
                        ))}
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                  <p className="chart-note">
                    Projected stockout:{" "}
                    {p.projected_stockout_date
                      ? date(p.projected_stockout_date, true)
                      : "None within the forecast horizon"}
                    . {p.notes}
                  </p>
                </>
              );
            }}
          </QueryPanel>
        </Card>
        <div className="grid-main">
          <div className="stack">
            <Card
              title="Sales history & demand forecast"
              subtitle="56 observed days · 28 forecast days · amber bars indicate censored sales"
            >
              <QueryPanel<Schema<"PositionHistory">>
                path={`${base}/history?days=56`}
              >
                {(h) => (
                  <>
                    <div
                      className="chart"
                      role="img"
                      aria-label="Observed sales with censored days and forecast demand"
                    >
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={[...h.days, ...h.forecast]}>
                          <defs>
                            <pattern
                              id="censored"
                              patternUnits="userSpaceOnUse"
                              width="6"
                              height="6"
                            >
                              <rect
                                width="6"
                                height="6"
                                fill="var(--color-amber-50)"
                              />
                              <path
                                d="M0 6L6 0"
                                stroke="var(--color-amber-500)"
                              />
                            </pattern>
                          </defs>
                          <CartesianGrid
                            vertical={false}
                            stroke="var(--chart-grid)"
                          />
                          <XAxis
                            dataKey="date"
                            tickFormatter={(v) => date(String(v))}
                            minTickGap={45}
                          />
                          <YAxis />
                          <Tooltip labelFormatter={(v) => date(String(v))} />
                          <Bar
                            isAnimationActive={false}
                            dataKey="units_sold"
                            name="Observed units sold"
                          >
                            {h.days.map((day) => (
                              <Cell
                                key={day.date}
                                fill={
                                  day.is_censored
                                    ? "url(#censored)"
                                    : "var(--color-navy)"
                                }
                              />
                            ))}
                          </Bar>
                          <Line
                            isAnimationActive={false}
                            dataKey="forecast_units"
                            name="Est. demand"
                            stroke="var(--color-teal-600)"
                            dot={false}
                            strokeWidth={2}
                          />
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                    <p className="chart-note">
                      {count(h.days.filter((x) => x.is_censored).length)}{" "}
                      censored days: observed sales can understate demand. No
                      hidden simulation demand is used.
                    </p>
                    <details>
                      <summary>View observed daily data</summary>
                      <div className="table-scroll">
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>Date</th>
                              <th>Sold</th>
                              <th>Availability</th>
                              <th>Promotion</th>
                            </tr>
                          </thead>
                          <tbody>
                            {h.days.map((x) => (
                              <tr key={x.date}>
                                <td>{date(x.date)}</td>
                                <td>{count(x.units_sold)}</td>
                                <td>{label(x.availability_status)}</td>
                                <td>{x.promotion_name ?? "—"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </details>
                  </>
                )}
              </QueryPanel>
            </Card>
            <Card
              title="Purchase orders"
              subtitle="Existing orders only · quantities known at the analytics cutoff"
            >
              <QueryPanel<Schema<"PositionOrders">>
                path={`${base}/purchase-orders`}
              >
                {(orders) => (
                  <div className="table-scroll">
                    {!orders.open.length && !orders.recent_received.length ? (
                      <p>No open or recent purchase orders.</p>
                    ) : (
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>PO number</th>
                            <th>Ordered</th>
                            <th>Promised</th>
                            <th>Est. arrival / received</th>
                            <th>Qty ordered</th>
                            <th>Received</th>
                            <th>Open</th>
                            <th>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {[...orders.open, ...orders.recent_received].map(
                            (o) => (
                              <tr key={o.purchase_order_id}>
                                <td className="mono">{o.po_number}</td>
                                <td>{date(o.order_date)}</td>
                                <td>{date(o.promised_delivery_date)}</td>
                                <td>
                                  {date(
                                    "expected_arrival_date" in o
                                      ? o.expected_arrival_date
                                      : o.first_receipt_date,
                                  )}
                                </td>
                                <td>{count(o.quantity_ordered)}</td>
                                <td>{count(o.quantity_received)}</td>
                                <td>
                                  {"open_quantity" in o
                                    ? count(o.open_quantity)
                                    : "—"}
                                </td>
                                <td>
                                  {"overdue" in o && o.overdue
                                    ? "Overdue · "
                                    : ""}
                                  {label(o.status)}
                                </td>
                              </tr>
                            ),
                          )}
                        </tbody>
                      </table>
                    )}
                  </div>
                )}
              </QueryPanel>
            </Card>
          </div>
          <Card
            title="Risk calculation"
            subtitle="Stored model inputs and outputs"
            className="breakdown"
          >
            <h3>Inventory</h3>
            <Breakdown
              values={{
                "On hand": count(d.inventory.on_hand_units),
                "On order": count(d.inventory.on_order_units),
                "Inventory position": count(
                  d.inventory.inventory_position_units,
                ),
              }}
            />
            <h3>Demand · model estimate</h3>
            <Breakdown
              values={{
                "Daily demand": `${decimal(d.demand.avg_daily_demand_units)} units/day`,
                "Daily standard deviation": decimal(
                  d.demand.daily_demand_std_units,
                ),
                "Forecast method": label(d.demand.forecast_method),
                Pattern: label(d.demand.demand_pattern),
                "Clean / censored days": `${d.demand.clean_days} / ${d.demand.censored_days}`,
                "7 / 14 / 28-day forecast": `${decimal(d.demand.forecast_7d_units)} / ${decimal(d.demand.forecast_14d_units)} / ${decimal(d.demand.forecast_28d_units)}`,
              }}
            />
            <h3>Supply</h3>
            <Breakdown
              values={{
                "Lead time": `${decimal(d.supply.lead_time_mean_days)} ± ${decimal(d.supply.lead_time_std_days)} days`,
                "Estimate source": label(d.supply.lead_time_source),
                "Received POs": count(d.supply.n_received_pos),
                "Lane on-time rate": rate(d.supply.on_time_rate),
                "Protection window": days(d.supply.protection_window_days),
              }}
            />
            <h3>Policy · model estimate</h3>
            <Breakdown
              values={{
                "Cycle service level": rate(d.policy.service_level),
                "Safety stock": decimal(d.policy.safety_stock_units),
                "Reorder point": count(d.policy.reorder_point_units),
                "Target stock": count(d.policy.order_up_to_units),
                "Lead-time demand": `${decimal(d.policy.lead_time_demand_mean_units)} ± ${decimal(d.policy.lead_time_demand_std_units)}`,
              }}
            />
            <h3>Exposure · model estimate</h3>
            <Breakdown
              values={{
                "Expected shortage": decimal(
                  d.exposure.expected_shortage_units,
                ),
                "Lost-sale assumption": rate(d.exposure.lost_sale_rate),
                "Expected lost units": decimal(d.exposure.expected_lost_units),
                "Revenue at risk": money(d.exposure.revenue_at_risk_usd),
                "Gross margin at risk": money(d.exposure.margin_at_risk_usd),
              }}
            />
          </Card>
        </div>
        <Card
          title="Sensitivity"
          subtitle="One input changed at a time · model estimates"
        >
          <QueryPanel<Schema<"Sensitivity">> path={`${base}/sensitivity`}>
            {(s) => (
              <>
                <div className="tier-list">
                  {s.scenarios.map((x) => (
                    <div className="tier-row" key={x.key}>
                      <span>{x.label}</span>
                      <span className="number">
                        {probability(x.stockout_probability)}{" "}
                        <small>vs {probability(s.baseline_probability)}</small>
                      </span>
                    </div>
                  ))}
                </div>
                <p className="chart-note">{s.note}</p>
              </>
            )}
          </QueryPanel>
        </Card>
        <Card
          title="How the probability was computed"
          subtitle="Binding checkpoint determines the displayed probability"
        >
          <details>
            <summary>Inspect demand and supply checkpoints</summary>
            <p className="formula">
              <code>
                {d.policy.distribution_family === "normal"
                  ? "P(stockout) = 1 − Φ((supply − μ) / σ)"
                  : "Count-family tail probability: P(demand > supply)"}
              </code>
            </p>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Checkpoint</th>
                    <th>Window</th>
                    <th>Supply</th>
                    <th>Demand μ ± σ</th>
                    <th>Distribution</th>
                    <th>Est. probability</th>
                    <th>Binding</th>
                  </tr>
                </thead>
                <tbody>
                  {d.checkpoints.map((c) => (
                    <tr key={c.checkpoint_seq}>
                      <td>{label(c.checkpoint_type)}</td>
                      <td>{days(c.window_days)}</td>
                      <td>{count(c.supply_units)}</td>
                      <td>
                        {decimal(c.demand_mean_units)} ±{" "}
                        {decimal(c.demand_std_units)}
                      </td>
                      <td>{label(c.distribution_family)}</td>
                      <td>
                        <Probability
                          value={c.stockout_probability}
                          tier={d.risk.risk_tier}
                        />
                      </td>
                      <td>{c.is_binding ? "Yes" : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </Card>
      </div>
    </>
  );
}
