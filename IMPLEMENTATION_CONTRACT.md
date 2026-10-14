# stocgain implementation interface

Updated 2026-10-11. **Implemented scope: Phases 0–2 complete; Stage 1 verified.** SQL analytics interfaces are implemented; forecasting/risk model outputs remain future Stage 2 work.

Authority: `docs/00_DESIGN_SUMMARY.md` §4 → relevant numbered document → `CODEX_HANDOFF.md`. Product behavior changes require owner approval; log technical decisions in `docs/DECISIONS_LOG.md`.

## Structure and versions

One backend package (`backend/src/stocgain`), one Next App Router app (`frontend`), root SQL directories (`sql/views`, `pipeline`, `api`, `analyses`, `quality`, `explain`, `schema`). Alembic lives in `backend/migrations`; root `.env` is shared configuration. Model/generator TOML contents are introduced in their implementation phases under `backend/config`.

Python 3.12 (tested 3.12.7); uv 0.13.0; PostgreSQL Docker image `postgres:17`; Node 22 (tested 22.23.3). Exact Python and npm dependency graphs are committed in `backend/uv.lock` and `frontend/package-lock.json`. Selected releases include FastAPI 0.143.0, Pydantic 2.14.0, SQLAlchemy 2.0.54, Alembic 1.20.0, psycopg 3.3.6, pandas 2.3.3, NumPy 2.5.3, SciPy 1.18.1, Next 16.4.0, React 19.3.0. Compatibility constraints for Starlette/AnyIO preserve the specified httpx test transport; see decisions log.

Backend public skeleton interfaces: `Settings`, `create_app(settings: Settings | None)`, `create_db_engine(settings)`, `check_database(engine)`. App lifespan owns/disposes the engine. Health calls real PostgreSQL `SELECT 1`; outages produce HTTP 200 with `database=unavailable` per docs/08. Only health is exposed as an application endpoint. `analytics_ready=false`, `current_run_id=null` until analytics-run detection is implemented. OpenAPI/type generation is deterministic and health-only at this point.

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

26 tables total: 17 ops + 8 analytics + 1 sim_truth. All 26 tables exist at Alembic revision 0004. Operational/truth data is loaded; analytics tables remain empty.

## SQL implemented; model-output generation planned

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

`make db-reset`, analytics, pipeline, dev and demo-docker remain explicit nonzero failures. `db refresh` refreshes the one populated MV. `db run-analysis 01..15` executes the selected standalone SQL. `make explain` measures the existing standard data and writes raw plans. Optional large generation is not implemented. Stage 2 / original Phase 3 forecasting is not authorized. Phase 2 SQL execution, historical isolation and measured EXPLAIN plans are verified. New schema changes require new reversible migrations; never edit applied revisions.

## Rebrand compatibility addendum (2026-10-09)

Official product name is `stocgain.`; full description is “Predictive Retail Inventory Intelligence Platform”; tagline is “Predict stockouts. Replenish smarter.” Name origin: “Stock Again” + “Stock + Gain”. Python package and CLI are `stocgain`; npm package is `stocgain-web`. Keep the active checkout path unchanged. The PostgreSQL database/user/password `stocksense`, `stocksense_test`, and Compose project/volume `stocksense` are retained intentionally to avoid a second database or destructive migration. `STOCGAIN_ENV` supersedes `STOCKSENSE_ENV`, which remains an accepted compatibility alias. Documentation references to SQL database identifiers must retain their actual names.

## Verified Phase 1 interface

All SQLAlchemy metadata matches the existing PostgreSQL schema. Config paths are normalized against the repository root. Generator streams, stable row ordering and IDs produce deterministic CSV checksums. Atomic output publication avoids partial files. All 18 DQ SQL files return zero violations on small and standard datasets. The serial DQ/profile session setting avoids Docker shared-memory exhaustion without changing checks. See `docs/PHASE1_VERIFICATION.md` for actual commands, row counts, checksums, runtimes and calibration limits. Historical operational consistency and Phase 2 extraction isolation are verified. See docs/PHASE2_VERIFICATION.md for scope and prescribed model-only deferrals.

## Phase 2 temporal and refresh contracts

Eleven extraction files accept `:as_of`; history/latent also take `:history_days`. Known future promotion plans extend 42 days; all observed facts are cutoff-bounded. Chain rate is deseasonalized per docs/05, with sparse-weekday flat fallback and full-history aggregates. Supplier reporting views aggregate receipts/POs at the current run cutoff; lifetime PO views remain intentionally lifetime. Missing prior run yields NULL, and current-run views remain empty without a successful run.

MV population is batch-only: apply-views recreates/populates it, refresh rebuilds it transactionally/non-concurrently. No triggers or automatic per-request refresh. Reconciliation is independent of MV freshness. All objects use the unchanged 26-table schema; no new physical migration needed. The two actual-model comparison tests remain marked requires_run until Stage 2 supplies outputs. Test-only fixtures are rolled back and never persisted to the main database.
