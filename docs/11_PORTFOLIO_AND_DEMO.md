# 11 — Portfolio Presentation and Demo

**Audience:** the project owner (a Georgia Tech Scheller IT Management undergraduate targeting data/business/supply chain analyst and product roles), and Codex for README and screenshot tasks in Phase 9.

---

## 1. Positioning

**One-sentence pitch:** *stocgain is an inventory intelligence app I built that uses SQL and statistics to predict which store-SKU positions will run out before the next delivery, explains why, estimates the margin at risk, and lets managers test what-if scenarios.*

**What it demonstrates:**

| Skill | Evidence in the repository |
|-------|----------------------------|
| Relational modeling | 26-table schema across `ops` / `analytics` / `sim_truth`, constraints, ERD (`docs/03`) |
| Analytical SQL | `sql/analyses/` (15 files), `sql/views/`, point-in-time extraction, `EXPLAIN ANALYZE` report |
| Statistics applied to operations | Censoring-aware forecasting, lead-time demand, service-level safety stock, backtesting (`docs/05`) |
| Business judgment | Prioritization by probability and dollars, explicit tradeoffs, honest exposure labeling |
| Product thinking | Personas, decisions per widget, Scenario Lab |
| Engineering hygiene | Tests, migrations, reproducible pipeline, typed API contracts |

**Honesty rules for every portfolio artifact:**

- Always say "simulated dataset". Never imply real retailer data, deployment, or adoption.
- Never present planned features as built. The README feature list reflects `docs/PROGRESS.md`.
- Never claim business impact ("saved $X"). Model outputs on simulated data are not business results.
- Accuracy claims only from the backtest, phrased as "in rolling-origin backtests on the simulated dataset".
- Say how AI tools were used (see §7, Q20).

---

## 2. README plan (`README.md`, written in Phase 9)

Order and content:

1. **Title + tagline + badges** (tests passing — only if CI exists; otherwise omit badges) and a one-line disclaimer: "Portfolio project · simulated data · not affiliated with any retailer."
2. **Hero screenshot** (Overview, 1440 × 900).
3. **The problem** (4 sentences): availability matters; static reports describe the past; stockouts hide demand; managers need prioritized, explained actions.
4. **What stocgain does** — the five questions (01 §2.3) with a screenshot thumbnail each (Overview, Risk Monitor, Detail, Scenario Lab, Methodology).
5. **How it works** — architecture diagram (Mermaid from 02 §3, simplified) and the data path in five steps.
6. **SQL highlights** — 3 short excerpts with one-line explanations: availability status CASE in `mv_daily_position`; gaps-and-islands stockout episodes; point-in-time open-PO extraction. Link to `sql/analyses/`.
7. **The model in plain English** — forecasting (censoring), stockout probability (checkpoints), safety stock, exposure; link to `docs/05`.
8. **Data provenance** — provenance statement (06 §1.2), seed, how to regenerate.
9. **Quick start** — the exact commands from 02 §9.3, with expected times (measured).
10. **Testing** — `make verify`, `make e2e`, counts of tests (measured).
11. **Repository map** — short tree.
12. **Design decisions** — link to ADRs in `docs/02` §15; 3 bullets of the most important.
13. **Limitations** — 6 bullets from 05 §16.
14. **Future improvements** — §10 below.
15. **License** — MIT; third-party notices.

Style: concise, scannable, no marketing superlatives, every number measured.

---

## 3. Architecture visuals and screenshot plan

### 3.1 Visuals

| Visual | Source | Where used |
|--------|--------|-----------|
| System architecture | Mermaid (02 §3) simplified to 5 boxes | README, Methodology page (static SVG) |
| Data path | Mermaid sequence (02 §4) | README "How it works" |
| ERD | Mermaid (03 §3); a simplified ops-only version for README | README, docs |
| Risk calculation diagram | Simple timeline graphic: today → PO arrival → window end, with supply vs demand | Methodology page, interview slides |

### 3.2 Screenshots (real, captured by `frontend/scripts/screenshots.ts` with Playwright at 1440 × 900, device scale factor 2)

