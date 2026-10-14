"use client";
import type { Schema } from "@/lib/api/client";
import {
  formatCount,
  formatMoney,
  formatRate,
  formatDays,
  formatDecimal,
  formatDelta,
} from "@/lib/format";
type Metric = keyof Schema<"ScenarioMetrics">;
const groups: {
  title: string;
  metrics: {
    key: Metric;
    label: string;
    kind: "count" | "money" | "rate" | "days" | "units";
    polarity: "lower" | "investment";
  }[];
}[] = [
  {
    title: "Near-term risk · model estimates",
    metrics: [
      {
        key: "at_risk_positions",
        label: "At-risk positions",
        kind: "count",
        polarity: "lower",
      },
      {
        key: "mean_stockout_probability",
        label: "Mean stockout probability",
        kind: "rate",
        polarity: "lower",
      },
      {
        key: "expected_shortage_units",
        label: "Expected shortage units",
        kind: "units",
        polarity: "lower",
      },
      {
        key: "margin_at_risk_usd",
        label: "Est. gross margin at risk",
        kind: "money",
        polarity: "lower",
      },
      {
        key: "revenue_at_risk_usd",
        label: "Est. revenue at risk",
        kind: "money",
        polarity: "lower",
      },
    ],
  },
  {
    title: "Replenishment policy · model estimates",
    metrics: [
      {
        key: "positions_below_reorder_point",
        label: "Positions below reorder point",
        kind: "count",
        polarity: "lower",
      },
      {
        key: "lead_time_demand_units",
        label: "Lead-time demand units",
        kind: "units",
        polarity: "investment",
      },
      {
        key: "avg_lead_time_days",
        label: "Mean lead time",
        kind: "days",
        polarity: "lower",
      },
      {
        key: "recommended_order_units",
        label: "Recommended order units",
        kind: "units",
        polarity: "investment",
      },
      {
        key: "recommended_order_value_usd",
        label: "Recommended order value",
        kind: "money",
        polarity: "investment",
      },
      {
        key: "safety_stock_units",
        label: "Safety stock units",
        kind: "units",
        polarity: "investment",
      },
      {
        key: "safety_stock_value_usd",
        label: "Safety stock value",
        kind: "money",
        polarity: "investment",
      },
    ],
  },
  {
    title: "Annualized tradeoff · planning assumptions",
    metrics: [
      {
        key: "annual_carrying_cost_usd",
        label: "Annual carrying cost of safety stock",
        kind: "money",
        polarity: "lower",
      },
      {
        key: "annual_expected_shortfall_margin_usd",
        label: "Annual expected shortfall margin",
        kind: "money",
        polarity: "lower",
      },
    ],
  },
];
export function Comparison({
  data,
  carryingRate,
}: {
  data: Schema<"ScenarioResponse">;
  carryingRate: number;
}) {
  return (
    <>
      <div className="table-scroll">
        <table className="data-table comparison">
          <thead>
            <tr>
              <th>Metric</th>
              <th className="number">Baseline</th>
              <th className="number">Scenario</th>
              <th className="number">Δ</th>
              <th className="number">Δ %</th>
            </tr>
          </thead>
          <tbody>
            {groups.map((group) => (
              <Rows key={group.title} group={group} data={data} />
            ))}
          </tbody>
        </table>
      </div>
      <p className="chart-note">
        Annualized tradeoff uses a {formatRate(carryingRate)} carrying-cost
        assumption. More safety stock is an investment tradeoff, not
        automatically an improvement. Near-term risk describes inventory already
        on hand.
      </p>
    </>
  );
}
function Rows({
  group,
  data,
}: {
  group: (typeof groups)[number];
  data: Schema<"ScenarioResponse">;
}) {
  return (
    <>
      <tr>
        <th colSpan={5}>{group.title}</th>
      </tr>
      {group.title.startsWith("Near") && (
        <tr>
          <td>Critical positions</td>
          <td className="number">
            {formatCount(data.baseline.positions_by_tier.critical)}
          </td>
          <td className="number">
            {formatCount(data.scenario.positions_by_tier.critical)}
          </td>
          <td className="number">
            {formatDelta(
              data.scenario.positions_by_tier.critical -
                data.baseline.positions_by_tier.critical,
            )}
          </td>
          <td className="number">
            {data.baseline.positions_by_tier.critical
              ? formatRate(
                  (data.scenario.positions_by_tier.critical -
                    data.baseline.positions_by_tier.critical) /
                    data.baseline.positions_by_tier.critical,
                )
              : "—"}
          </td>
        </tr>
      )}
      {group.metrics.map((m) => {
        const b = data.baseline[m.key],
          s = data.scenario[m.key],
          delta = data.delta.absolute[m.key],
          relative = data.delta.relative[m.key];
        const format = (v: number) =>
          m.kind === "money"
            ? formatMoney(v, true)
            : m.kind === "rate"
              ? formatRate(v)
              : m.kind === "days"
                ? formatDays(v)
                : m.kind === "units"
                  ? formatDecimal(v)
                  : formatCount(v);
        return (
          <tr key={m.key} data-metric={m.key}>
            <td>{m.label}</td>
            <td className="number">{format(b)}</td>
            <td className={`number ${s !== b ? "changed" : ""}`}>
              {format(s)}
            </td>
            <td
              className={`number ${m.polarity === "lower" && delta !== 0 ? (delta < 0 ? "better" : "worse") : ""}`}
            >
              {m.kind === "rate"
                ? formatDelta(delta, "rate")
                : `${delta > 0 ? "+" : delta < 0 ? "−" : ""}${format(Math.abs(delta))}`}
            </td>
            <td className="number">
              {relative === null || relative === undefined
                ? "—"
                : `${relative > 0 ? "+" : ""}${formatRate(relative)}`}
            </td>
          </tr>
        );
      })}
    </>
  );
}
