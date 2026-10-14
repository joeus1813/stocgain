# Phase 2 SQL performance — 2026-10-11

Measured on macOS 15.6.1 arm64, PostgreSQL 17.11 in Docker Desktop, Python 3.12.7. Existing standard seed 42: 12 stores × 400 SKUs × 180 days. No model runs exist. `make migrate explain schema-dump` passed. `make explain` refreshes the existing MV, ANALYZEs it, executes each analysis, then executes every EXPLAIN wrapper three times and saves the third plan. Transaction-local parallel workers are disabled to avoid the previously observed Docker shared-memory limit. These are local warm measurements, not p95 or production guarantees.

| Workload | Final execution time | Interpretation |
|---|---:|---|
| Q1 MV build SELECT | 876.127 ms | Full observed-data join; actual REFRESH separately 1.694 s |
| Q2 56-day history, 268,800 rows | 282.110 ms | MV read and sort |
| Q2 equivalent direct ops | 925.174 ms | Same history projection, joined from base tables |
| Q3 full 864,000-row MV history | 349.751 ms | Server-side plan, excludes client fetch/serialization |
| Q5 overview SQL | 238.402 ms | Operational 56-day and PO aggregations; risk tables empty |
| Q6 one-position 56-day history | 0.044 ms | Composite MV index |
| Q6 equivalent direct ops | 0.473 ms | Direct joins |

Earlier observed Q2 times were 266.931 ms (MV) and 725.047 ms (ops). The final rerun was approximately 3.28× faster through the MV. The difference demonstrates an actual benefit without treating variable runtime as an invariant. Q2 (<1.5 s), Q6 (<30 ms) and refresh (<20 s) targets were met on this machine. Q5's operational portion is below 300 ms; its fully populated model-output target remains unverified.

Q4 risk page, Q7 supplier reporting and Q8 risk trend plans execute but have no current/model run: 0.044, 0.064 and 0.020 ms respectively. These do **not** establish their populated-model targets. Actual operational supplier analyses 04/05 execute against all supplier records; see the table below. No additional indexes or migrations were justified; existing MV unique `(store_id,product_id,position_date)` and date indexes are retained.

Raw third-run plans with scan/join nodes, buffers and execution times are in [raw](raw/). Q1 wraps the MV SELECT because PostgreSQL cannot EXPLAIN REFRESH directly. Q2/Q6 ops baselines expand the identical MV definition as a CTE. `phase2_results.json` includes exact columns, row counts and two actual example rows per analysis.

## Analysis executions

These elapsed times include SQL execution and fetching all result rows, measured once per analysis during the benchmark run. Top-50/top-100 limits are the specified portfolio outputs.

| Analysis | Rows | Elapsed ms |
|---|---:|---:|
| 01_rolling_sales_velocity | 50 | 576.65 |
| 02_demand_trends | 800 | 1183.69 |
| 03_days_of_cover | 63 | 45.60 |
| 04_supplier_lead_time | 48 | 49.12 |
| 05_supplier_reliability | 48 | 52.34 |
| 06_stockout_frequency | 50 | 206.13 |
| 07_high_risk_identification | 0 | 5.58 |
| 08_margin_exposure | 0 | 3.69 |
| 09_regional_risk_comparison | 1 | 3.39 |
| 10_demand_volatility | 4,800 | 111.31 |
| 11_po_fulfillment | 288 | 85.62 |
| 12_replenishment_prioritization | 0 | 3.70 |
| 13_inventory_reconciliation | 61 | 5.05 |
| 14_abc_xyz_matrix | 0 | 1.32 |
| 15_in_stock_rate_trend | 108 | 268.91 |

Analyses 07, 08, 12 and 14 intentionally return zero rows without a current run. Analysis 09 returns one empty chain-total row with guarded NULL ratios. Their nonempty join/ranking/aggregation contracts are tested using rollback-only illustrative SQL fixtures. No synthetic model output is persisted to the project DB.