| File | Page / state |
|------|-------------|
| `docs/screenshots/01_overview.png` | Overview, no filters |
| `docs/screenshots/02_overview_southeast.png` | Overview filtered to Southeast |
| `docs/screenshots/03_risk_monitor.png` | Risk Monitor filtered to Critical + High |
| `docs/screenshots/04_product_detail.png` | Detail of the #1 priority position |
| `docs/screenshots/05_product_detail_breakdown.png` | Same, breakdown and checkpoint table expanded |
| `docs/screenshots/06_scenario_lab.png` | Scenario Lab: supplier SUP-015, +4 days, +20% demand |
| `docs/screenshots/07_suppliers.png` | Supplier Performance (P1) |
| `docs/screenshots/08_methodology.png` | Methodology top section |
| `docs/screenshots/09_mobile_overview.png` | Overview at 390 × 844 |

Screenshots must come from the running application with the standard dataset; no editing other than cropping.

---

## 4. Three-minute live demo

### 4.1 Preparation checklist (day before and 10 minutes before)

- [ ] `make pipeline` completed on the standard preset with seed 42; `make api` and `make web` running; production build preferred (`npm run build && npm start`).
- [ ] Browser at 1440 × 900 (or full-screen laptop), zoom 100%, bookmarks bar hidden, notifications off.
- [ ] Tabs open: Overview (no filters), Scenario Lab (neutral).
- [ ] Note the #1 priority position, its store, probability, and margin at risk (the dataset is deterministic, so these are stable; write them on a card).
- [ ] Fallback: screenshots folder open in Finder in case of a technical failure.

### 4.2 Script

The dataset's demo events (06 §8) are expected to put Southeast storm-prep items and a delayed electrical supplier near the top of the list. The exact items are whatever the deterministic dataset produces — **rehearse with the real data** and substitute the actual names/numbers in the narration.

| Time | Screen / action | Narration (plain English) |
|------|-----------------|---------------------------|
| **0:00–0:30** | Overview, no filters | "Retailers lose sales every day to empty shelves. A typical stock report tells you what's on hand right now — it doesn't tell you whether that will last until the next truck, and when an item has been out of stock, its sales look like low demand, so the next order is too small. stocgain predicts which store-SKU positions will run out before replenishment arrives and tells you what to do. This is a simulated 12-store home-improvement network — all the data is synthetic." |
| **0:30–1:15** | Point at KPI row → at-risk positions and estimated margin at risk → heatmap (Southeast Electrical hot) → Priority actions | "Out of 4,800 store-SKU positions, [N] are high or critical risk, with about [$X] of gross margin at risk before their next replenishment — that's a model estimate, labeled as such. The heatmap shows risk concentrated in Southeast Electrical — storm-prep demand is spiking there. The priority list is ranked by risk level first, then dollars at risk, so a manager knows what to do first." |
| **1:15–2:00** | Click #1 priority → Product Detail; read the explanation; point at projection chart and PO table | "Why is this one flagged? The explanation is generated from the numbers: on-hand covers about [D] days, the next delivery isn't expected until [date], and that PO is already overdue because this supplier has been late. The chart shows expected inventory hitting zero before the delivery marker. The breakdown shows every input — demand rate, variability, lead time, safety stock, reorder point — so nothing is a black box. The recommendation is to expedite that PO, and it also suggests a reorder quantity rounded to case packs." |
| **2:00–2:45** | Scenario Lab → Suppliers: SUP-015 → lead time +4 days → demand +20% → then service level 98% → Reset | "What if this supplier's delays get worse? I scope to that supplier and add four days of lead time and 20% more demand. The same model reruns: at-risk positions go from [a] to [b], margin at risk roughly [multiplies]. Now if I raise the service level to 98%, near-term risk doesn't change — the stock on the shelf is what it is — but the policy changes: more safety stock, more capital tied up, and lower expected shortfall per year. That's the tradeoff managers actually face. Reset brings it back to baseline." |
| **2:45–3:00** | Methodology page (scroll briefly) | "Under the hood: PostgreSQL holds the operational data and does the heavy lifting in SQL — joins, window functions, supplier lead-time stats. Python does the forecasting and probability math; FastAPI serves it; Next.js is the front end. Everything is reproducible from a seed and covered by tests." |

