# stocgain implementation interface

Updated 2026-10-14. **Implemented scope: Phases 0–8 plus Phase 9 documentation; fresh-setup acceptance remains open.** The owner authorized Stage 4. Public deployment and remote Git writes remain unauthorized. Current verified state is summarized in IMPLEMENTATION_STATUS.md.

Authority: `docs/00_DESIGN_SUMMARY.md` §4 → relevant numbered document → `CODEX_HANDOFF.md`. Product behavior changes require owner approval; log technical decisions in `docs/DECISIONS_LOG.md`.

## Structure and versions

One backend package (`backend/src/stocgain`), one Next App Router app (`frontend`), root SQL directories (`sql/views`, `pipeline`, `api`, `analyses`, `quality`, `explain`, `schema`). Alembic lives in `backend/migrations`; root `.env` is shared configuration. Model/generator TOML contents are introduced in their implementation phases under `backend/config`.

Python 3.12 (tested 3.12.7); uv 0.13.0; PostgreSQL Docker image `postgres:17`; Node 22 (tested 22.23.3). Exact Python and npm dependency graphs are committed in `backend/uv.lock` and `frontend/package-lock.json`. Selected releases include FastAPI 0.143.0, Pydantic 2.14.0, SQLAlchemy 2.0.54, Alembic 1.20.0, psycopg 3.3.6, pandas 2.3.3, NumPy 2.5.3, SciPy 1.18.1, Next 16.4.0, React 19.3.0. Compatibility constraints for Starlette/AnyIO preserve the specified httpx test transport; see decisions log.

Backend public skeleton interfaces: `Settings`, `create_app(settings: Settings | None)`, `create_db_engine(settings)`, `check_database(engine)`. App lifespan owns/disposes the engine. Health calls real PostgreSQL `SELECT 1`; outages produce HTTP 200 with `database=unavailable` per docs/08. All 16 required P0 endpoints are exposed with strict response schemas, numeric units and generated TypeScript. Health reports actual current-run readiness. Metadata remains available without an analytics run; analytics routes return explicit 503 until ready.

Frontend imports API types from `src/lib/api/schema.ts`, generated from `frontend/openapi.json`. Do not hand-edit either. SQL/query/business calculations must not move into components.

## Ownership and canonical operational definitions (implemented)

Exact columns, types, nullability, checks, keys, indexes and delete behavior remain binding in docs/03 §§4–7. Physical quantities are integer; unit money numeric(10,2); extended money numeric(12,2); ratios use 0–1. Preserve these exact table names and grains:

| Schema/table | Primary key / grain | Essential definition |
|---|---|---|
| ops.regions | region_id | unique region_code and region_name |
| ops.stores | store_id | unique Snn code; region FK; location and positive sales area |
| ops.product_categories | category_id | unique category_code/name |
| ops.suppliers | supplier_id | unique SUP-nnn code/name; primary_category FK |
| ops.products | product_id | unique SKU; category FK; price > cost > 0 |
| ops.product_suppliers | product_id, supplier_id | one primary via partial unique index; positive case pack; MOQ multiple of pack |
| ops.supplier_store_lanes | supplier_id, store_id | contract lead time 1–60; review weekday 1–7 |
| ops.calendar | calendar_date | ISO year/week/weekday; week_start_date; holidays |
| ops.promotions | promotion_id | region nullable = chain; dates, discount, planned lift |
| ops.promotion_products | promotion_id, product_id | promotion membership |
| ops.daily_sales | store_id, product_id, sales_date | dense units_sold, net_sales_amount, cogs_amount |
| ops.inventory_snapshots | store_id, product_id, snapshot_date | dense opening_on_hand and closing_on_hand, both non-negative |
| ops.purchase_orders | purchase_order_id | unique PO number; lane FK; promised date > order date; **no stored status** |
| ops.purchase_order_lines | po_line_id | PO/product; ordered, cancelled, cost; unique PO+line and PO+product |
| ops.inventory_receipts | receipt_id | PO line/date; positive quantity; unique line+date; no redundant store/product |
| ops.inventory_adjustments | adjustment_id | position/date; signed nonzero delta and reason enum |
| ops.dataset_manifest | dataset_id = 1 | synthetic provenance, version/preset/seed/dates, row_counts, checksum |

The simulator writes CSV; the transactional loader owns writes to ops and hidden truth. Receipts occur at day start, sales next, adjustments last. `closing = opening + received - sold + net_adjustment`; `sold <= opening + received`; next opening equals previous closing. Fix generator/loader if DQ fails, never adjust outputs by hand.

26 tables total: 17 ops + 8 analytics + 1 sim_truth. All 26 tables exist at Alembic revision 0004. Operational/truth data and 13 successful analytics runs are loaded.

