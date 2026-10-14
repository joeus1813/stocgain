# 01 — Product Requirements Document (PRD)

**Product:** stocgain — Retail Inventory Intelligence and Decision Support
**Tagline:** Predict stockouts. Replenish smarter.
**Status:** Approved for implementation (design phase complete)
**Related:** `00_DESIGN_SUMMARY.md` (canonical constants), `05_ANALYTICS_MODELS.md` (formulas), `07_UI_UX_SPECIFICATION.md` (screens)

---

## 1. Product vision

Large home-improvement retailers lose sales every day to empty shelves, yet most store and supply-chain teams still work from static stock reports that describe **what already happened**. A report that says "on hand: 14" does not say whether 14 units will last until the next truck.

stocgain converts raw operational data into a short, prioritized list of **inventory positions that are likely to run out before replenishment arrives**, explains **why**, estimates **how much margin is at risk**, and suggests **what to do**, with the tradeoffs made explicit.

**Vision statement:** *Every morning, an inventory analyst or store manager opens stocgain and, in under five minutes, knows the ten store-SKU positions that most need attention, why each is at risk, and what action to take.*

### 1.1 What stocgain is

- A decision-support analytics application over a relational inventory database.
- Predictive: it forecasts demand and estimates the probability of future stockouts.
- Explainable: every number on screen can be traced to a formula and source data.
- Honest: built on a clearly labeled simulated dataset, with model estimates labeled as estimates.

### 1.2 What stocgain is not

- Not an ordering system. It never places purchase orders.
- Not an ERP, WMS, or POS replacement.
- Not a machine-learning showcase. Statistical methods are chosen for transparency.
- Not affiliated with any retailer, and not built on any company's data.

---

## 2. Problem definition

### 2.1 Business problem

For a multi-store retailer, a stockout on a high-demand item has three costs:

1. **Lost margin** from customers who buy elsewhere.
2. **Customer trust**: a contractor who finds an empty bay on Monday shops elsewhere on Tuesday.
3. **Hidden demand**: when shelves are empty, sales drop to zero, and naive forecasts conclude demand fell, which causes **smaller** future orders and **more** stockouts.

### 2.2 Why existing static reports are insufficient

| Static report shows | What it misses |
|---------------------|----------------|
| Current on-hand units | Whether those units cover demand until the next delivery |
| Last 4 weeks of sales | That some of those weeks were stockouts (censored demand) |
| Open purchase orders | Whether the PO will arrive in time, given supplier history |
| Supplier on-time % | Which store-SKU positions are actually exposed to that supplier |
| Days of supply | The uncertainty in demand and lead time |

### 2.3 The five questions stocgain answers

| # | Question | Where answered |
|---|----------|----------------|
| Q1 | Which products are likely to run out before replenishment arrives? | Risk Monitor; Overview "Top at-risk positions" |
| Q2 | What factors drive those risks? | Product Risk Detail: drivers, explanation, breakdown |
| Q3 | Which products and stores need intervention first? | Overview "Priority actions"; Risk Monitor default sort |
| Q4 | How much revenue or gross margin is at risk? | Overview KPI; Risk Monitor column; Detail breakdown |
| Q5 | Which replenishment actions reduce risk, and what are the tradeoffs? | Recommendations; Scenario Lab |

---

## 3. Personas

A single demo user can switch between perspectives using filters. No permission system is required.

### Persona A — Inventory Analyst ("Priya")

| Attribute | Detail |
|-----------|--------|
| Role | Monitors stock levels across stores; recommends adjustments to replenishment parameters |
| Main objectives | Catch emerging stockouts early; keep forecasts honest; find abnormal demand |
| Most important KPIs | At-risk positions (Critical + High); stockout probability; forecast WAPE and bias; recent stockout days; demand variability (CV) |
| Expected workflow | Open Risk Monitor → filter to Critical/High → sort by probability → open detail for the top items → check whether risk is demand-driven or supply-driven → note actions → check forecast evaluation panel weekly |
| Required features | Risk Monitor with filters, sort, search, CSV export; Product Detail with sales history, censored-day markers, forecast, breakdown; forecast evaluation panel |
| Decisions supported | Which SKUs to reorder now; which forecasts to distrust (low data, high volatility); which SKUs need parameter review |

