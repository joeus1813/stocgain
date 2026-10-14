> Current handoff — 2026-10-14: Stage 3 warm latency gate passes (browser p95 1.383 s). Stage 4 delivery and final regression evidence are in IMPLEMENTATION_STATUS.md and docs/STAGE4_VERIFICATION.md; isolated fresh-setup acceptance remains open. Preserve port 3050 and existing databases/volumes. No external publication or deployment was performed by this execution.


# CODEX_HANDOFF — stocgain Implementation Contract

> **Continue the existing stocgain implementation from its latest verified checkpoint.** This document is the binding contract. It is self-contained for planning and day-to-day decisions; the numbered documents in `docs/` contain the exhaustive detail (exact SQL, every formula, every component) and are equally binding. If this file and a numbered doc disagree, `docs/00_DESIGN_SUMMARY.md` §4 (Canonical Constants) wins, then the numbered doc, then this file — and you must record the conflict in `docs/DECISIONS_LOG.md`.
>
> Read `AGENTS.md` before writing any code.

---

## 1. Product mission

stocgain is a portfolio-grade retail **inventory intelligence and decision-support** web application for a **fictional, simulated** 12-store home-improvement retailer. Tagline: *Predict stockouts. Replenish smarter.*

It must answer, with traceable numbers:

1. Which store-SKU positions are likely to run out **before replenishment arrives**?
2. What is **driving** each risk?
3. Which positions and stores need **intervention first**?
4. How much **revenue and gross margin** is at risk (model estimate)?
5. What **replenishment actions** reduce risk, and what are the **tradeoffs**?

Success = an interviewer concludes "this candidate applies SQL and analytics to a real operational problem", and the project owner (a business/IT undergraduate) can explain every part.

**It is not:** an ordering system (never creates POs), affiliated with any retailer, built on real company data, or an ML showcase.

---

## 2. Scope and non-goals

### 2.1 P0 (must ship; build first)

PostgreSQL schema + migrations + views · deterministic synthetic data generator (small, standard presets) · loader + data-quality checks · ≥ 12 SQL analyses (15 specified) · censoring-aware demand forecast · lead-time estimation · risk scoring (stockout probability, safety stock, reorder point, order-up-to, tiers) · financial exposure · recommendations (`expedite_po`, `reorder`, `monitor`, `no_action`) + priority ranking · deterministic explanations · weekly backfill runs (risk trend) · FastAPI P0 endpoints · Overview · Risk Monitor · Product Detail · Scenario Lab (4 controls, scope, reset, tradeoff panel) · basic Methodology page · "Simulated Retail Dataset" badge · Docker Compose + Makefile · core tests.

### 2.2 P1 (after all P0 acceptance passes)

Supplier Performance pages + endpoints · sensitivity panel · CSV export · forecast evaluation panel · polished Methodology · scenario presets · advanced filters · refined states · README, screenshots, performance report.

### 2.3 P2 (do not build without explicit owner instruction)

ML forecasting · store transfers · alternative suppliers · anomaly detection · alerts · persistent scenarios · authentication · hosted deployment · optimization.

### 2.4 Non-goals

Placing/modifying purchase orders · real data · multi-user auth · microservices · queues/schedulers · Kubernetes · distribution-center modeling · price optimization · any paid service or LLM API.

---

## 3. Technology stack

| Layer | Choice |
|-------|--------|
| DB | PostgreSQL 17 (Docker image `postgres:17`), host port **5433** |
| Backend | Python 3.12, **uv**, FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2.0 (Core `text()` for analytics SQL, ORM models for migrations), Alembic, psycopg 3, pandas, NumPy, SciPy, Typer, Uvicorn |
| Backend quality | pytest (+pytest-cov, httpx), Ruff, mypy (strict on `stocgain.analytics`) |
| Frontend | Next.js (App Router, current stable major), React 19, TypeScript strict, Tailwind CSS v4, shadcn/ui, TanStack Query v5, TanStack Table v8, Recharts, lucide-react, openapi-typescript |
| Frontend quality | ESLint, Prettier, Vitest + React Testing Library, Playwright (+ axe in Phase 8) |
| Infra | Docker Compose v2, Makefile, Node 22 LTS |
| Config | `.env` (pydantic-settings), `backend/config/analytics.toml`, `backend/config/generator.toml` (parsed with stdlib `tomllib`) |