## SQL and model-output generation implemented

Eight analytics tables: analytics_runs, demand_forecasts, demand_forecast_daily, forecast_evaluations, supplier_lane_estimates, inventory_risk_snapshots, risk_checkpoints, replenishment_recommendations. Outputs are versioned by run_id and deleted through run cascades as specified. Daily forecasts are current-run only (42 days). Risk snapshots preserve inputs, probability, exposure and explanation; recommendations never create or modify purchase orders.

All twelve ordered repeatable views are implemented: 010_v_current_run, 020_mv_daily_position (the one materialized view), 030_v_po_line_status, 040_v_po_status, 050_v_supplier_lane_performance, 060_v_supplier_performance, 070_v_category_dow_profile, 080_v_product_abc_class, 090_v_stockout_episodes, 100_v_inventory_reconciliation, 110_v_current_risk, 120_v_risk_trend. `mv_daily_position` derives in_stock/sold_out/out_all_day and censoring. See docs/04 for exact semantics.

Fifteen standalone analyses (docs/04 §5), eighteen DQ checks (docs/03 §10). Headers state file, purpose, grain, constructs, business question. Multi-line SQL lives in files; bind query parameters; whitelist sort keys. Views apply in filename order in one transaction, after Alembic. Never edit applied revisions.

## Historical isolation and reproducibility

Default analysis cutoff is 2026-09-30 end of day, not wall-clock time. Standard history is 2026-04-04 through 2026-09-30 (180 days); small is 2026-06-03 through 2026-09-30 (120 days). Seed 42; burn-in 35 days. Small = 3 stores × 60 products = 21,600 rows per dense table; standard = 12 × 400 = 864,000. These counts have been generated, loaded and independently verified.

All pipeline extraction uses `:as_of`; operational facts after cutoff are excluded. Planned promotion schedules may extend into the forecast window per docs/04; observed future sales/receipts must never leak. Reconstruct open PO quantities/status using cutoff-bounded facts. The future-row deletion test must leave historical extraction unchanged.

`sim_truth.latent_demand` is hidden evaluation truth. Only simulation generation/loading/migration may write/manage it; analytical reads are limited to backtest simulation-only evaluation and DQ15. No forecasting, risk, API or UI access. Generator uses seeded NumPy streams, stable sorting, deterministic IDs/checksums; no wall-clock/random hash inputs. Storage/serialization rounds money, intermediate calculations do not.

## Commands and cross-stage gates

Implemented: setup, db-up/down, migrate, seed, schema-dump, api/web health, lint/typecheck/test, OpenAPI checks and Phase 0 e2e. `make migrate` applies four existing revisions and delivered views. `make seed PRESET=small|standard SEED=42` runs generation → load → apply views → validate → refresh. Database identifiers and localhost:5433 remain unchanged.

- `stocgain data generate --preset standard --seed 42 [--output PATH]`
- `stocgain data load --path data/generated/standard [--replace]`
- `stocgain data validate` / `stocgain data profile`
- `stocgain db apply-views` / `stocgain db refresh`

Loader validates CSV hashes, counts and headers before writing. Same-checksum data is revalidated without replacement. Different existing data is refused unless `--replace` (or `make seed LOAD_FLAGS=--replace`) is explicitly supplied; that operation transactionally truncates all application tables, loads, validates and rolls back on failure. It never deletes the database or Docker volume. Replacement discards existing analytics outputs and requires owner authorization in agent sessions. Default tests populate only the existing test DB and do not silently replace a different dataset.

`make db-reset`, pipeline, dev and demo-docker remain explicit nonzero failures. `make analytics` runs historical backfill then current evaluation. `db refresh` refreshes the one populated MV. `db run-analysis 01..15` executes the selected standalone SQL. `make explain` measures the existing standard data and writes raw plans. Optional large generation is not implemented. Stage 2 / Phases 3–4 were explicitly authorized and implemented. Phase 2 SQL execution, historical isolation and measured EXPLAIN plans are verified. New schema changes require new reversible migrations; never edit applied revisions.

## Rebrand compatibility addendum (2026-10-09)

Official product name is `stocgain.`; full description is “Predictive Retail Inventory Intelligence Platform”; tagline is “Predict stockouts. Replenish smarter.” Name origin: “Stock Again” + “Stock + Gain”. Python package and CLI are `stocgain`; npm package is `stocgain-web`. Keep the active checkout path unchanged. The PostgreSQL database/user/password `stocksense`, `stocksense_test`, and Compose project/volume `stocksense` are retained intentionally to avoid a second database or destructive migration. `STOCGAIN_ENV` supersedes `STOCKSENSE_ENV`, which remains an accepted compatibility alias. Documentation references to SQL database identifiers must retain their actual names.

