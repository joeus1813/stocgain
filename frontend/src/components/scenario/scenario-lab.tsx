"use client";
import Link from "next/link";
import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { useMeta, useApi } from "@/lib/api/hooks";
import { request, type Schema } from "@/lib/api/client";
import {
  formatCount as count,
  formatMoney as money,
  formatRate as rate,
  formatProbability as probability,
  formatLabel as label,
  formatDelta,
  formatDecimal,
} from "@/lib/format";
import { Card, Loading, ErrorState, Empty, Tier } from "../shared/ui";
import { MultiSelect } from "../layout/filter-bar";
import { AssumptionControl } from "./assumption-control";
import { Comparison } from "./comparison";
export function ScenarioLab() {
  const meta = useMeta();
  if (meta.isPending) return <Loading />;
  if (meta.isError)
    return <ErrorState error={meta.error} retry={() => void meta.refetch()} />;
  if (!meta.data.run)
    return <Empty title="Analytics are not ready. Run make analytics." />;
  return <ScenarioForm key={meta.data.run.run_id} meta={meta.data} />;
}
function ScenarioForm({ meta }: { meta: Schema<"Meta"> }) {
  const params = useSearchParams(),
    router = useRouter();
  const filters = useApi<Schema<"FiltersResponse">>("/filters");
  const defaultSl = String(meta.parameters.service_level * 100);
  const [values, setValues] = useState(() => ({
    lt: params.get("lt") ?? "0",
    dem: params.get("dem") ?? "0",
    sl: params.get("sl") ?? defaultSl,
    buf: params.get("buf") ?? "0",
    store: params.get("store") ?? "",
    category: params.get("category") ?? "",
    supplier: params.get("supplier") ?? "",
  }));
  const [debounced, setDebounced] = useState(values);
  const limits = meta.parameters.scenario_limits;
  const controls = [
    {
      key: "lt",
      label: "Supplier lead time change",
      min: limits.lead_time_change_days[0],
      max: limits.lead_time_change_days[1],
      step: 1,
      base: "0",
    },
    {
      key: "dem",
      label: "Demand change (%)",
      min: limits.demand_change_rate[0] * 100,
      max: limits.demand_change_rate[1] * 100,
      step: 5,
      base: "0",
    },
    {
      key: "sl",
      label: "Service level (%)",
      min: limits.service_level[0] * 100,
      max: limits.service_level[1] * 100,
      step: 0.5,
      base: defaultSl,
    },
    {
      key: "buf",
      label: "Safety stock buffer (%)",
      min: limits.safety_stock_buffer_rate[0] * 100,
      max: limits.safety_stock_buffer_rate[1] * 100,
      step: 5,
      base: "0",
    },
  ] as const;
  const valid = controls.every(
    (c) =>
      values[c.key] !== "" &&
      Number.isFinite(Number(values[c.key])) &&
      Number(values[c.key]) >= c.min &&
      Number(values[c.key]) <= c.max &&
      (c.key !== "lt" || Number.isInteger(Number(values[c.key]))),
  );
  const serialized = JSON.stringify(values),
    settled = JSON.stringify(debounced);
  useEffect(() => {
    if (!valid) return;
    const timer = setTimeout(() => {
      setDebounced(values);
      const p = new URLSearchParams();
      for (const [key, value] of Object.entries(values))
        if (value) p.set(key, value);
      router.replace(`/scenarios?${p}`, { scroll: false });
    }, 400);
    return () => clearTimeout(timer);
  }, [serialized, valid, router, values]);
  const ids = (v: string) => (v ? v.split(",").map(Number) : null);
  const body: Schema<"ScenarioRequest"> = {
    scope: {
      store_ids: ids(debounced.store),
      category_ids: ids(debounced.category),
      supplier_ids: ids(debounced.supplier),
    },
    assumptions: {
      lead_time_change_days: Number(debounced.lt),
      demand_change_rate: Number(debounced.dem) / 100,
      service_level: Number(debounced.sl) / 100,
      safety_stock_buffer_rate: Number(debounced.buf) / 100,
    },
  };
  const query = useQuery({
    queryKey: ["scenario", meta.run?.run_id, settled],
    queryFn: ({ signal }) =>
      request<Schema<"ScenarioResponse">>("/scenarios/evaluate", signal, body),
    enabled: valid,
    placeholderData: keepPreviousData,
    retry: false,
    staleTime: 30000,
  });
  const changed =
    controls.some((c) => Number(values[c.key]) !== Number(c.base)) ||
    !!(values.store || values.category || values.supplier);
  const reset = () =>
    setValues({
      lt: "0",
      dem: "0",
      sl: defaultSl,
      buf: "0",
      store: "",
      category: "",
      supplier: "",
    });
  const data = query.data;
  const busy = query.isFetching || serialized !== settled;
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">What-if analysis</div>
          <h1>Scenario Lab</h1>
          <p>
            Recalculate risk and replenishment using the same model as the
            dashboard.
          </p>
        </div>
        <span className="model-label">Model estimates · Nothing is saved</span>
      </div>
      <div className="scenario-layout">
        <aside className="card assumptions">
          <details className="assumption-disclosure" open>
            <summary>
              <h2>Assumptions</h2>
            </summary>
            <p className="chart-note">
              Changes apply only to the selected scope.
            </p>
            <div style={{ marginTop: 20 }}>
              <MultiSelect
                label="Stores"
                value={values.store}
                options={
                  filters.data?.stores.map((s) => ({
                    id: s.store_id,
                    label: `${s.store_code} · ${s.store_name}`,
                  })) ?? []
                }
                onChange={(v) => setValues({ ...values, store: v })}
              />
              <MultiSelect
                label="Categories"
                value={values.category}
                options={
                  filters.data?.categories.map((s) => ({
                    id: s.category_id,
                    label: s.category_name,
                  })) ?? []
                }
                onChange={(v) => setValues({ ...values, category: v })}
              />
              <MultiSelect
                label="Suppliers"
                value={values.supplier}
                options={
                  filters.data?.suppliers.map((s) => ({
                    id: s.supplier_id,
                    label: s.supplier_name,
                  })) ?? []
                }
                onChange={(v) => setValues({ ...values, supplier: v })}
              />
            </div>
            <p className="chart-note">
              {data
                ? `${count(data.positions_in_scope)} positions in scope`
                : "Loading baseline scope…"}
            </p>
            {controls.map((c) => (
              <AssumptionControl
                key={c.key}
                label={c.label}
                min={c.min}
                max={c.max}
                step={c.step}
                value={values[c.key]}
                changed={Number(values[c.key]) !== Number(c.base)}
                onChange={(value) => setValues({ ...values, [c.key]: value })}
              />
            ))}
            <div className="presets">
              <button
                onClick={() =>
                  setValues({
                    ...values,
                    lt: "4",
                    dem: "20",
                    sl: defaultSl,
                    buf: "0",
                  })
                }
              >
                Supplier disruption
              </button>
              <button
                onClick={() =>
                  setValues({
                    ...values,
                    lt: "0",
                    dem: "30",
                    sl: defaultSl,
                    buf: "0",
                  })
                }
              >
                Demand surge
              </button>
              <button
                onClick={() =>
                  setValues({
                    ...values,
                    lt: "0",
                    dem: "0",
                    sl: "98",
                    buf: "0",
                  })
                }
              >
                Higher service
              </button>
              <button
                onClick={() =>
                  setValues({
                    ...values,
                    lt: "0",
                    dem: "0",
                    sl: "90",
                    buf: "-20",
                  })
                }
              >
                Lean inventory
              </button>
            </div>
            <button
              className="reset-scenario"
              disabled={!changed}
              onClick={reset}
            >
              Reset to baseline
            </button>
            <p className="chart-note" role="status">
              {!valid
                ? "Fix invalid assumptions to recalculate."
                : busy
                  ? "Recalculating… First use may take several seconds."
                  : data
                    ? `Updated · ${formatDecimal(data.computation_ms)} ms server calculation`
                    : "Ready"}
            </p>
          </details>
        </aside>
        <div className="stack" aria-busy={busy}>
          {query.isError && (
            <ErrorState
              error={query.error}
              retry={() => void query.refetch()}
            />
          )}{" "}
          {!data && !query.isError && (
            <Loading label="Computing baseline… First use warms the model cache and may take several seconds." />
          )}
          {data &&
            (data.positions_in_scope === 0 ? (
              <Empty title="No positions in this scope." />
            ) : (
              <>
                <Card
                  title="Scenario comparison"
                  subtitle={
                    busy
                      ? "Recalculating — previous results remain visible"
                      : "Baseline and scenario use the same as-of inputs"
                  }
                >
                  <p className="scenario-headline">
                    {data.delta.absolute.at_risk_positions === 0 &&
                    data.delta.absolute.margin_at_risk_usd === 0
                      ? "No change in near-term risk from baseline."
                      : `At-risk positions change from ${count(data.baseline.at_risk_positions)} to ${count(data.scenario.at_risk_positions)} (${formatDelta(data.delta.absolute.at_risk_positions)}); estimated gross margin at risk changes from ${money(data.baseline.margin_at_risk_usd, true)} to ${money(data.scenario.margin_at_risk_usd, true)}.`}
                  </p>
                  <Comparison
                    data={data}
                    carryingRate={meta.parameters.carrying_cost_rate_annual}
                  />
                </Card>
                <div className="grid-two">
                  <Card
                    title="Tier transitions"
                    subtitle="Baseline rows → scenario columns"
                  >
                    <div className="table-scroll" tabIndex={0}>
                      <table className="data-table transition-matrix">
                        <thead>
                          <tr>
                            <th>From / to</th>
                            {data.tier_transitions.order.map((t) => (
                              <th key={t}>{label(t)}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {data.tier_transitions.matrix.map((row, i) => (
                            <tr key={i}>
                              <th>{label(data.tier_transitions.order[i])}</th>
                              {row.map((n, j) => (
                                <td
                                  key={j}
                                  style={{
                                    background:
                                      i === j
                                        ? "var(--color-muted)"
                                        : j < i
                                          ? "var(--high-bg)"
                                          : "var(--better-bg)",
                                  }}
                                >
                                  {n ? count(n) : "·"}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Card>
                  <Card
                    title="Margin at risk by category"
                    subtitle="Model estimate · baseline vs. scenario"
                  >
                    <div className="chart">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          layout="vertical"
                          data={[...data.by_category].sort(
                            (a, b) =>
                              b.scenario_margin_at_risk_usd -
                              a.scenario_margin_at_risk_usd,
                          )}
                        >
                          <CartesianGrid
                            horizontal={false}
                            stroke="var(--chart-grid)"
                          />
                          <XAxis
                            type="number"
                            tickFormatter={(v) => money(Number(v), true)}
                          />
                          <YAxis
                            type="category"
                            dataKey="category_name"
                            width={90}
                          />
                          <Tooltip formatter={(v) => money(Number(v))} />
                          <Legend />
                          <Bar
                            isAnimationActive={false}
                            dataKey="baseline_margin_at_risk_usd"
                            name="Baseline"
                            fill="var(--color-navy)"
                          />
                          <Bar
                            isAnimationActive={false}
                            dataKey="scenario_margin_at_risk_usd"
                            name="Scenario"
                            fill="var(--color-amber-500)"
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </Card>
                </div>
                <Card
                  title="Largest changes"
                  subtitle="Product detail links show baseline values, not scenario-adjusted values"
                >
                  <div className="table-scroll" tabIndex={0}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Product / store</th>
                          <th>Tier: baseline → scenario</th>
                          <th>Est. probability</th>
                          <th>Δ est. margin</th>
                          <th>Order units</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.top_changes.map((p) => (
                          <tr key={`${p.store_id}-${p.product_id}`}>
                            <td className="product-cell">
                              <Link
                                href={`/positions/${p.store_id}/${p.product_id}`}
                              >
                                {p.product_name}
                              </Link>
                              <small>
                                {p.sku} · {p.store_code}
                              </small>
                            </td>
                            <td>
                              <Tier tier={p.baseline_tier} /> →{" "}
                              <Tier tier={p.scenario_tier} />
                            </td>
                            <td>
                              {probability(p.baseline_stockout_probability)} →{" "}
                              {probability(p.scenario_stockout_probability)}
                            </td>
                            <td>
                              {formatDelta(
                                p.scenario_margin_at_risk_usd -
                                  p.baseline_margin_at_risk_usd,
                                "money",
                              )}
                            </td>
                            <td>
                              {p.baseline_recommended_order_units === null
                                ? "—"
                                : count(
                                    p.baseline_recommended_order_units,
                                  )}{" "}
                              →{" "}
                              {p.scenario_recommended_order_units === null
                                ? "—"
                                : count(p.scenario_recommended_order_units)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
                {data.warnings.map((w, i) => (
                  <div className="notice" key={i}>
                    {w}
                  </div>
                ))}
              </>
            ))}
          <Card
            title="How to read this"
            subtitle="Decision support, not an order-placement tool"
          >
            <details>
              <summary>Risk, policy, and investment tradeoffs</summary>
              <p className="chart-note">
                Lead-time and demand changes affect near-term risk and
                replenishment policy. Service level and safety stock buffer
                change policy only: inventory already on hand does not change.
                Their effect appears in the annualized carrying-cost and
                expected-shortfall comparison. Lost-sale and carrying-cost rates
                are planning assumptions. Results describe a simulated network,
                not a real retailer.
              </p>
              <p className="chart-note">
                Baseline cycle service level:{" "}
                {rate(meta.parameters.service_level)}. No scenario or purchase
                order is persisted.
              </p>
            </details>
          </Card>
        </div>
      </div>
    </>
  );
}
