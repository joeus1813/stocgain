# Phase 2 / Stage 1 verification — 2026-10-11

Phase 2's implementation and SQL acceptance gates pass. Stage 1 (Phases 0–2) is complete. Stage 2 is ready to begin on owner instruction and has not begun. This does not claim forecasting, risk modeling or dashboards are implemented.

## Delivered scope

- Exactly **12 SQL views**: 11 ordinary views and `analytics.mv_daily_position`, with all existing 26 physical tables preserved.
- All **15 standalone analyses**, **11 as-of extraction queries**, `api/overview_summary.sql`, the numbered analysis CLI, eight EXPLAIN workloads plus two direct-ops comparison wrappers.
- Real PostgreSQL tests for availability, rolling windows, coverage, PO quantities, supplier lead times/rates, revenue/margin aggregation, stockout episodes, SKU/category/region joins, KPI filters, missing runs, sparse weekday profiles and competing runs.
- Main database retains standard seed 42; existing test DB retains small seed 42. No resets, volume deletion, data regeneration, remote action or Git history rewrite.

## Actual verification

| Command | Observed result |
|---|---|
| `make lint typecheck test check-openapi` | PASS: Ruff/format 51 files; strict mypy 31 source files; ESLint and TypeScript; 116 backend passed, 2 requires_run skipped, 2 slow deselected in 8.60 s; 4 frontend tests passed in 0.942 s; health OpenAPI drift clean |
| `pytest …test_point_in_time.py …test_views.py …test_kpi_sql.py …test_sql_analyses.py -q` | PASS: 46 passed, 2 requires_run skipped in 2.52 s |
| `pytest backend/tests/db/test_point_in_time.py -q` (after extending overview assertion) | PASS: 6 passed in 1.52 s |
| `make migrate explain schema-dump` | PASS: final views applied, all 15 analyses executed, all 10 EXPLAIN files executed three times, actual schema exported |
| Standalone `psql -v ON_ERROR_STOP=1` over all 15 analysis files | PASS on standard data; each process exited successfully |
| Standard acceptance and DQ | PASS: 2 slow tests in 13.94 s; every standard table count, 12 views, 15 analyses, 11 extraction queries. CLI DQ01–18 all zero in 7.956 s |

Two requires_run tests are explicitly deferred to Phase 3: KPI parity with an actual generated model run and volatility classification parity with real forecasts. Rollback fixtures cover SQL behavior now. The forecasting-output equality extension of the leakage test also belongs to Phase 3 because no forecasting function exists yet; extraction equality is verified now. These are the roadmap's prescribed later-model checks, not skipped SQL failures.

On resume Docker Desktop was stopped: daemon socket absent and localhost:5433 refused connections. Initial resumed DB commands failed at connection setup; none of those were counted as passing. Starting the installed app and existing Compose service restored PostgreSQL; no reinstall or database recreation was needed. All results above are subsequent successful runs.

## Integrity and historical results

- Standard sales, inventory snapshots and latent demand each remain **864,000 rows**; daily MV has **864,000 rows**. Standard date range remains 2026-04-04–2026-09-30.
- Historical extraction at history_end−30 is byte/value-equivalent after deleting future operational facts and refreshing the MV inside a rolled-back test transaction. All 11 queries use `:as_of`; future promotion plans are the explicit known-in-advance exception.
- Cancellation quantities become visible only after the first receipt. Supplier-view receipt and PO aggregation now use the selected run cutoff. Both supplier views and overview KPIs remain equal after future receipts/POs are removed.
- Sparse or missing weekday categories use the exact flat-profile fallback before chain rates are aggregated; current-run selection excludes failed/running rows and resolves competing current/backfill runs as specified.
- All physical-table DDL blocks compare unchanged against 7a4db02; ERD unchanged. Only prescribed derived objects/indexes were added. Applied revisions 0001–0004 are untouched.
- No operational forecast/risk/API query reads latent demand. The isolated `extract_latent_demand.sql` is reserved for simulation-only backtest evaluation and tested as an extraction contract only.

## Real operational examples

Standard history totals: **1,850,996 units sold**, **$67,550,899.44 net sales**, **$42,755,569.37 COGS**. These are simulated dataset amounts, not business results. Analysis 02 produces 800 complete-week/category/region rows; analysis 10 produces 4,800 position descriptors; analysis 11 produces 288 supplier/month rows. Full counts and samples are in `perf/raw/phase2_results.json`.

Supplier advisory investigation: Phase 1's received-date calibration sample and Phase 2's promised-date/all-due KPI have different windows and denominators. All-due median supplier OTR is 0.9771018455 (still above the 0.80–0.92 plausibility band). SUP-021 has 126 on-time of 151 due POs = **0.8344370861**, versus 0.8193548387 in the received-date sample (155 POs). SUP-021 has zero unreceived due POs, so its discrepancy is not attributable to excluded open POs; the window/sample changes and prescribed early/on-time generator probabilities explain the distinction. Chain-wide there are 7,161 due POs, 6,887 on time, including 6 unreceived due POs counted late. The advisories do not invalidate the joins or formulas, but supplier calibration remains outside the desired plausibility bands. No data or formula was tuned to hide it.

## Materialized-view behavior

`make migrate` / `db apply-views` atomically recreates views in dependency order; MV creation populates from existing operational facts. `stocgain db refresh` performs a non-concurrent, transactional refresh; it does not refresh automatically on every fact write. `make seed` applies/validates/refreshes after loading; the loader builds delivered views on a new/different explicitly authorized load. Same-checksum standalone loads validate without rebuilding; use refresh after independent operational changes. The MV's unique grain index also rejects promotion-join duplication. A refresh may block readers, acceptable for this local batch architecture. Reconciliation reads base tables and does not rely on a refreshed MV.

## Performance and limitations

Final measured 56-day extract: **282.110 ms MV vs 925.174 ms ops**; earlier measurement 266.931 vs 725.047 ms. Actual refresh **1.694 s**. See [QUERY_PERFORMANCE.md](perf/QUERY_PERFORMANCE.md) for all plans and limits. No populated-model performance claim; main analytics tables remain empty. No p95, production benchmark, dashboard, forecasting accuracy or business impact claim. Existing frontend development dependency advisories and optional large generator remain as documented in Phase 1.

Independent Phase 2 review found sparse-profile handling and competing-run test gaps; both were corrected and tested. It also identified inherited historical supplier-view leakage, reproduced and corrected on resumption. The reviewer did not judge future model correctness or populated-model performance; those remain Stage 2 work.