Do not add other runtime dependencies without recording the reason in `docs/DECISIONS_LOG.md`. Forbidden: Redis, Celery, Airflow/Prefect/Dagster, Kafka, GraphQL, Prisma/Drizzle, Redux, D3 directly, Faker/mock-data libraries in app code.

---

## 4. Architecture summary

Modular monolith: **PostgreSQL** + one Python package **`stocgain`** (CLI + FastAPI) + one **Next.js** app.

```
Generator (seeded) → CSV → COPY loader → ops.* + sim_truth.*
  → SQL data-quality checks (fail fast)
  → SQL views + materialized view analytics.mv_daily_position
  → analytics pipeline (as-of parameterized SQL extraction → Python forecasting → lead time → risk → recommendations → backtest)
  → analytics.* tables tagged by run_id
  → FastAPI (/api/v1) reads current run via named SQL files
  → Next.js pages (TanStack Query; types generated from OpenAPI)
```

Layer rules:
- `stocgain.analytics.*` are **pure functions** (no DB/FastAPI imports) except `analytics/pipeline.py`.
- `stocgain.api.*` → `services` → repositories (`db/sql_loader` running `sql/api/*.sql`) and analytics functions.
- Multi-line SQL lives in `.sql` files under `sql/`, never inline in Python.
- Only `analytics/backtest.py` (via `sql/pipeline/extract_latent_demand.sql`) and DQ15 may reference `sim_truth`.
- Analytics are refreshed by an explicit command (`make analytics`), never per request. The API serves the latest succeeded `current` run.
- Scenario Lab calls the **same** analytics functions as the pipeline on cached baseline inputs (cache keyed by `run_id`).

---

## 5. Repository structure

```
StockSense/
├── AGENTS.md  CODEX_HANDOFF.md  README.md  LICENSE  THIRD_PARTY_NOTICES.md
├── Makefile  docker-compose.yml  .env.example  .gitignore
├── docker/initdb/01_create_test_db.sql
├── scripts/verify_fresh_setup.sh
├── data/generated/                       # gitignored
├── docs/ 00…11 + PROGRESS.md + DECISIONS_LOG.md + perf/QUERY_PERFORMANCE.md + screenshots/
├── sql/
│   ├── views/      010_v_current_run … 120_v_risk_trend (repeatable, applied in order)
│   ├── pipeline/   extract_*.sql (all take :as_of)
│   ├── api/        named queries for endpoints
│   ├── analyses/   01_rolling_sales_velocity … 15_in_stock_rate_trend
│   ├── quality/    DQ01 … DQ18
│   ├── explain/    q1 … q8
│   └── schema/ddl_reference.sql          # generated by make schema-dump
├── backend/
│   ├── pyproject.toml  uv.lock  Dockerfile  alembic.ini
│   ├── config/analytics.toml  config/generator.toml
│   ├── migrations/versions/0001…0004
│   ├── scripts/bench_api.py
│   ├── src/stocgain/{settings,logging_config,cli}.py
│   ├── src/stocgain/db/{engine,models,sql_loader,views}.py
│   ├── src/stocgain/generator/{config,rng,catalog,demand,promotions,simulation,writer}.py
│   ├── src/stocgain/loader/copy_loader.py
│   ├── src/stocgain/quality/checks.py
│   ├── src/stocgain/analytics/{config,types,distributions,forecasting,demand_patterns,leadtime,risk,policy,exposure,explanations,replenishment,backtest,scenario,pipeline}.py
│   ├── src/stocgain/services/{runs,overview,risk_monitor,positions,suppliers,forecasts,scenarios,meta}.py
│   ├── src/stocgain/api/{app,deps,errors,pagination,export_openapi}.py + routers/ + schemas/
│   └── tests/{unit,db,api,fixtures}/
└── frontend/
    ├── package.json  next.config.ts  tsconfig.json  eslint.config.mjs  components.json
    ├── vitest.config.ts  playwright.config.ts  Dockerfile  openapi.json
    ├── scripts/screenshots.ts
    ├── src/app/{layout,page,not-found,error}.tsx, risk/, positions/[storeId]/[productId]/, suppliers/, suppliers/[supplierId]/, scenarios/, methodology/
    ├── src/components/{ui,layout,kpi,charts,tables,risk,scenario,states}/
    ├── src/lib/{format,url-state,constants,definitions}.ts, lib/api/{schema(generated),client,hooks,types}.ts
    ├── src/styles/globals.css
    └── tests/{unit,e2e,fixtures}/
```