### 4.3 If something breaks

- API down → switch to screenshots and narrate the same flow.
- Slow scenario → narrate the tradeoff from the comparison grid already on screen.
- Unexpected #1 item → use the explanation as-is; the narration structure (coverage vs. replenishment vs. drivers) applies to any position.

---

## 5. Two-minute technical explanation

> "The system has three parts. **PostgreSQL** stores the operational data in a normalized schema — stores, products, suppliers, daily sales, daily inventory balances, purchase orders, lines, receipts, adjustments, promotions. A data-quality step checks things like the inventory equation — opening plus receipts minus sales plus adjustments must equal closing for every store, SKU, and day.
>
> **SQL builds the features.** A materialized view integrates sales, balances, receipts, and promotions per store-SKU-day and labels each day as in stock, sold out, or out all day. Other views compute purchase-order status, supplier lead times and on-time rates, and stockout streaks with a gaps-and-islands query. The pipeline queries are 'as-of' parameterized so that historical runs and backtests only see data that existed at the time.
>
> **Python does the modeling.** The forecast is an exponentially weighted average of demand on clean in-stock days — stockout days are excluded, not treated as zero — adjusted by day of week and planned promotions. For risk, I combine demand uncertainty and lead-time uncertainty with the standard lead-time-demand formula, then compute the probability that demand exceeds on-hand plus scheduled deliveries at each delivery checkpoint before an order placed today could arrive. Slow movers use a negative binomial instead of a normal distribution. The same functions compute safety stock, reorder points, order quantities, and expected margin at risk, and the Scenario Lab calls those same functions with modified assumptions — so the scenario results can't drift from the dashboard.
>
> **FastAPI** exposes typed endpoints; the TypeScript types in **Next.js** are generated from the API schema. I validated the forecast with rolling-origin backtests against naive baselines and wrote unit tests with hand-computed examples for every formula."

---

## 6. Plain-language explanations (for a business audience)

| Topic | Explanation |
|-------|-------------|
| **Why PostgreSQL** | "It's the kind of relational database real companies run operations on. It handles millions of rows on a laptop, enforces data rules — like no negative inventory — and supports the advanced SQL I wanted to show: window functions, materialized views, and query plans." |
| **How the tables relate** | "Stores and products are the 'who and what.' Every store-product-day has a sales row and an inventory row. Purchase orders go from a supplier to a store and have lines for products; receipts record when those lines actually arrived. Analytics tables store each forecasting run's results, tagged by run, so every number can be traced back." |
| **How SQL is used** | "SQL does the data work: combining tables, flagging stockout days, calculating supplier lead times and on-time rates, finding stockout streaks, and summarizing everything for the dashboard. Python receives clean features instead of raw tables." |
| **How forecasting works** | "For each store and product, I average recent daily demand, weighting recent days more — but only on days the item was actually in stock and not on promotion. Days when it was out of stock don't count as zero demand. Then I adjust for day of week and planned promotions." |
| **How the risk formula works** | "I estimate how much demand will happen before the next delivery, and how uncertain that is — uncertainty comes from both demand and the supplier's delivery time. Then I ask: what's the chance demand is bigger than what's on the shelf plus what's arriving in time? That's the stockout probability. Positions above 50% are Critical, above 25% High, above 10% Moderate." |
| **How margin at risk works** | "Expected units we'll be short, times the share of those customers who'd actually walk away instead of substituting or waiting, times the profit per unit. It's an estimate, and the assumptions are listed." |
| **How the scenario simulator works** | "It takes every position's stored inputs, applies your assumptions — longer lead times, more demand, a different service level — and reruns exactly the same calculations. Nothing is pre-baked." |

---

## 7. Interview question bank