## Verified Phase 1 interface

All SQLAlchemy metadata matches the existing PostgreSQL schema. Config paths are normalized against the repository root. Generator streams, stable row ordering and IDs produce deterministic CSV checksums. Atomic output publication avoids partial files. All 18 DQ SQL files return zero violations on small and standard datasets. The serial DQ/profile session setting avoids Docker shared-memory exhaustion without changing checks. See `docs/PHASE1_VERIFICATION.md` for actual commands, row counts, checksums, runtimes and calibration limits. Historical operational consistency and Phase 2 extraction isolation are verified. See docs/PHASE2_VERIFICATION.md for scope and prescribed model-only deferrals.

## Phase 2 temporal and refresh contracts

Eleven extraction files accept `:as_of`; history/latent also take `:history_days`. Known future promotion plans extend 42 days; all observed facts are cutoff-bounded. Chain rate is deseasonalized per docs/05, with sparse-weekday flat fallback and full-history aggregates. Supplier reporting views aggregate receipts/POs at the current run cutoff; lifetime PO views remain intentionally lifetime. Missing prior run yields NULL, and current-run views remain empty without a successful run.

MV population is batch-only: apply-views recreates/populates it, refresh rebuilds it transactionally/non-concurrently. No triggers or automatic per-request refresh. Reconciliation is independent of MV freshness. All objects use the unchanged 26-table schema; no new physical migration needed. The two actual-model comparisons now generate real outputs inside rollback-only test transactions; neither skips. Test-only fixtures are rolled back and never persisted to the main database.


## Phase 4 runtime contract

Every analytical request resolves one successful current run and uses one read-only repeatable-read PostgreSQL transaction. Named SQL files bind values; risk sorting uses a fixed whitelist. Unknown scope IDs return UNKNOWN_FILTER_VALUE; request validation includes field errors. No endpoint places orders or persists scenarios.

Scenario calculations replay full-precision operational as-of inputs using persisted run config, then reuse the Phase 3 functions. A bounded, synchronized cache is keyed by database identity and run ID; a new run cannot reuse the prior baseline. Final position serialization matches Numeric storage precision, and neutral comparisons include every risk field. Forecasting inputs never access simulation truth.

Phase 4 delivered 16 P0 endpoints. Stage 3 adds the six specified P1 endpoints: CSV export, position sensitivity, supplier summary/list/detail, and stored forecast evaluation. All 22 paths are implemented; no new database, migrations, model assumptions or persisted scenarios. Supplier SQL preserves as-of receipt isolation. CSV estimates are labeled and Content-Disposition is exposed to the local browser.

Performance: standard full-scope scenario warm p95 1.794 seconds, above 1.5-second target; first cache warmup observed through projection 6.432 seconds. These are recorded gaps, not met-target claims. See docs/PHASE4_VERIFICATION.md and raw measurements.

## Stage 3 frontend contract

Routes: `/`, `/risk`, `/positions/[storeId]/[productId]`, `/suppliers`, `/suppliers/[supplierId]`, `/scenarios`, `/methodology`. All metrics use generated OpenAPI types and real API responses. Global scope uses URL `region/store/category`, scenario controls use `lt/dem/sl/buf/store/category/supplier`; scenarios encode percentage controls in percentage points in the URL and convert to API ratios only at the request boundary. Query caches include the run ID. Search debounces 300 ms; scenario updates debounce 400 ms, abort stale requests and retain prior results while computing. Numeric validation uses `/meta` limits. Older stored explanation percentages are normalized for display only; database prose and formulas remain intact. Browser screenshots and actual verification are in `docs/STAGE3_VERIFICATION.md`. The 1.5-second Scenario Lab update target is not claimed met.

Stage 3 measured production-browser performance: 20 full-scope updates, p50 2.242 s, p95 2.426 s including the 400 ms debounce. docs/07 §10.4 AC5 remains unmet; Phase 7 acceptance remains open. See `docs/perf/raw/stage3_scenario.json`.

## Stage 4 handoff

The historical Stage 3 latency statements above are superseded by the measured warm browser p95 1.383 s (20 distinct requests), preserved in stage4_scenario.json. Scalar count-family computations use the same tail and truncated first-moment identities as the existing batch implementation; reference tests retain singular NB numerical behavior. Cold first load remains 7.014 s. Local frontend port is 3050. Makefile pipeline runs migrate, safe seed and analytics sequentially; isolated fresh setup is prepared but unverified. No original database/volume may be removed for that test. See STAGE4_VERIFICATION for remaining acceptance limitations.