---

## 6. Database schema requirements

Full specification (types, nullability, every CHECK, sample rows): `docs/03_DATABASE_DESIGN.md`. Summary of the **26 tables**:

### 6.1 `ops` (operational; generated by the simulator)

| Table | PK | Key columns / constraints |
|-------|----|---------------------------|
| `regions` | `region_id` smallint | `region_code` UK, `region_name` UK |
| `stores` | `store_id` smallint | `store_code` UK (`^S[0-9]{2}$`), `store_name`, `city`, `state_code`, `region_id` FK, `opened_date`, `sales_area_sqft` > 0, `is_active` |
| `product_categories` | `category_id` | `category_code` UK, `category_name` UK |
| `suppliers` | `supplier_id` | `supplier_code` UK (`^SUP-[0-9]{3}$`), `supplier_name` UK, `primary_category_id` FK, `is_active` |
| `products` | `product_id` int | `sku` UK (`^[A-Z]{2}-[0-9]{5}$`), `product_name`, `category_id` FK, `brand_name`, `unit_of_measure` (enum-like CHECK), `unit_price` numeric(10,2) > 0, `unit_cost` > 0, CHECK `unit_price > unit_cost`, `introduced_date`, `is_active` |
| `product_suppliers` | (`product_id`, `supplier_id`) | `is_primary`, `case_pack_qty` > 0, `min_order_qty` > 0 and multiple of pack; **partial unique** one primary per product |
| `supplier_store_lanes` | (`supplier_id`, `store_id`) | `contract_lead_time_days` 1–60, `review_weekday` 1–7, `is_active` |
| `calendar` | `calendar_date` | ISO year/week/day, names, month, quarter, `week_start_date`, `is_weekend`, `holiday_name` |
| `promotions` | `promotion_id` | `promotion_code` UK, name, `region_id` FK nullable (NULL = chain), dates (end ≥ start, ≤ 30 days), `discount_rate` (0, 0.6), `planned_lift` 1.00–3.00 |
| `promotion_products` | (`promotion_id`, `product_id`) | |
| `daily_sales` | (`store_id`, `product_id`, `sales_date`) | **dense**; `units_sold` ≥ 0, `net_sales_amount`, `cogs_amount` numeric(12,2); BRIN on `sales_date` |
| `inventory_snapshots` | (`store_id`, `product_id`, `snapshot_date`) | **dense**; `opening_on_hand` ≥ 0, `closing_on_hand` ≥ 0; btree on `snapshot_date` |
| `purchase_orders` | `purchase_order_id` int | `po_number` UK (`^PO-[0-9]{6}$`), `(supplier_id, store_id)` FK → lanes, `order_date`, `promised_delivery_date` > order_date. **No stored status.** |
| `purchase_order_lines` | `po_line_id` | `purchase_order_id` FK, `line_number`, `product_id` FK, `quantity_ordered` > 0, `quantity_cancelled` 0…ordered, `unit_cost`; UK (po, line), (po, product) |
| `inventory_receipts` | `receipt_id` | `po_line_id` FK, `received_date`, `quantity_received` > 0; UK (line, date) |
| `inventory_adjustments` | `adjustment_id` | store, product, date, `quantity_delta` ≠ 0 (signed), `reason_code` enum; negative unless `cycle_count_correction` |
| `dataset_manifest` | `dataset_id` = 1 | `data_origin` ('synthetic'), generator version, preset, seed, dates, timestamps, `row_counts` jsonb, `content_checksum`, `notes` (provenance statement) |

**Inventory equation (binding):** `closing = opening + received − sold + net_adjustment`; `sold ≤ opening + received`; `opening(d) = closing(d−1)`; never negative. Event order within a day: receipts (start) → sales → adjustments (end).

### 6.2 `analytics` (derived; every row tagged with `run_id`, cascade on run delete)