### Persona B — Store Operations Manager ("Marcus")

| Attribute | Detail |
|-----------|--------|
| Role | Responsible for product availability at one store (e.g., S03 Tampa) |
| Main objectives | Know what to prioritize today; keep bays full; escalate supplier problems |
| Most important KPIs | Critical positions at my store; margin at risk at my store; overdue POs; days of cover |
| Expected workflow | Open Overview → select his store in the global store filter → read "Priority actions" → click the first item → read plain-language explanation → act (expedite PO / reorder) → return |
| Required features | Store filter that persists across pages; priority action list; plain-language explanations; PO status on detail page |
| Decisions supported | Which items to chase today; whether the problem is demand or replenishment; whether to request an expedite |

### Persona C — Supply Chain / Regional Manager ("Dana")

| Attribute | Detail |
|-----------|--------|
| Role | Oversees replenishment performance across a region or the chain |
| Main objectives | Identify unreliable suppliers; compare regions; decide where to invest inventory |
| Most important KPIs | Supplier on-time rate; lead-time mean and variability; supplier-linked margin exposure; regional at-risk share; safety stock value vs. margin at risk |
| Expected workflow | Overview → store comparison and category heatmap → Supplier Performance ranked table → open the worst supplier → Scenario Lab: "What if this supplier's lead time grows by 4 days?" → compare cost of higher service level |
| Required features | Supplier Performance page; region filter; Scenario Lab with tradeoff panel |
| Decisions supported | Which supplier conversations to have; whether to raise safety stock for a region/category; whether higher service levels are worth the capital |

---

## 4. User stories

Format: *As a [persona], I want [capability] so that [outcome].* Each story has acceptance criteria (AC). Priority: P0 = MVP, P1 = polish, P2 = optional.

### 4.1 Overview

| ID | Story | Priority | Acceptance criteria |
|----|-------|----------|---------------------|
| US-01 | As any user, I want a landing dashboard showing overall inventory risk so that I know how severe today's situation is. | P0 | Shows 6 KPI cards defined in §7.1 with values from `GET /api/v1/overview/summary`; each card has a tooltip with definition and time window; values match SQL in 04 §6 exactly. |
| US-02 | As Marcus, I want to filter the whole dashboard to my store so that I see only my problems. | P0 | Store and region filters in the top filter bar; selection stored in URL query params; all Overview widgets refetch with the filter; filter survives navigation to Risk Monitor. |
| US-03 | As any user, I want to see the highest-priority actions so that I know what to do first. | P0 | Top 10 recommendations ordered by `priority_rank`; each row links to Product Detail. |
| US-04 | As Dana, I want to compare stores and categories so that I can see where risk concentrates. | P0 | Store comparison bar chart and category × store heatmap; clicking a cell opens Risk Monitor pre-filtered. |
| US-05 | As Priya, I want to see whether risk is rising or falling week over week. | P0 | Risk trend chart with 13 weekly points from backfill runs; toggle between at-risk count and margin at risk. |

### 4.2 Risk Monitor

| ID | Story | Priority | Acceptance criteria |
|----|-------|----------|---------------------|
| US-10 | As Priya, I want a sortable, filterable table of all store-SKU positions with risk metrics. | P0 | Server-side pagination (50/page default), sort by any numeric column, filters for store, category, risk tier, action type, supplier; search by SKU or product name. Totals update with filters. |
| US-11 | As Priya, I want to export the filtered table to CSV. | P1 | `GET /api/v1/risk/positions/export.csv` with the same filters; file includes header row and a provenance comment line; ≤ 10,000 rows. |
| US-12 | As any user, I want to click a row to see why it is at risk. | P0 | Row click navigates to `/positions/{storeId}/{productId}`; filter state preserved for back navigation. |

### 4.3 Product Risk Detail