| # | Question | Strong answer (key points) |
|---|----------|----------------------------|
| 1 | Why build this on simulated data? | No public dataset links store-level sales, inventory, POs, and receipts; company data is confidential. A causal simulation keeps inventory flows consistent and lets me check the model against hidden true demand — clearly labeled as simulation-only. |
| 2 | Isn't it circular to test a model on data you designed? | Partly, and I say so. The simulator uses different mechanics than the model (negative binomial demand, seasonality, holidays, realized promo lift differing from plan, supplier behavior), and the model never sees latent demand. Results show the method works under known conditions, not that it works at a real retailer. |
| 3 | How do you handle stockouts in the forecast? | Days that sold out or were out all day are excluded instead of treated as zero; estimate from clean days; fall back to chain-wide demand when history is thin. Example: naive average 3.6/day vs 6.0/day censoring-aware. |
| 4 | What does "75.7% stockout probability" mean? | Under the model's assumptions, there's about a 76% chance demand before the next replenishment exceeds the stock available by then. It's a model estimate. |
| 5 | How do incoming purchase orders affect risk? | Each open PO counts once, at its expected arrival date, adjusted for the supplier's typical lateness. I check supply vs demand just before each arrival and at the end of the lead time. Inventory position (on hand + on order) is used only for the reorder decision. |
| 6 | Difference between reorder point and stockout probability? | Reorder point: "should we order now?" — compares inventory position to lead-time demand at 95% service. Stockout probability: "will we run out before supply arrives?" — compares scheduled supply to demand. You can need to reorder with low near-term risk, or have plenty on order that arrives too late. |
| 7 | Why a normal distribution — and when not? | Normal is accurate and explainable for fast movers. For slow movers (a few units over the lead time), demand is a small count, so I use a negative binomial or Poisson; the normal would overstate risk (67% vs 52% in my example). |
| 8 | How did you pick 95% service level? | It's a common default for cycle service level; it's configurable, and the Scenario Lab shows the cost of moving it: safety stock rises steeply above 95% while shortage reduction diminishes. |
| 9 | How do you validate the forecast? | Rolling-origin backtest: 8 weekly origins, 28-day horizons, only data available at each origin. Compare to a 28-day naive mean and seasonal naive. Metrics: MAE, WAPE, bias. On real data I could only score in-stock days; in the simulation I can also score against hidden true demand. |
| 10 | Why WAPE and not MAPE? | MAPE divides by each day's actual, which is undefined or explodes on zero-demand days — common in retail. WAPE aggregates errors over total demand. |
| 11 | Why not machine learning? | The baseline is explainable and testable; ML would need to beat it on the same leakage-free backtest to justify its complexity. That's a future extension, not a starting point. |
| 12 | How do you prioritize? | Risk tier first (probability-based), then estimated margin at risk, then soonest projected stockout. No invented weights; easy to defend. |
| 13 | How are lost-sale rates justified? | They're assumptions by category (e.g., plumbing repairs are urgent → higher walk-away rate; hardware is substitutable → lower), configurable and displayed. In a real deployment I'd calibrate with substitution analysis or customer research. |
| 14 | How do you prevent data leakage? | All pipeline SQL is parameterized by an as-of date and filters every table to that date; a test deletes all future rows and checks nothing changes. Latent demand lives in a separate schema the forecasting code can't read. |
| 15 | What SQL are you proudest of? | The availability-status materialized view, gaps-and-islands stockout episodes, and point-in-time open-PO extraction that also handles partial receipts and cancellations. |
| 16 | How would it scale to 2,000 stores × 35,000 SKUs? | 70M positions × days is a data-warehouse problem: partition facts by date, move feature SQL to a warehouse (BigQuery/Snowflake/Redshift), run forecasting in batch jobs per region, keep the API reading precomputed outputs. The architecture's separation of SQL features, batch modeling, and read API stays the same. |
| 17 | What would you need to deploy at a real retailer? | Real feeds (POS, perpetual inventory, PO/ASN), DC modeling, supplier capacity, shelf capacity, calibration of lost-sale rates, forecast accuracy monitoring, user access controls, and integration with ordering systems — stocgain deliberately doesn't place orders. |
| 18 | What are the biggest limitations? | Censored days assumed similar to clean days; no annual seasonality; normal/count approximations; max-of-checkpoints is a lower bound; assumed lost-sale rates; direct-to-store network. |
| 19 | What would you improve next? | Store-to-store transfers, a challenger ML model evaluated against the baseline, P10/P90 exposure ranges, alerting. |
| 20 | How did you use AI tools? | I used AI assistants to help write the design specification and to implement code from it. I made and documented the design decisions, verified outputs against hand calculations and tests, and can explain every formula and query. (Adjust to reflect what actually happened.) |