| Table | PK | Purpose |
|-------|----|---------|
| `analytics_runs` | `run_id` identity | `run_type` (current/backfill), `as_of_date`, `status`, `model_version`, `config` jsonb, `dataset_checksum`, timestamps, `step_timings` jsonb, `positions_scored`, `error_message` |
| `demand_forecasts` | (run, store, product) | method, pattern, lookback/clean/censored/promo days, `base_daily_demand`, `daily_demand_std`, CV, trend ratio, ADI, CV², 7/14/28-day totals and stds |
| `demand_forecast_daily` | (run, store, product, target_date) | `horizon_day` 1–42, `forecast_units`, `dow_index`, `promo_multiplier`, `promotion_id` — **current runs only** |
| `forecast_evaluations` | `evaluation_id` | model × basis × segment metrics (MAE, WAPE, bias), UK on the combination |
| `supplier_lane_estimates` | (run, supplier, store) | source (lane/supplier/contract), n, mean/std lead time, mean/std delay, mean delay when late, on-time rate |
| `inventory_risk_snapshots` | (run, store, product) | all risk inputs/outputs (03 §6.6): on hand, on order, IP, next receipt, demand, days of cover, lead time, LTD mean/std, family, SS, ROP, order-up-to, below-ROP, binding checkpoint fields, probability, shortage, lost-sale rate, lost units, revenue/margin at risk, projected stockout, tier, drivers[], explanation |
| `risk_checkpoints` | (run, store, product, seq) | each checkpoint's window, supply, demand mean/std, family, probability, shortage, `is_binding` (partial unique) |
| `replenishment_recommendations` | `recommendation_id` | one per position per run; action, urgency, `priority_rank` (NULL iff no_action), order units/cost, related PO, rationale |

Views (`sql/views/`, repeatable): `v_current_run`, **`mv_daily_position`** (materialized: integrates sales, snapshots, receipts, adjustments, promotions; derives `availability_status` ∈ {in_stock, sold_out, out_all_day} and `is_censored`), `v_po_line_status`, `v_po_status`, `v_supplier_lane_performance`, `v_supplier_performance`, `v_category_dow_profile`, `v_product_abc_class`, `v_stockout_episodes`, `v_inventory_reconciliation`, `v_current_risk`, `v_risk_trend`. Exact SQL in `docs/04` §3.

### 6.3 `sim_truth`

`latent_demand` (store, product, date, `latent_units`) — hidden true demand; only the backtest's simulation-only basis and DQ15 may read it.

### 6.4 Enums (PostgreSQL types; order matters)

`risk_tier` (low < moderate < high < critical) · `action_type` (no_action < monitor < reorder < expedite_po) · `forecast_method` · `demand_pattern` · `distribution_family` · `checkpoint_type` · `lead_time_source` · `run_type` · `run_status` · `adjustment_reason` · `risk_driver` — values in `docs/00` §4.3.

### 6.5 Migrations

Alembic revisions `0001_schemas_and_reference`, `0002_operational_facts`, `0003_analytics_outputs`, `0004_sim_truth`, each with a working downgrade. Views are applied after migrations by `stocgain db apply-views`. Never edit an applied revision; add a new one.

---

## 7. Analytics formulas (binding summary — full spec `docs/05`)

Notation: as-of `T` (end of day); future day `t` is `T+t`. A receipt arriving on date `E` is preceded by `w = (E − T) − 1` days of demand; an order placed on `T+1` with lead time `L` covers `L` days.

**Forecast (per position):**
- Last 56 days. **Clean** = `in_stock` and not promo; **censored** (`sold_out`, `out_all_day`) and promo days excluded.
- `z_d = y_d / idx_c(dow)` (category day-of-week index, mean 1, from SQL). Weights `w_d = 0.5^(age/14)`.
- `ℓ = Σw·z / Σw`; `σ_obs² = Σw(z−ℓ)²/Σw`.
- Fallback: `n ≥ 14` store_sku; `7 ≤ n < 14` blended `λ=n/14` with chain rate × store scale; `n < 7` chain_fallback (`σ_obs = ℓ`); none → insufficient_data (`ℓ = 0`, tier moderate, monitor).
- `σ_d = max(σ_obs, √ℓ)`.
- `f_t = ℓ × idx_c(dow(T+t)) × planned_lift_t` for `t = 1…42`; beyond 42 = mean(f₃₆…f₄₂).
- Pattern via ADI/CV² (1.32 / 0.49); trend ratio recent 14 vs prior 42 clean days.