| ID | Story | Priority | Acceptance criteria |
|----|-------|----------|---------------------|
| US-20 | As Marcus, I want a plain-language explanation of why an item is flagged. | P0 | Explanation text from `inventory_risk_snapshots.explanation`; numbers in the text match the numbers in the breakdown panel exactly. |
| US-21 | As Priya, I want the full calculation breakdown. | P0 | Breakdown panel lists every input and output in 05 §5–§7 with units and definitions. |
| US-22 | As any user, I want a projection chart of inventory over the coming weeks. | P0 | Chart shows 28 days of history (actual closing on hand) and 28 days of projection (expected, P10–P90 band), PO receipt markers, reorder point and safety stock reference lines, and a "today" divider. |
| US-23 | As Priya, I want recent sales with stockout days highlighted. | P0 | 56-day bar chart; censored days visually distinct and excluded-from-forecast note shown. |
| US-24 | As Marcus, I want to see open and recent purchase orders. | P0 | Table with PO number, order date, promised date, expected arrival, open units, status (on time / overdue / partially received). |
| US-25 | As Priya, I want to see how much each factor contributes to risk. | P1 | Sensitivity panel: stockout probability recomputed with (a) zero lead-time variability, (b) open POs arriving on promised date, (c) demand variability at Poisson floor. |

### 4.4 Supplier Performance

| ID | Story | Priority | Acceptance criteria |
|----|-------|----------|---------------------|
| US-30 | As Dana, I want a ranked supplier table. | P1 | Columns: supplier, category, POs (90d), on-time rate, in-full rate, mean lead time, lead-time std, overdue open POs, at-risk positions, supplier-linked margin at risk, review flag. Default sort: on-time rate ascending. |
| US-31 | As Dana, I want a supplier detail view showing trend and exposed positions. | P1 | Weekly on-time trend, lane table (by store), list of at-risk positions sourced from the supplier; disclaimer that association ≠ causation. |

### 4.5 Scenario Lab

| ID | Story | Priority | Acceptance criteria |
|----|-------|----------|---------------------|
| US-40 | As Dana, I want to change lead time, demand, service level, and safety stock buffer and see the impact. | P0 | Four controls; results recalculated via `POST /api/v1/scenarios/evaluate` within 1.5 s (p95 target); Baseline vs Scenario vs Δ shown for every summary metric. |
| US-41 | As Dana, I want to scope a scenario to a supplier, store, or category. | P0 | Scope selectors; positions-in-scope count shown. |
| US-42 | As any user, I want to reset to baseline. | P0 | "Reset to baseline" restores defaults (Δ lead time 0, Δ demand 0, service level 0.95, buffer 0) and the result equals the stored baseline. |
| US-43 | As Dana, I want one-click example scenarios. | P1 | Presets: "Supplier disruption (+4 days, +20% demand)", "Demand surge (+30%)", "Higher service (98%)", "Lean inventory (90%, −20% buffer)". |
| US-44 | As Dana, I want to see the cost of higher service levels. | P0 | Tradeoff panel: safety stock value, annual carrying cost (assumption-labeled), expected per-cycle shortage margin. |

### 4.6 Methodology and provenance

| ID | Story | Priority | Acceptance criteria |
|----|-------|----------|---------------------|
| US-50 | As an interviewer, I want to know where the data comes from and how calculations work. | P0 (basic) / P1 (polished) | Methodology page with data provenance, forecast method, risk formula, recommendation rules, assumptions, limitations; live parameter values from `GET /api/v1/meta`. |
| US-51 | As any user, I want to always know the data is simulated. | P0 | "Simulated Retail Dataset" badge visible in the top bar on every page; links to Methodology §Data. |
| US-52 | As Priya, I want to see forecast accuracy against baselines. | P1 | Forecast evaluation table: stocgain vs naive 28-day mean vs seasonal naive; MAE, WAPE, bias; by horizon bucket and velocity class; evaluation basis labeled. |

---

## 5. User journeys

### 5.1 Journey 1 — Morning triage (Marcus, P0)

```mermaid
journey
    title Morning triage at S03 Tampa
    section Orient
      Open stocgain: 5: Marcus
      Select store S03 in filter bar: 4: Marcus
      Read KPI row and Priority actions: 5: Marcus
    section Investigate
      Click #1 priority (generator, Critical): 5: Marcus
      Read explanation and PO status: 5: Marcus
      Check projection chart: 4: Marcus
    section Act
      Note "Expedite PO-S03-…": 4: Marcus
      Return to Overview, open #2: 4: Marcus
```

### 5.2 Journey 2 — Weekly risk review (Priya, P0/P1)

