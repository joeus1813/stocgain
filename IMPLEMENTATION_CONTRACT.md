# stocgain implementation interface

Updated 2026-10-09. **Implemented scope: Phase 0 complete; Phase 1 in progress.** Schema/data/SQL contracts below are planned, not claims of existing database objects.

Authority: `docs/00_DESIGN_SUMMARY.md` §4 → relevant numbered document → `CODEX_HANDOFF.md`. Product behavior changes require owner approval; log technical decisions in `docs/DECISIONS_LOG.md`.

## Structure and versions

One backend package (`backend/src/stocgain`), one Next App Router app (`frontend`), root SQL directories (`sql/views`, `pipeline`, `api`, `analyses`, `quality`, `explain`, `schema`). Alembic lives in `backend/migrations`; root `.env` is shared configuration. Model/generator TOML contents are introduced in their implementation phases under `backend/config`.

Python 3.12 (tested 3.12.7); uv 0.13.0; PostgreSQL Docker image `postgres:17`; Node 22 (tested 22.23.3). Exact Python and npm dependency graphs are committed in `backend/uv.lock` and `frontend/package-lock.json`. Selected releases include FastAPI 0.143.0, Pydantic 2.14.0, SQLAlchemy 2.0.54, Alembic 1.20.0, psycopg 3.3.6, pandas 2.3.3, NumPy 2.5.3, SciPy 1.18.1, Next 16.4.0, React 19.3.0. Compatibility constraints for Starlette/AnyIO preserve the specified httpx test transport; see decisions log.

Backend public skeleton interfaces: `Settings`, `create_app(settings: Settings | None)`, `create_db_engine(settings)`, `check_database(engine)`. App lifespan owns/disposes the engine. Health calls real PostgreSQL `SELECT 1`; outages produce HTTP 200 with `database=unavailable` per docs/08. Only health is exposed as an application endpoint. `analytics_ready=false`, `current_run_id=null` until analytics-run detection is implemented. OpenAPI/type generation is deterministic and health-only at this point.

Frontend imports API types from `src/lib/api/schema.ts`, generated from `frontend/openapi.json`. Do not hand-edit either. SQL/query/business calculations must not move into components.

## Ownership and canonical operational definitions (planned)

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

26 tables total: 17 ops + 8 analytics + 1 sim_truth. No operational or analytic table is created in this checkpoint.

## Analytics and SQL contracts (planned)

Eight analytics tables: analytics_runs, demand_forecasts, demand_forecast_daily, forecast_evaluations, supplier_lane_estimates, inventory_risk_snapshots, risk_checkpoints, replenishment_recommendations. Outputs are versioned by run_id and deleted through run cascades as specified. Daily forecasts are current-run only (42 days). Risk snapshots preserve inputs, probability, exposure and explanation; recommendations never create or modify purchase orders.

Twelve ordered repeatable views: 010_v_current_run, 020_mv_daily_position (the one materialized view), 030_v_po_line_status, 040_v_po_status, 050_v_supplier_lane_performance, 060_v_supplier_performance, 070_v_category_dow_profile, 080_v_product_abc_class, 090_v_stockout_episodes, 100_v_inventory_reconciliation, 110_v_current_risk, 120_v_risk_trend. `mv_daily_position` derives in_stock/sold_out/out_all_day and censoring. See docs/04 for exact semantics.

Fifteen standalone analyses (docs/04 §5), eighteen DQ checks (docs/03 §10). Headers state file, purpose, grain, constructs, business question. Multi-line SQL lives in files; bind query parameters; whitelist sort keys. Views apply in filename order in one transaction, after Alembic. Never edit applied revisions.

## Historical isolation and reproducibility

Default analysis cutoff is 2026-09-30 end of day, not wall-clock time. Standard history is 2026-04-04 through 2026-09-30 (180 days); small is 2026-06-03 through 2026-09-30 (120 days). Seed 42; burn-in 35 days. Small = 3 stores × 60 products = 21,600 rows per dense table; standard = 12 × 400 = 864,000. These are target counts, not generated counts.

All pipeline extraction uses `:as_of`; operational facts after cutoff are excluded. Planned promotion schedules may extend into the forecast window per docs/04; observed future sales/receipts must never leak. Reconstruct open PO quantities/status using cutoff-bounded facts. The future-row deletion test must leave historical extraction unchanged.

`sim_truth.latent_demand` is hidden evaluation truth. Only simulation generation/loading/migration may write/manage it; analytical reads are limited to backtest simulation-only evaluation and DQ15. No forecasting, risk, API or UI access. Generator uses seeded NumPy streams, stable sorting, deterministic IDs/checksums; no wall-clock/random hash inputs. Storage/serialization rounds money, intermediate calculations do not.

## Commands and cross-stage gates

Implemented now: `make setup`, `db-up`, `db-down`, `api`, `web`, `lint`, `typecheck`, `test`, `test-frontend`, `openapi`, `check-openapi`, `verify`, `e2e`. Database-dependent commands/tests require Docker. `make setup` installs locked dependencies and preserves existing .env. PostgreSQL binds localhost:5433; initdb creates stocksense_test on first volume initialization. API/web use 8000/3000.

Configured Alembic shell only: `uv run --project backend alembic -c backend/alembic.ini ...`. No revisions exist; empty migration success is not schema verification.

Required future interfaces (currently explicit nonzero failures):
- `make migrate`: revisions 0001_schemas_and_reference, 0002_operational_facts, 0003_analytics_outputs, 0004_sim_truth, then views.
- `make seed PRESET=small SEED=42` (or standard): generate → transactional COPY load → validate → materialized-view refresh.
- `stocgain db apply-views`, `stocgain db refresh`, `stocgain db run-analysis 06`.
- `stocgain data generate --preset standard --seed 42`, `load --path data/generated/standard`, `validate`, `profile`.
- `make schema-dump`: actual migrated PostgreSQL schema only; never fabricate a reference dump.
- Stage 2 / original Phase 3: `make analytics` = backfill 12 weeks + current run with evaluation; `stocgain analytics run --as-of YYYY-MM-DD --evaluate`. Not implemented or authorized this session.

Do not bypass Phase 0 to start schema/data work. Before Stage 2, prove migrations up/down/up, small+standard load, checksums, DQ/integrity, SQL execution, historical isolation and measured EXPLAIN plans; record real results in PROGRESS. Preserve table/API/config boundaries so forecasting can be added without redesign. New schema changes require new reversible migrations and documented compatibility changes.

## Rebrand compatibility addendum (2026-10-09)

Official product name is `stocgain.`; full description is “Predictive Retail Inventory Intelligence Platform”; tagline is “Predict stockouts. Replenish smarter.” Name origin: “Stock Again” + “Stock + Gain”. Python package and CLI are `stocgain`; npm package is `stocgain-web`. Keep the active checkout path unchanged. The PostgreSQL database/user/password `stocksense`, `stocksense_test`, and Compose project/volume `stocksense` are retained intentionally to avoid a second database or destructive migration. `STOCGAIN_ENV` supersedes `STOCKSENSE_ENV`, which remains an accepted compatibility alias. Documentation references to SQL database identifiers must retain their actual names.