**Lead time:** lane stats from received POs (≤ T, last 180 days): lane if n ≥ 8, else supplier (contract + supplier mean delay), else contract (σ = 0.25×contract). σ floors 0.5 day. Open PO ETA: future-promised → `promised + max(0, round(mean_delay))`; overdue → `T + max(1, round(mean_delay_when_late − days_overdue))` (default 3).

**Window demand:** `μ = F(w)` (cumulative forecast, fractional interpolation); `σ² = w·σ_d² + (μ/w)²·s²`. Family: μ ≤ 0 or σ ≈ 0 → degenerate; μ ≥ 20 → Normal; else NB (`n = μ²/(σ²−μ)`, `p = μ/σ²`) if σ² > μ, else Poisson.

**Stockout probability:** protection window `w_end = L̄` (s = σ_L). Checkpoints: before each distinct open-PO ETA with `w_k < w_end` (supply = OH + earlier receipts, s = σ_delay) and at `w_end` (supply = OH + POs arriving before `w_end`). `P = max_k P(D_k > S_k)`; binding = argmax; expected shortage `E` = binding `E[(D−S)⁺]` (Normal: `σ[φ(z) − z(1−Φ(z))]`).

**Days of cover:** `OH / (F₂₈/28)`, NULL if 0 demand, cap 365.

**Policy:** `SS = max(0, Q_α(LTD) − μ_L) × (1+b)`; `ROP = ceil(μ_L + SS)`; `order_up_to = max(ROP, ceil(μ_{L+7} + max(0, Q_α(D_{L+7}) − μ_{L+7})(1+b)))`; `below_ROP = IP ≤ ROP AND order_up_to > IP`; `qty = max(MOQ, ceil((order_up_to − IP)/pack)·pack)`. Default α = 0.95 (cycle service level). IP = on hand + on order (no backorders).

**Exposure:** `lost = E × λ_category`; `revenue_at_risk = lost × price`; `margin_at_risk = lost × (price − cost)`. λ: PT .50, HT .40, EL .55, PL .65, BM .70, LG .60, PA .45, HW .35. Never multiply by P again.

**Tier:** insufficient_data → moderate; OH = 0 and μ_next ≥ 1 → critical; P ≥ .50 critical; ≥ .25 high; ≥ .10 moderate (→ high if margin ≥ $250); else low.

**Recommendation (first match):** `expedite_po` if open PO and ((binding = receipt and P ≥ .25) or (next PO arrives at/after window end and P ≥ .25) or (overdue PO and tier ≥ moderate)); `reorder` if below ROP; `monitor` if tier ≥ moderate or fallback method; else `no_action`. Order qty populated whenever below ROP. **Rank** (non-no_action): tier desc → margin desc → days to projected stockout asc (nulls last) → action severity desc → store_id, product_id.

**Explanations:** deterministic templates in `docs/05` §8.3 using the shared formatter (`docs/07` §4.6).

**Scenario:** Δ lead time (−7…+14 d) applied to L̄ (floor 1) and all ETAs (floor T+1); demand change k (−0.5…+1.0) scales f and σ_d; service level 0.80–0.995; SS buffer b (−0.5…+1.0). Recompute with the same functions. Tradeoff: SS value × 0.25 carrying; `E[(D_{L+R} − S)⁺] × λ × margin × 365/7` annual expected shortfall. **Neutral inputs must reproduce stored outputs within 1e−6.**

**Backtest:** 8 weekly origins (T−77…T−28), 28-day horizons, recompute everything as of each origin; models `stocgain_v1`, `naive_28d_mean`, `seasonal_naive_7d`; bases `observed_in_stock` and `simulated_latent` (labeled simulation-only); MAE, WAPE, bias (no MAPE).

**Backfill:** 12 weekly runs at T−84…T−7 (`run_type = backfill`, no daily forecasts stored, no backtest) + current run with backtest.

**Golden cases** (must pass, tolerances ±0.002 prob, ±0.05 units, ±$0.05): G1 hero (P 0.7568, E 24.14, margin $148.88, ROP 168, S 257, qty 168) … G12 — `docs/05` §13, §15.

---

## 8. API specifications (full spec `docs/08`)

Base `/api/v1`. JSON; errors use `{ "error": { "code", "message", "details" } }`. Repeated query params for ID filters. Pagination `page`/`page_size` (≤ 200). Headers `X-Request-ID`, `X-stocgain-Run-Id`, `X-stocgain-As-Of`. Units encoded in field suffixes (`_usd`, `_units`, `_days`, `_rate`, `_probability`) and `x-unit` schema extension. Ratios 0–1 only.