---

## 8. Resume bullets

### 8.1 Rules

- Write only after Phase 9 verification; fill bracketed values from §9 (verified facts).
- Describe what was built and verified; never planned features.
- Never claim business improvements; any accuracy statement must say "in backtests on simulated data".
- Keep each bullet ≤ 2 lines on the resume.

### 8.2 Templates

**Bullet 1 — SQL and data engineering**

> Designed a [26]-table PostgreSQL schema and [15] analytical SQL queries and views (CTEs, window functions, gaps-and-islands, point-in-time feature extraction) over [864K] simulated store-SKU-day records to measure sales velocity, supplier lead-time reliability, and stockout history across a [12]-store retail network.

**Bullet 2 — Forecasting, risk, visualization, decision support**

> Built a Python/FastAPI inventory-risk engine (stockout-censored demand forecasting, lead-time demand distributions, service-level safety stock) and a Next.js dashboard with a what-if Scenario Lab that ranks replenishment actions by estimated margin at risk; validated with [N] automated tests and leakage-free rolling-origin backtests against naive baselines.

Optional variant, only if the backtest supports it: "…forecast reduced WAPE by [X]% versus a naive 28-day average in rolling-origin backtests on simulated data."

### 8.3 Short project description (for LinkedIn / portfolio site)

> **stocgain — Retail inventory intelligence (portfolio project, simulated data).** Predicts which store-SKU positions will stock out before replenishment, explains the drivers, estimates gross margin at risk, and models what-if scenarios. PostgreSQL + SQL analytics, Python statistical models, FastAPI, Next.js.

---

## 9. Verified facts register (fill in Phase 9 — do not pre-fill)

| Fact | Value | How measured | Date |
|------|-------|--------------|------|
| Tables in schema | | `SELECT COUNT(*) FROM information_schema.tables WHERE table_schema IN ('ops','analytics','sim_truth') AND table_type='BASE TABLE'` | |
| SQL analysis files | | `ls sql/analyses/*.sql \| wc -l` | |
| Store-SKU-day rows | | `SELECT COUNT(*) FROM ops.daily_sales` | |
| Fresh setup time | | `scripts/verify_fresh_setup.sh` | |
| `make pipeline` time | | same | |
| Backend tests passing | | `pytest` summary | |
| Frontend unit tests passing | | Vitest summary | |
| E2E specs passing | | Playwright summary | |
| Backtest WAPE (stocgain vs naive, observed basis, all horizons) | | `forecast_evaluations` | |
| Scenario evaluation time (full scope) | | `computation_ms` p95 over 20 calls | |

---

## 10. Future improvements (README list)

1. Store-to-store transfer recommendations (rule already specified, 05 §9.6).
2. Challenger ML forecast (gradient boosting with calendar and price features), adopted only if it beats the baseline on the same backtest.
3. Exposure ranges (P10–P90) instead of a single expected value.
4. Distribution-center echelon and truck-minimum constraints.
5. Persistent, shareable scenarios.
6. Alerting (daily digest of new Critical positions).
7. Calibrated lost-sale rates from substitution analysis.
8. Hosted demo with read-only access.

---

## 11. License and third-party notices

- Code license: **MIT** (`LICENSE`, created in Phase 0; the copyright holder line is filled in by the project owner).
- Dataset: generated by the project; released under the same license; provenance statement included.
- Fonts: Inter and JetBrains Mono (SIL Open Font License 1.1) via `next/font`.
- Dependencies: summarized in `THIRD_PARTY_NOTICES.md` (Phase 9) with name, version, and license for direct dependencies (FastAPI MIT, SQLAlchemy MIT, Alembic MIT, Pydantic MIT, pandas BSD-3, NumPy BSD-3, SciPy BSD-3, psycopg LGPL-3.0, Typer MIT, Next.js MIT, React MIT, Tailwind MIT, Radix/shadcn MIT, Recharts MIT, TanStack MIT, lucide ISC, Playwright Apache-2.0, Vitest MIT). Codex must verify each license from package metadata rather than trusting this list.
- No third-party datasets are used.