1. Risk Monitor → filter tier = Critical, High → 83 rows (example).
2. Sort by `stockout_probability` desc.
3. Open detail for items whose driver includes `recent_stockouts` to confirm censoring treatment.
4. Export filtered list to CSV for the weekly replenishment meeting (P1).
5. Methodology → Forecast evaluation to check WAPE trend (P1).

### 5.3 Journey 3 — Supplier disruption what-if (Dana, P0)

1. Supplier Performance → identify the supplier with the lowest on-time rate (P1; in P0 use Overview store/category views).
2. Scenario Lab → scope = that supplier → lead time +4 days → demand +20%.
3. Read: Critical positions 6 → 19; margin at risk +$X; recommended order value +$Y.
4. Raise service level 95% → 98%: safety stock value +$Z, annual carrying cost +$W, per-cycle shortage margin −$V.
5. Decide whether to accept higher inventory for that supplier's items.

(Values X–Z are produced by the model at runtime; the PRD does not pre-specify them.)

---

## 6. Feature list by priority

### 6.1 P0 — Essential MVP (required for a functioning demo)

| ID | Feature | Doc |
|----|---------|-----|
| F-01 | PostgreSQL schema with constraints, migrations, views | 03 |
| F-02 | Deterministic synthetic data generator (small/standard presets) | 06 |
| F-03 | COPY loader + data-quality validation (reconciliation, integrity) | 03, 10 |
| F-04 | SQL analytical views and at least 12 analysis queries | 04 |
| F-05 | Censoring-aware demand forecast with fallbacks | 05 §3 |
| F-06 | Lead-time estimation per lane with fallbacks | 05 §4 |
| F-07 | Risk scoring: lead-time demand, safety stock, reorder point, order-up-to, stockout probability, tier | 05 §5–§6 |
| F-08 | Financial exposure (revenue and gross margin, model estimate) | 05 §7 |
| F-09 | Recommendations: expedite_po, reorder, monitor, no_action + priority rank | 05 §9 |
| F-10 | Deterministic plain-language explanations | 05 §8 |
| F-11 | Weekly backfill runs for risk trend | 05 §12 |
| F-12 | FastAPI endpoints for all P0 pages | 08 |
| F-13 | Executive Overview page | 07 §6 |
| F-14 | Inventory Risk Monitor page (filters, sort, search, pagination) | 07 §7 |
| F-15 | Product Risk Detail page (explanation, breakdown, projection, history, POs) | 07 §8 |
| F-16 | Scenario Lab (4 controls, scope, baseline vs scenario, reset, tradeoff panel) | 07 §10 |
| F-17 | Basic Methodology page with provenance and formulas | 07 §11 |
| F-18 | "Simulated Retail Dataset" badge + estimate labeling | 07 §4 |
| F-19 | Local setup via Docker Compose + Makefile | 02 §9 |
| F-20 | Core automated tests (DB, analytics, API, frontend smoke) | 10 |

### 6.2 P1 — Portfolio polish (after P0 is stable and verified)

| ID | Feature |
|----|---------|
| F-30 | Supplier Performance page and supplier detail |
| F-31 | Risk sensitivity ("what drives this risk") panel |
| F-32 | CSV export of Risk Monitor |
| F-33 | Forecast evaluation panel (vs. baselines, observed and simulation-only bases) |
| F-34 | Polished Methodology page with live parameters and diagrams |
| F-35 | Scenario presets and category breakdown chart |
| F-36 | Advanced filters (supplier, action type, demand pattern, velocity class) |
| F-37 | Refined loading skeletons and empty states |
| F-38 | Professional README, screenshots, architecture visuals |
| F-39 | `EXPLAIN ANALYZE` report in `docs/perf/QUERY_PERFORMANCE.md` |

### 6.3 P2 — Optional enhancements (only with explicit reason)

| ID | Feature | Precondition |
|----|---------|--------------|
| F-50 | ML forecast (e.g., gradient boosting) | Must beat stocgain baseline on the same backtest; shown side-by-side |
| F-51 | Store-to-store transfer recommendations | Rule in 05 §9.6 |
| F-52 | Alternative supplier recommendation | Uses secondary `product_suppliers` rows |
| F-53 | Demand anomaly detection | |
| F-54 | Automated alerts | |
| F-55 | Persistent scenario history | Tables in 03 §11 |
| F-56 | Authentication | |
| F-57 | Hosted deployment | |
| F-58 | Inventory optimization (e.g., budget-constrained service levels) | |