| Method | Path | Priority |
|--------|------|----------|
| GET | `/health` | P0 |
| GET | `/meta` | P0 |
| GET | `/filters` | P0 |
| GET | `/overview/summary` · `/risk-distribution` · `/risk-trend` · `/store-comparison` · `/category-heatmap` · `/top-products` | P0 |
| GET | `/recommendations` | P0 |
| GET | `/risk/positions` | P0 |
| GET | `/risk/positions/export.csv` | P1 |
| GET | `/positions/{store_id}/{product_id}` · `/history` · `/projection` · `/purchase-orders` | P0 |
| GET | `/positions/{store_id}/{product_id}/sensitivity` | P1 |
| GET | `/suppliers/summary` · `/suppliers` · `/suppliers/{supplier_id}` | P1 |
| GET | `/forecasts/evaluation` | P1 |
| POST | `/scenarios/evaluate` | P0 |

Error codes: 400 `EXPORT_TOO_LARGE`; 404 `NOT_FOUND`, `STORE_NOT_FOUND`, `PRODUCT_NOT_FOUND`, `SUPPLIER_NOT_FOUND`, `POSITION_NOT_FOUND`; 422 `VALIDATION_ERROR`, `UNKNOWN_FILTER_VALUE`; 503 `ANALYTICS_NOT_READY`, `DATABASE_UNAVAILABLE`; 500 `INTERNAL_ERROR`.

Frontend types: `make openapi` → `frontend/openapi.json` → `openapi-typescript` → `src/lib/api/schema.ts` (committed); `make check-openapi` fails on drift.

---

## 9. Page-by-page UI requirements (full spec `docs/07`)

Global: light enterprise design with tokens in `docs/07` §3 (canvas `#F6F7F9`, ink `#0E1A2B`, teal `#0F7F76` primary, amber for estimates, risk tier colors critical `#D92D20` / high `#EF6820` / moderate `#EAAA08` / low `#98A2B3`); Inter + JetBrains Mono; tabular numerals; left sidebar; top bar with as-of date, run ID, and the **Simulated Retail Dataset** badge on every page; global Region/Store/Category filters in URL; "Est." tags on every model estimate; tooltips with definitions on every KPI and column; formatting per `docs/07` §4.6; no pie/donut or dual-axis charts; no dead controls; skeleton/empty/error/analytics-not-ready states everywhere.

| Page | Route | Must include |
|------|-------|--------------|
| Executive Overview | `/` | 6 KPIs (active positions, at-risk positions with WoW delta, est. GM at risk, **median** days of cover, supplier on-time 90d, in-stock rate 28d); priority actions (top 10); risk distribution; risk trend (13 weeks, toggle count/$); top at-risk products; store comparison; category × store heatmap; all drill-downs to Risk Monitor/Detail |
| Risk Monitor | `/risk` | Server-side table (columns per `docs/07` §7.2), search, store/category/tier/action filters (+ supplier, below-ROP P1), sort, pagination, summary line, URL state, row → detail, CSV export (P1) |
| Product Detail | `/positions/[storeId]/[productId]` | Identity header; explanation + driver chips + recommendation callout (no order button); key numbers; inventory projection chart (history, expected, band, receipts, ROP/SS lines, stockout marker); 56-day sales history with censored days; full risk breakdown + checkpoint table; PO table; sensitivity (P1); copy summary |
| Supplier Performance (P1) | `/suppliers`, `/suppliers/[id]` | KPIs, reliability-vs-variability scatter, ranked table with review flag and disclaimer, supplier detail (weekly on-time, lead-time histogram, lanes, exposed positions) |
| Scenario Lab | `/scenarios` | Scope selectors; 4 assumption controls (slider + numeric); debounced auto-evaluate with cancellation; URL state; reset; comparison grid (near-term risk, policy, tradeoff); headline sentence; tier transition matrix; category comparison; largest changes; interpretation notes; warnings; presets (P1) |
| Methodology | `/methodology` | Provenance, simulated retailer and events, forecasting, evaluation (P1), risk, policy, exposure, recommendations, scenarios, assumptions/limitations, architecture — parameters live from `/meta` |

