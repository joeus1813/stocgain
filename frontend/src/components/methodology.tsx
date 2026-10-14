"use client";
import { useMeta } from "@/lib/api/hooks";
import {
  formatRate as rate,
  formatCount as count,
  formatDate as date,
  formatMoney as money,
  formatLabel as label,
} from "@/lib/format";
import { Loading, ErrorState } from "./shared/ui";
import { ForecastEvaluation } from "./forecast-evaluation";
export function Methodology() {
  const q = useMeta();
  if (q.isPending) return <Loading />;
  if (q.isError)
    return <ErrorState error={q.error} retry={() => void q.refetch()} />;
  const { dataset: d, parameters: p, run } = q.data;
  const sections = [
    "Data provenance",
    "The simulated retailer",
    "Demand forecasting",
    "Forecast evaluation",
    "Stockout risk",
    "Safety stock and reorder point",
    "Financial exposure",
    "Recommendations",
    "Scenario Lab",
    "Assumptions and limitations",
    "Technical architecture",
  ];
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">Transparent by design</div>
          <h1>Analytics Methodology</h1>
          <p>
            What the model knows, how it calculates, and where its assumptions
            end.
          </p>
        </div>
      </div>
      <div className="methodology-layout">
        <nav aria-label="Methodology contents">
          {sections.map((s, i) => (
            <a key={s} href={`#method-${i + 1}`}>
              <span>{String(i + 1).padStart(2, "0")}</span> {s}
            </a>
          ))}
        </nav>
        <article className="methodology">
          <section id="method-1">
            <h2>01 · Data provenance</h2>
            <p>
              {d?.provenance_statement ?? "No dataset has been loaded yet."}
            </p>
            {d && (
              <>
                <p>
                  Preset <code>{d.preset}</code>, seed {count(d.seed)},
                  generator <code>{d.generator_version}</code>. Observed
                  history: {date(d.history_start_date, true)} to{" "}
                  {date(d.history_end_date, true)}.
                </p>
                <details>
                  <summary>Actual loaded row counts</summary>
                  <div className="table-scroll" tabIndex={0}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Table</th>
                          <th>Rows</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(d.row_counts).map(([table, n]) => (
                          <tr key={table}>
                            <td>
                              <code>{table}</code>
                            </td>
                            <td>{count(n)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
              </>
            )}
          </section>
          <section id="method-2">
            <h2>02 · The simulated retailer</h2>
            {d && (
              <p>
                The fictional network contains {count(d.counts.stores)} stores
                in {count(d.counts.regions)} regions, {count(d.counts.products)}{" "}
                SKUs across {count(d.counts.categories)} categories, and{" "}
                {count(d.counts.suppliers)} suppliers. Seeded demand,
                deliveries, promotions and a naive legacy replenishment policy
                produce both stocked and stockout periods.
              </p>
            )}
            {d?.events.map((e) => (
              <details key={e.id}>
                <summary>
                  {e.id} · {e.name}
                </summary>
                <p>{e.description}</p>
              </details>
            ))}
          </section>
          <section id="method-3">
            <h2>03 · Demand forecasting</h2>
            <p>
              Sales are not always demand. Days that sell out, or start with no
              available inventory, are censored and excluded from clean-day
              estimation. Clean observations are adjusted for weekday patterns;
              planned promotions adjust future demand.
            </p>
            <p>
              The exponentially weighted estimate uses {p.lookback_days} days of
              history and a {p.half_life_days}-day half-life. A local estimate
              needs {p.min_clean_days_full} clean days; histories with at least{" "}
              {p.min_clean_days_blend} clean days blend local and chain
              evidence. Sparser histories fall back to chain-wide demand. The
              model does not use hidden simulated demand.
            </p>
            <div className="formula" tabIndex={0}>
              <code>
                weight(age) = 2^(−age / half_life)
                <br />
                forecast(t) = demand_level × weekday_index(t) ×
                planned_promotion(t)
              </code>
            </div>
          </section>
          <section id="method-4">
            <h2>04 · Forecast evaluation</h2>
            <p>
              Historical rolling origins train only on information available at
              the cutoff. The model is compared with a trailing mean and a
              seasonal naive baseline. The observed basis excludes
              stockout-censored days. The hidden-demand basis is only available
              in this simulation.
            </p>
            <ForecastEvaluation />
          </section>
          <section id="method-5">
            <h2>05 · Stockout risk</h2>
            <p>
              The model evaluates demand before each inbound shipment and at the
              protection-window end. The highest checkpoint probability
              determines the near-term risk estimate. It is a lower bound on the
              probability of any stockout across all checkpoints, not a union
              probability.
            </p>
            <div className="formula" tabIndex={0}>
              <code>
                Normal: P(stockout) = 1 − Φ((supply − demand_mean) / demand_sd)
              </code>
            </div>
            <p>
              Normal demand is used when expected window demand is at least{" "}
              {count(p.normal_min_mean_units)} units. Smaller windows use
              Poisson or negative binomial count distributions according to
              dispersion. No-demand windows use a degenerate distribution.
            </p>
            <ul>
              {Object.entries(p.tier_thresholds).map(([tier, t]) => (
                <li key={tier}>
                  {label(tier)}: probability threshold {rate(t)}
                </li>
              ))}
            </ul>
            <p>
              Moderate positions with estimated gross margin at risk of at least{" "}
              {money(p.exposure_escalation_usd)} are escalated to High. Current
              stockouts with sufficient forecast demand receive the documented
              critical override.
            </p>
          </section>
          <section id="method-6">
            <h2>06 · Safety stock and reorder point</h2>
            <p>
              The baseline cycle service level is {rate(p.service_level)}, with
              a {p.review_period_days}-day review period. Cycle service level is
              the probability of no stockout in a cycle, not the fraction of
              units fulfilled.
            </p>
            <div className="formula" tabIndex={0}>
              <code>
                window_demand_variance = L × demand_variance + demand_mean² ×
                lead_time_variance
                <br />
                safety_stock = max(0, demand_quantile(service_level) −
                expected_demand)
                <br />
                reorder_point = ceil(expected_demand + safety_stock − 1e−9)
                <br />
                inventory_position = on_hand + outstanding_purchase_orders
              </code>
            </div>
            <p>
              The target-stock horizon includes the review period. Recommended
              orders account for every outstanding PO, minimum order quantities,
              and case packs.
            </p>
          </section>
          <section id="method-7">
            <h2>07 · Financial exposure</h2>
            <div className="formula" tabIndex={0}>
              <code>
                expected_lost_units = expected_shortage × assumed_lost_sale_rate
                <br />
                est_margin_at_risk = expected_lost_units × (unit_price −
                unit_cost)
              </code>
            </div>
            <p>
              Exposure is an estimate over the binding protection window. It is
              neither realized loss nor an annual total. Regular prices exclude
              promotional discounts; gross margin excludes freight, labor and
              shrink. Category lost-sale rates are assumptions, not measured
              conversion rates.
            </p>
            <div className="table-scroll" tabIndex={0}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Lost-sale assumption</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(p.lost_sale_rates).map(([c, r]) => (
                    <tr key={c}>
                      <td>{label(c)}</td>
                      <td>{rate(r)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section id="method-8">
            <h2>08 · Recommendations</h2>
            <p>
              Expedite an existing PO when an inbound delay is actionable;
              reorder when inventory position reaches the trigger and a positive
              order is needed; otherwise monitor elevated risk or take no
              action. Recommendations are ranked by urgency, risk, exposure and
              timing. They never create or modify purchase orders.
            </p>
          </section>
          <section id="method-9">
            <h2>09 · Scenario Lab</h2>
            <p>
              Demand and lead-time adjustments change risk and policy using the
              same functions as the baseline. Service level and safety stock
              buffer change policy targets only: they cannot alter stock already
              on hand. Annualized carrying cost uses the configured{" "}
              {rate(p.carrying_cost_rate_annual)} assumption. Neutral controls
              reproduce the baseline; scenarios are not saved.
            </p>
          </section>
          <section id="method-10">
            <h2>10 · Assumptions and limitations</h2>
            <ul>
              {[
                "Censored-day demand is assumed to resemble clean-day demand after weekday adjustment.",
                "Daily demand is independent, and demand is independent of lead time.",
                "Unreceived orders right-censor lead-time estimates; observed means can understate delays.",
                "No annual seasonality, holiday effect or explicit trend term is modeled.",
                "Inventory projection bands are approximate and omit some receipt uncertainty.",
                "No backorders, customer commitments, distribution centers or store transfers are modeled.",
                "Recommendations omit supplier capacity, truck minimums and shelf capacity.",
                "Exposure combines positions with different protection windows. Lost-sale rates are planning assumptions.",
                "Supplier review flags show association, not causation.",
                "Cold model-cache requests can take several seconds. Scenario updates may exceed the performance target.",
                "All results describe simulated data and provide no evidence about a real retailer.",
              ].map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </section>
          <section id="method-11">
            <h2>11 · Technical architecture</h2>
            <div
              className="architecture-flow"
              role="img"
              aria-label="PostgreSQL to SQL views to Python analytics to FastAPI to Next.js"
            >
              PostgreSQL → SQL views → Python analytics → FastAPI → Next.js
            </div>
            <p>
              Run {run?.run_id ?? "—"} · model{" "}
              <code>{run?.model_version ?? "not computed"}</code>. Data is
              processed in explicit analytics runs, with as-of isolation. APIs
              read PostgreSQL and persisted outputs; the frontend displays those
              responses.
            </p>
          </section>
        </article>
      </div>
    </>
  );
}