**Rule:** No P1 work begins until every P0 acceptance criterion passes. No P2 work begins without an explicit instruction from the project owner.

---

## 7. KPI definitions (product level)

Exact SQL lives in `04_SQL_ANALYTICS.md` §6. These definitions are binding for UI labels and tooltips.

### 7.1 Overview KPI cards (P0)

| KPI | Definition | Time window | Format | Source |
|-----|-----------|-------------|--------|--------|
| Active store-SKU positions | Count of (store, product) pairs with `products.is_active` and a risk snapshot in the current run; subtitle shows distinct active SKUs | As of run date | Integer with thousands separator | `analytics.inventory_risk_snapshots` |
| At-risk positions | Positions with `risk_tier` in (`critical`, `high`); subtitle shows % of active positions and Critical count | As of run date; delta vs. run 7 days earlier | Integer + % | `analytics.inventory_risk_snapshots` |
| Est. gross margin at risk | Σ `margin_at_risk_usd` over positions in filter | Before each position's next replenishment (protection window) | USD, no cents above $10k | `analytics.inventory_risk_snapshots` |
| Median days of cover | Median of `days_of_cover` over positions with forecast demand > 0 (capped at 365) | As of run date | 1 decimal + "days" | `analytics.inventory_risk_snapshots` |
| Supplier on-time rate | POs due in window with first receipt ≤ promised date ÷ POs due in window (unreceived overdue POs count as late) | Trailing 90 days ending as-of | % with 1 decimal | `analytics.v_po_status` |
| End-of-day in-stock rate | Position-days with `closing_on_hand > 0` ÷ all position-days | Trailing 28 days ending as-of; delta vs. prior 28 days | % with 1 decimal | `analytics.mv_daily_position` |

### 7.2 Product success metrics (for the portfolio project)

These measure whether the **project** succeeds, not business outcomes (no real business outcomes exist).

| Metric | Target | How verified |
|--------|--------|--------------|
| Clean setup time from fresh clone to populated dashboard (standard preset) | ≤ 15 minutes including Docker image pulls; ≤ 5 minutes of pipeline time on an Apple Silicon MacBook (target, to be measured) | Timed run documented in README |
| Displayed metrics traceable to SQL/Python | 100% | Lineage table (04 §6) and code review |
| Mock/hardcoded dashboard values | 0 | `grep` audit + API tests asserting values equal SQL |
| Backend test suite | Passes; analytics module line coverage ≥ 85% | `make test` |
| Frontend type check and lint | 0 errors | `make lint typecheck` |
| E2E smoke tests | Pass on standard dataset | `make e2e` |
| Scenario neutrality | Neutral scenario reproduces baseline within 1e-6 | Automated test |
| 3-minute demo | Rehearsable without errors | Demo checklist in 11 |

---

## 8. Global acceptance criteria (product level)

1. **No mock data:** Every number rendered in the UI originates from an API response that reads PostgreSQL tables/views populated by the pipeline.
2. **Provenance:** The "Simulated Retail Dataset" badge is visible on every page at ≥ 1024 px width and accessible from the mobile menu.
3. **Estimate labeling:** Every estimated metric (forecasts, probabilities, exposure, projections) is labeled "Est." or "Model estimate" with a tooltip.
4. **Traceable explanations:** For any position, the explanation sentence values equal the breakdown panel values (same rounding rules).
5. **Determinism:** Running the full pipeline twice with the same preset and seed produces identical `ops` data and identical analytics outputs (excluding timestamps and run IDs).
6. **No automatic ordering:** No feature writes purchase orders.
7. **Graceful failures:** If analytics have not been run, pages show an "Analytics not ready — run `make analytics`" state instead of crashing.
8. **Desktop-first quality:** Pages render without horizontal scrolling at 1280 px and 1440 px; usable at 390 px (mobile) with stacked layout and horizontally scrollable tables.

---

## 9. Out of scope

- Real-time streaming data or POS integration.
- Multiple users, roles, or authentication (single demo user).
- Purchase order creation or modification.
- Distribution centers, vendor-managed inventory, or multi-echelon optimization.
- Price, markdown, or assortment optimization.
- Any use of real company data, logos, or branding.