---

## 10. Seed data requirements (full spec `docs/06`)

- Deterministic: NumPy `SeedSequence([seed, stream_id])` per component; default seed **42**; identical CSV checksums on rerun.
- Presets: **small** (3 stores S01/S07/S10, 60 SKUs, 10 suppliers, 2026-06-03→2026-09-30), **standard** (12 stores, 400 SKUs, 48 suppliers, 2026-04-04→2026-09-30, 864,000 store-SKU-days), **large** (optional).
- 35-day burn-in (only POs/receipts kept from burn-in).
- Causal model: latent demand ~ NegBin(λ = base × store × region-category × seasonality × weekday × holiday × realized promo lift × trend × events); sales = min(latent, available); receipts at start of day; adjustments at end of day; **naive legacy policy** (28-day raw average incl. stockout zeros, weekly review per lane) creates POs; supplier fulfillment with on-time probability, lateness, early arrivals, partial and short shipments; arrivals after the end date are not written (open POs at as-of).
- Promotions in history and planned in the 42-day forecast window (planned lift ≠ realized lift).
- Demo events (config, on by default): E1 Southeast storm-prep surge (Sep 17–30); E2 SUP-015 Lakeshore Electric Distributors delays from Aug 20; E3 SUP-021 Gulfmark Plumbing Supply Co. chronically unreliable; E4 lawn season decline (seasonality); E5 planned fall Paint and Plumbing promotions.
- Latent demand only in `sim_truth.latent_demand`.
- Fictional names for stores (real city names only), brands, suppliers, products; provenance statement in manifest, README, UI.
- Calibration plausibility ranges in `docs/06` §10 (tune generator parameters, never outputs; record tuning).

---

## 11. Test requirements (full plan `docs/10`)

- **DB:** constraint rejection tests DB01–DB24; migration round trip.
- **Data quality:** DQ01–DQ18 pass on clean data **and** detect injected corruption.
- **Generator:** determinism, counts, reconciliation, no negatives, sales ≤ available/latent, censoring present, open POs at end, partial shipments, future promotions, event effects.
- **SQL:** every view/analysis runs; invariants; point-in-time (deleting future rows changes nothing).
- **Forecast:** F01–F19 incl. golden G4, fallbacks, missing days, intermittent, zero demand, backtest leakage guard, WAPE with zero actuals.
- **Risk/policy/exposure/explanations/recommendations:** R01–R29 incl. golden G1–G12, boundaries, overdue POs, no double counting, rounding.
- **Properties:** strict invariants in `docs/05` §16.1.
- **Scenario:** S01–S12 incl. neutrality, monotonic aggregates, tradeoff direction, validation, cache invalidation.
- **API:** every endpoint success + failure; pagination; filter combinations; sorting; consistency across endpoints; error envelopes; OpenAPI determinism.
- **Frontend unit:** formatter (shared fixtures with backend), key components.
- **E2E:** overview, navigation, risk monitor, product detail, scenario lab, states, responsive, a11y (Phase 8).
- Coverage: `stocgain.analytics` ≥ 85%.
- `make verify` must pass before any phase is marked done.

---

## 12. Development environment setup

```bash
# prerequisites: Docker Desktop running, uv, Node 22
make setup                       # uv sync; npm ci; copy .env.example → .env
make db-up                       # Postgres 17 on localhost:5433 (+ stocksense_test)
make pipeline                    # migrate → generate standard (seed 42) → load → validate → views → analytics
make api                         # http://localhost:8000/api/v1 (docs at /docs)
make web                         # http://localhost:3000
make verify                      # lint + typecheck + tests + openapi check
make e2e                         # Playwright against running stack
```

Makefile targets (binding names): `setup, db-up, db-down, db-reset, migrate, seed, analytics, pipeline, api, web, dev, demo-docker, test, test-backend, test-frontend, e2e, lint, typecheck, openapi, check-openapi, explain, schema-dump, verify`.

CLI (`stocgain`): `data generate|load|validate|profile`, `db apply-views|refresh|run-analysis`, `analytics run [--as-of] [--evaluate]|backfill --weeks N`, `pipeline all --preset --seed`.

Environment variables: `docs/02` §8.1. Postgres settings: `shared_buffers=512MB`, `work_mem=32MB`, `maintenance_work_mem=256MB`.

---

## 13. Implementation phase order (full detail `docs/09`)

| Phase | Deliverable | Gate |
|-------|-------------|------|
| 0 | Repo, Docker, FastAPI health, Next.js page calling real `/health` | services communicate; `make verify` trivial pass |
| 1 | Schema + migrations, generator, loader, DQ | 864k rows; DQ clean; deterministic |
| 2 | Views, pipeline SQL, 15 analyses | all run; point-in-time test passes |
| 3 | Forecast, lead time, risk, policy, exposure, explanations, recommendations, backtest, scenario core, pipeline | golden + property tests; 13 runs; neutrality |
| 4 | P0 API + OpenAPI types + minimal real-data KPI page | API tests; consistency; check-openapi |
| 5 | Design system, shell, shared components, formatter | lint/typecheck/unit pass; states work |
| 6 | Overview, Risk Monitor, Product Detail (P0) → Suppliers, sensitivity, export (P1) | page AC + E2E |
| 7 | Scenario Lab | scenario AC + E2E |
| 8 | Polish, Methodology, performance report, a11y, responsive, dead-control audit | `make verify` + `make e2e` |
| 9 | README, real screenshots, notices, fresh-setup verification, verified facts | §14 checklist complete |

Work in **vertical slices with real data**. Never build screens on mock JSON.

---

## 14. Acceptance criteria (project-level checklist)

Data and SQL
- [ ] `make pipeline` on a fresh database completes; 26 tables; 864,000 rows in each dense table (standard).
- [ ] All error-severity DQ checks return 0 rows; reconciliation discrepancies = 0.
- [ ] Generation is byte-identical across two runs with seed 42.
- [ ] 15 SQL analyses run and pass invariants; views documented with header comments.
- [ ] Point-in-time test passes.

Analytics
- [ ] Golden cases G1–G12 pass; strict invariants pass; coverage ≥ 85%.
- [ ] 13 succeeded runs (12 backfill + current); current run has 4,800 positions in forecasts, risk, recommendations; 201,600 daily forecast rows.
- [ ] Backtest results stored for 3 models × 2 bases; reported as produced (no claims beyond them).
- [ ] Neutral scenario reproduces stored outputs (1e−6).
- [ ] Explanation numbers equal breakdown values (tested).

API
- [ ] All P0 endpoints implemented with schemas, errors, filters, pagination; tests pass; OpenAPI types committed and in sync.
- [ ] Performance targets measured and recorded (met or explained).

Frontend
- [ ] All P0 pages implemented per `docs/07`; every displayed value comes from the API; no mock data in `src/`.
- [ ] Simulated Retail Dataset badge on every page; Est. tags on estimates; tooltips with definitions.
- [ ] Loading, empty, error, and analytics-not-ready states on every page.
- [ ] No horizontal scroll at 1440/1280; usable at 390.
- [ ] E2E specs pass; axe shows no serious/critical violations (Phase 8).

Project
- [ ] P1 features implemented or explicitly deferred in `docs/PROGRESS.md` with reasons.
- [ ] README, real screenshots, LICENSE, THIRD_PARTY_NOTICES present; README commands work verbatim on a fresh clone.
- [ ] `docs/PROGRESS.md` and `docs/DECISIONS_LOG.md` current; known limitations listed in README and Methodology.
- [ ] Verified facts register (`docs/11` §9) filled with measured values; resume bullets use only verified facts.

---

## 15. Final demo requirements

The project owner must be able to run this flow without errors on the standard dataset (script in `docs/11` §4):

1. **0:00–0:30** Overview: business problem; KPIs and dataset label visible.
2. **0:30–1:15** At-risk count, est. margin at risk, heatmap concentration, priority actions.
3. **1:15–2:00** Click the #1 priority position → explanation, projection chart with receipt marker and stockout marker, breakdown, PO table, recommendation.
4. **2:00–2:45** Scenario Lab: scope to a supplier, +4 days lead time, +20% demand → risk and exposure rise; raise service level to 98% → safety stock value up, expected shortfall down, near-term risk unchanged; reset to baseline.
5. **2:45–3:00** Methodology page and architecture summary.

Requirements: every interaction responds in < 2 s on a laptop; no console errors; all numbers are live from the database; no placeholder text anywhere; the flow works identically after a fresh `make pipeline`.
