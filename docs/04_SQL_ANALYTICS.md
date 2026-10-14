# 04 — SQL Analytics

**Related:** `03_DATABASE_DESIGN.md` (tables), `05_ANALYTICS_MODELS.md` (Python models), `08_API_SPECIFICATION.md` (endpoints)

SQL is the analytical backbone of stocgain. This document specifies:

1. The SQL files and where they live (§1)
2. Responsibility split between SQL and Python (§2)
3. Reusable views (§3)
4. Point-in-time pipeline extraction queries (§4)
5. Fifteen portfolio analyses (§5)
6. KPI definitions with exact SQL and lineage (§6)
7. API query conventions (§7)
8. Edge cases (§8)
9. Query optimization and `EXPLAIN ANALYZE` plan (§9)

The SQL below is **normative in logic** and close to final syntax. Codex may adjust syntax (aliases, formatting, casts) but must preserve semantics, grain, and filters. Every SQL file begins with a header comment:

```sql
-- File: sql/analyses/06_stockout_frequency.sql
-- Purpose: Historical stockout frequency and longest stockout streak per store-SKU.
-- Grain: one row per store-SKU.
-- Constructs: CTE, window ROW_NUMBER (gaps-and-islands), conditional aggregation, joins.
-- Business question: Which positions run out repeatedly, and for how long?
```

---

## 1. SQL file inventory

| Directory | Purpose | Executed by |
|-----------|---------|-------------|
| `sql/views/` | Repeatable view definitions (`DROP … CASCADE; CREATE …`), applied in filename order | `stocgain db apply-views` |
| `sql/pipeline/` | As-of-parameterized feature extraction for the analytics pipeline (`:as_of`) | `analytics/pipeline.py` |
| `sql/api/` | Named queries used by API repositories (`:run_id`, filters) | `services/*` via `db/sql_loader.py` |
| `sql/analyses/` | Fifteen standalone portfolio analyses, runnable with `psql -f` | Humans, tests (`tests/db/test_sql_analyses.py`) |
| `sql/quality/` | Data-quality checks returning violating rows | `stocgain data validate` |
| `sql/explain/` | `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)` wrappers for the 8 key queries | `make explain` |

**Required advanced constructs and where they appear (traceability for reviewers):**

| Construct | Files (examples) |
|-----------|------------------|
| Multi-table JOINs (≥ 4 tables) | `020_mv_daily_position`, `02_demand_trends`, `09_regional_risk_comparison`, `110_v_current_risk` |
| CTEs (incl. chained) | every analysis |
| Window functions — `AVG/COUNT … OVER` with frames | `01_rolling_sales_velocity` |
| Window functions — `LAG`, moving averages | `02_demand_trends`, `05_supplier_reliability` |
| Window functions — `ROW_NUMBER`, `RANK`, `DENSE_RANK` | `06_stockout_frequency` (gaps-and-islands), `07_high_risk_identification`, `12_replenishment_prioritization` |
| Running totals / Pareto (`SUM() OVER (ORDER BY …)`) | `08_margin_exposure`, `080_v_product_abc_class` |
| `CASE` expressions | `020_mv_daily_position` (availability status), `10_demand_volatility` (classification) |
| Conditional aggregation (`FILTER`, `SUM(CASE…)`) | `05_supplier_reliability`, `09_regional_risk_comparison` |
| Date arithmetic, `generate_series` | `020_mv_daily_position` (promotion days), `DQ04` |
| Statistical aggregates (`stddev_samp`, `percentile_cont`, `regr_slope`, `corr`) | `04_supplier_lead_time`, `10_demand_volatility` |
| `GROUPING SETS` / `ROLLUP` | `09_regional_risk_comparison`, `13_inventory_reconciliation` |
| `DISTINCT ON` | `120_v_risk_trend` |
| Materialized view + unique index | `020_mv_daily_position` |
| Point-in-time (as-of) filtering | `sql/pipeline/*` |

---

## 2. SQL vs Python responsibilities

| Calculation | SQL | Python | Rationale |
|-------------|-----|--------|-----------|
| Integrate daily sales, balances, receipts, adjustments, promotions | ✅ `mv_daily_position` | | Relational join of 5 sources |
| Availability status (`in_stock` / `sold_out` / `out_all_day`) | ✅ | | Row-level CASE on integrated data |
| Inventory reconciliation, continuity, integrity | ✅ `sql/quality` | | Set-based checks |
| PO line/PO status, open quantity, lead time, delay, on-time, in-full | ✅ `v_po_line_status`, `v_po_status` | | Aggregation over receipts |
| Lane/supplier lead-time statistics (mean, std, on-time rate) | ✅ `extract_lane_lead_times.sql` | Fallback selection (lane → supplier → contract) | Stats in SQL; rule in Python where it is unit-tested |
| Category day-of-week profile | ✅ `extract_category_dow_profile.sql` | | Grouped averages |
| Store scale factors for chain fallback | ✅ `extract_store_scale.sql` | | Grouped ratios |
| Open PO lines as of a date | ✅ `extract_open_po_lines.sql` | ETA adjustment for delays/overdue | ETA rule is model logic |
| ABC class, stockout episodes, volatility descriptors | ✅ views/analyses | | Window functions |
| Censoring-aware EWMA level, σ, fallbacks, daily forecasts | | ✅ `forecasting.py` | Vectorized matrix math; unit-testable |
| Demand pattern (ADI/CV²) for the model | | ✅ `demand_patterns.py` (SQL analysis 10 mirrors it for reporting) | Must match model inputs exactly |
| Lead-time demand mean/variance, distributions, quantiles, expected shortage | | ✅ `distributions.py`, `risk.py`, `policy.py` | SciPy |
| Risk tiers, drivers, explanations, recommendations, ranking | | ✅ | Rules with unit tests |
| Backtest | | ✅ `backtest.py` | Rolling origins |
| Scenario recomputation | | ✅ `scenario.py` | Reuses risk functions |
| Dashboard aggregations (KPIs, distributions, heatmaps, rankings, trend) | ✅ `sql/api/*` | | Set-based over stored outputs |
| Pagination, filtering, sorting of positions | ✅ | | Index-backed |

**Rule:** Python must not re-implement an aggregation that a view or SQL file already provides. Python receives already-aggregated feature frames.

---

## 3. Reusable views (`sql/views/`)

Apply order (filename order):

| File | Object | Type | Depends on |
|------|--------|------|------------|
| `010_v_current_run.sql` | `analytics.v_current_run` | view | `analytics_runs` |
| `020_mv_daily_position.sql` | `analytics.mv_daily_position` | **materialized** | `ops` facts |
| `030_v_po_line_status.sql` | `analytics.v_po_line_status` | view | POs, lines, receipts |
| `040_v_po_status.sql` | `analytics.v_po_status` | view | 030 |
| `050_v_supplier_lane_performance.sql` | `analytics.v_supplier_lane_performance` | view | 010, 040 |
| `060_v_supplier_performance.sql` | `analytics.v_supplier_performance` | view | 010, 040, risk snapshots |
| `070_v_category_dow_profile.sql` | `analytics.v_category_dow_profile` | view | 010, 020 |
| `080_v_product_abc_class.sql` | `analytics.v_product_abc_class` | view | 010, 020 |
| `090_v_stockout_episodes.sql` | `analytics.v_stockout_episodes` | view | 020 |
| `100_v_inventory_reconciliation.sql` | `analytics.v_inventory_reconciliation` | view | `ops` facts (not the MV) |
| `110_v_current_risk.sql` | `analytics.v_current_risk` | view | 010, risk, recommendations, dims |
| `120_v_risk_trend.sql` | `analytics.v_risk_trend` | view | runs, risk snapshots |

Views that depend on `v_current_run` return zero rows until analytics have run. That is expected.

### 3.1 `analytics.v_current_run`

```sql
DROP VIEW IF EXISTS analytics.v_current_run CASCADE;
CREATE VIEW analytics.v_current_run AS
SELECT run_id, as_of_date, model_version, completed_at
FROM analytics.analytics_runs
WHERE status = 'succeeded' AND run_type = 'current'
ORDER BY as_of_date DESC, completed_at DESC
LIMIT 1;
```

### 3.2 `analytics.mv_daily_position` (materialized)

Grain: one row per store × product × history date (dense; 864,000 rows in standard).

```sql
DROP MATERIALIZED VIEW IF EXISTS analytics.mv_daily_position CASCADE;
CREATE MATERIALIZED VIEW analytics.mv_daily_position AS
WITH receipts_by_day AS (
    SELECT po.store_id, pol.product_id, r.received_date AS position_date,
           SUM(r.quantity_received)::int AS units_received
    FROM ops.inventory_receipts r
    JOIN ops.purchase_order_lines pol ON pol.po_line_id = r.po_line_id
    JOIN ops.purchase_orders po      ON po.purchase_order_id = pol.purchase_order_id
    GROUP BY po.store_id, pol.product_id, r.received_date
),
adjustments_by_day AS (
    SELECT store_id, product_id, adjustment_date AS position_date,
           SUM(quantity_delta)::int AS net_adjustment
    FROM ops.inventory_adjustments
    GROUP BY store_id, product_id, adjustment_date
),
promo_days AS (
    SELECT s.store_id, pp.product_id, gs.d::date AS position_date, p.promotion_id
    FROM ops.promotions p
    JOIN ops.promotion_products pp ON pp.promotion_id = p.promotion_id
    JOIN ops.stores s ON p.region_id IS NULL OR s.region_id = p.region_id
    CROSS JOIN LATERAL generate_series(p.start_date, p.end_date, interval '1 day') AS gs(d)
)
SELECT
    i.store_id,
    i.product_id,
    i.snapshot_date                                   AS position_date,
    i.opening_on_hand,
    COALESCE(rc.units_received, 0)                    AS units_received,
    ds.units_sold,
    COALESCE(ad.net_adjustment, 0)                    AS net_adjustment,
    i.closing_on_hand,
    i.opening_on_hand + COALESCE(rc.units_received, 0) AS available_units,
    CASE
        WHEN i.opening_on_hand + COALESCE(rc.units_received, 0) = 0             THEN 'out_all_day'
        WHEN ds.units_sold >= i.opening_on_hand + COALESCE(rc.units_received, 0) THEN 'sold_out'
        ELSE 'in_stock'
    END                                               AS availability_status,
    (i.opening_on_hand + COALESCE(rc.units_received, 0) = 0
       OR ds.units_sold >= i.opening_on_hand + COALESCE(rc.units_received, 0)) AS is_censored,
    ds.net_sales_amount,
    ds.cogs_amount,
    pd.promotion_id,
    (pd.promotion_id IS NOT NULL)                     AS is_promo_day
FROM ops.inventory_snapshots i
JOIN ops.daily_sales ds
  ON ds.store_id = i.store_id AND ds.product_id = i.product_id AND ds.sales_date = i.snapshot_date
LEFT JOIN receipts_by_day rc
  ON rc.store_id = i.store_id AND rc.product_id = i.product_id AND rc.position_date = i.snapshot_date
LEFT JOIN adjustments_by_day ad
  ON ad.store_id = i.store_id AND ad.product_id = i.product_id AND ad.position_date = i.snapshot_date
LEFT JOIN promo_days pd
  ON pd.store_id = i.store_id AND pd.product_id = i.product_id AND pd.position_date = i.snapshot_date;

CREATE UNIQUE INDEX ux_mv_daily_position ON analytics.mv_daily_position (store_id, product_id, position_date);
CREATE INDEX ix_mv_daily_position_date ON analytics.mv_daily_position (position_date);
```

**Availability semantics:**

| Status | Condition | Interpretation | Used for demand estimation? |
|--------|-----------|----------------|-----------------------------|
| `in_stock` | available > 0 and sold < available | Sales = demand (uncensored) | Yes (if not a promo day) |
| `sold_out` | available > 0 and sold = available | Demand ≥ sales (right-censored) | No |
| `out_all_day` | available = 0 | Demand unobservable | No |

Refresh: `REFRESH MATERIALIZED VIEW analytics.mv_daily_position;` after each load (non-concurrent is acceptable in batch; concurrent refresh is possible thanks to the unique index).

### 3.3 `analytics.v_po_line_status`

Lifetime status as of the latest loaded data (dashboards). Point-in-time variants live in `sql/pipeline/`.

```sql
DROP VIEW IF EXISTS analytics.v_po_line_status CASCADE;
CREATE VIEW analytics.v_po_line_status AS
WITH rec AS (
    SELECT po_line_id,
           SUM(quantity_received)::int AS quantity_received,
           MIN(received_date)          AS first_receipt_date,
           MAX(received_date)          AS last_receipt_date,
           COUNT(*)::int               AS receipt_count
    FROM ops.inventory_receipts
    GROUP BY po_line_id
)
SELECT pol.po_line_id, pol.purchase_order_id, po.po_number, po.supplier_id, po.store_id, pol.product_id,
       po.order_date, po.promised_delivery_date,
       pol.quantity_ordered, pol.quantity_cancelled,
       COALESCE(rec.quantity_received, 0) AS quantity_received,
       pol.quantity_ordered - pol.quantity_cancelled - COALESCE(rec.quantity_received, 0) AS open_quantity,
       rec.first_receipt_date, rec.last_receipt_date, COALESCE(rec.receipt_count, 0) AS receipt_count,
       pol.unit_cost,
       CASE
         WHEN pol.quantity_ordered - pol.quantity_cancelled - COALESCE(rec.quantity_received,0) > 0
              AND COALESCE(rec.quantity_received,0) = 0 THEN 'open'
         WHEN pol.quantity_ordered - pol.quantity_cancelled - COALESCE(rec.quantity_received,0) > 0
              THEN 'partially_received'
         WHEN pol.quantity_cancelled > 0 THEN 'closed_short'
         ELSE 'received'
       END AS line_status
FROM ops.purchase_order_lines pol
JOIN ops.purchase_orders po ON po.purchase_order_id = pol.purchase_order_id
LEFT JOIN rec ON rec.po_line_id = pol.po_line_id;
```

### 3.4 `analytics.v_po_status`

Grain: one row per PO. Lead time and delay are defined at the PO level from the **first receipt** (the generator ships all lines of a PO together; remainders of partial lines arrive later).

```sql
DROP VIEW IF EXISTS analytics.v_po_status CASCADE;
CREATE VIEW analytics.v_po_status AS
SELECT purchase_order_id, po_number, supplier_id, store_id, order_date, promised_delivery_date,
       COUNT(*)::int                                   AS line_count,
       SUM(quantity_ordered)::int                      AS units_ordered,
       SUM(quantity_received)::int                     AS units_received,
       SUM(quantity_cancelled)::int                    AS units_cancelled,
       SUM(open_quantity)::int                         AS units_open,
       MIN(first_receipt_date)                         AS first_receipt_date,
       MIN(first_receipt_date) - order_date            AS lead_time_days,
       MIN(first_receipt_date) - promised_delivery_date AS delay_days,
       CASE WHEN MIN(first_receipt_date) IS NULL THEN NULL
            ELSE MIN(first_receipt_date) <= promised_delivery_date END AS on_time,
       BOOL_AND(quantity_cancelled = 0 AND receipt_count = 1
                AND quantity_received = quantity_ordered)              AS in_full,
       CASE
         WHEN SUM(open_quantity) = 0 AND SUM(quantity_cancelled) > 0 THEN 'closed_short'
         WHEN SUM(open_quantity) = 0                                 THEN 'received'
         WHEN SUM(quantity_received) > 0                             THEN 'partially_received'
         ELSE 'open'
       END AS po_status
FROM analytics.v_po_line_status
GROUP BY purchase_order_id, po_number, supplier_id, store_id, order_date, promised_delivery_date;
```

### 3.5 `analytics.v_supplier_lane_performance`

Grain: supplier × store, relative to the current run's as-of date.

```sql
DROP VIEW IF EXISTS analytics.v_supplier_lane_performance CASCADE;
CREATE VIEW analytics.v_supplier_lane_performance AS
WITH cr AS (SELECT as_of_date FROM analytics.v_current_run)
SELECT p.supplier_id, p.store_id,
       COUNT(*) FILTER (WHERE p.first_receipt_date <= cr.as_of_date)                       AS received_pos,
       ROUND(AVG(p.lead_time_days) FILTER (WHERE p.first_receipt_date <= cr.as_of_date), 2) AS mean_lead_time_days,
       ROUND(STDDEV_SAMP(p.lead_time_days) FILTER (WHERE p.first_receipt_date <= cr.as_of_date), 2) AS std_lead_time_days,
       COUNT(*) FILTER (WHERE p.promised_delivery_date BETWEEN cr.as_of_date - 89 AND cr.as_of_date) AS pos_due_90d,
       COUNT(*) FILTER (WHERE p.promised_delivery_date BETWEEN cr.as_of_date - 89 AND cr.as_of_date
                          AND p.first_receipt_date <= p.promised_delivery_date)                AS on_time_pos_90d,
       COUNT(*) FILTER (WHERE p.promised_delivery_date <= cr.as_of_date
                          AND p.first_receipt_date IS NULL)                                    AS overdue_open_pos
FROM analytics.v_po_status p
CROSS JOIN cr
GROUP BY p.supplier_id, p.store_id;
```

### 3.6 `analytics.v_supplier_performance`

Grain: supplier. Feeds the Supplier Performance page (`sql/api/suppliers_list.sql` selects from it).

```sql
DROP VIEW IF EXISTS analytics.v_supplier_performance CASCADE;
CREATE VIEW analytics.v_supplier_performance AS
WITH cr AS (SELECT run_id, as_of_date FROM analytics.v_current_run),
po_stats AS (
    SELECT p.supplier_id,
           COUNT(*) FILTER (WHERE p.promised_delivery_date BETWEEN cr.as_of_date - 89 AND cr.as_of_date) AS pos_due_90d,
           COUNT(*) FILTER (WHERE p.promised_delivery_date BETWEEN cr.as_of_date - 89 AND cr.as_of_date
                              AND p.first_receipt_date <= p.promised_delivery_date)                AS on_time_pos_90d,
           COUNT(*) FILTER (WHERE p.promised_delivery_date BETWEEN cr.as_of_date - 89 AND cr.as_of_date
                              AND p.in_full)                                                       AS in_full_pos_90d,
           AVG(p.lead_time_days)        FILTER (WHERE p.first_receipt_date > cr.as_of_date - 180) AS mean_lead_time_days,
           STDDEV_SAMP(p.lead_time_days) FILTER (WHERE p.first_receipt_date > cr.as_of_date - 180) AS std_lead_time_days,
           percentile_cont(0.9) WITHIN GROUP (ORDER BY p.lead_time_days)
               FILTER (WHERE p.first_receipt_date > cr.as_of_date - 180)                          AS p90_lead_time_days,
           COUNT(*) FILTER (WHERE p.first_receipt_date IS NULL AND p.promised_delivery_date <= cr.as_of_date) AS overdue_open_pos
    FROM analytics.v_po_status p CROSS JOIN cr
    GROUP BY p.supplier_id
),
exposure AS (
    SELECT r.supplier_id,
           COUNT(*) FILTER (WHERE r.risk_tier IN ('critical','high')) AS at_risk_positions,
           SUM(r.margin_at_risk_usd)                                  AS margin_at_risk_usd
    FROM analytics.inventory_risk_snapshots r JOIN cr ON r.run_id = cr.run_id
    GROUP BY r.supplier_id
)
SELECT s.supplier_id, s.supplier_code, s.supplier_name, c.category_name,
       ps.pos_due_90d,
       ROUND(ps.on_time_pos_90d::numeric / NULLIF(ps.pos_due_90d, 0), 4) AS on_time_rate,
       ROUND(ps.in_full_pos_90d::numeric / NULLIF(ps.pos_due_90d, 0), 4) AS in_full_rate,
       ROUND(ps.mean_lead_time_days::numeric, 2) AS mean_lead_time_days,
       ROUND(ps.std_lead_time_days::numeric, 2)  AS std_lead_time_days,
       ROUND(ps.p90_lead_time_days::numeric, 1)  AS p90_lead_time_days,
       ROUND(ps.std_lead_time_days::numeric / NULLIF(ps.mean_lead_time_days, 0), 4) AS lead_time_cv,
       ps.overdue_open_pos,
       COALESCE(e.at_risk_positions, 0)    AS at_risk_positions,
       COALESCE(e.margin_at_risk_usd, 0)   AS margin_at_risk_usd,
       ( (ps.on_time_pos_90d::numeric / NULLIF(ps.pos_due_90d,0) < 0.80
          OR ps.std_lead_time_days / NULLIF(ps.mean_lead_time_days,0) > 0.35)
         AND COALESCE(e.at_risk_positions,0) >= 1 )               AS review_flag,
       RANK() OVER (ORDER BY ps.on_time_pos_90d::numeric / NULLIF(ps.pos_due_90d,0) ASC NULLS LAST) AS reliability_rank
FROM ops.suppliers s
JOIN ops.product_categories c ON c.category_id = s.primary_category_id
LEFT JOIN po_stats ps ON ps.supplier_id = s.supplier_id
LEFT JOIN exposure e  ON e.supplier_id = s.supplier_id;
```

`review_flag` thresholds (on-time < 80% or lead-time CV > 0.35, with ≥ 1 at-risk position) are defined here and documented in 05 §9.5.

### 3.7 `analytics.v_category_dow_profile`

Reporting version of the day-of-week index (as of the current run). The pipeline uses the parameterized equivalent `sql/pipeline/extract_category_dow_profile.sql` with identical logic.

```sql
DROP VIEW IF EXISTS analytics.v_category_dow_profile CASCADE;
CREATE VIEW analytics.v_category_dow_profile AS
WITH cr AS (SELECT as_of_date FROM analytics.v_current_run),
base AS (
    SELECT p.category_id, c.iso_day_of_week, m.units_sold
    FROM analytics.mv_daily_position m
    JOIN ops.products p ON p.product_id = m.product_id
    JOIN ops.calendar c ON c.calendar_date = m.position_date
    CROSS JOIN cr
    WHERE m.position_date BETWEEN cr.as_of_date - 55 AND cr.as_of_date
      AND m.availability_status = 'in_stock'
      AND NOT m.is_promo_day
),
by_dow AS (
    SELECT category_id, iso_day_of_week, AVG(units_sold) AS avg_units, COUNT(*) AS n_obs
    FROM base GROUP BY category_id, iso_day_of_week
)
SELECT category_id, iso_day_of_week, avg_units, n_obs,
       avg_units / NULLIF(AVG(avg_units) OVER (PARTITION BY category_id), 0) AS dow_index
FROM by_dow;
```

The index averages to exactly 1.0 across the 7 weekdays of each category.

### 3.8 `analytics.v_product_abc_class`

Chain-wide revenue classification over the trailing 56 days (A = products that make up the first 80% of revenue, B = next 15%, C = rest).

```sql
DROP VIEW IF EXISTS analytics.v_product_abc_class CASCADE;
CREATE VIEW analytics.v_product_abc_class AS
WITH cr AS (SELECT as_of_date FROM analytics.v_current_run),
rev AS (
    SELECT m.product_id, SUM(m.net_sales_amount) AS revenue
    FROM analytics.mv_daily_position m CROSS JOIN cr
    WHERE m.position_date BETWEEN cr.as_of_date - 55 AND cr.as_of_date
    GROUP BY m.product_id
),
ranked AS (
    SELECT product_id, revenue,
           SUM(revenue) OVER (ORDER BY revenue DESC, product_id ROWS UNBOUNDED PRECEDING) - revenue AS revenue_before,
           SUM(revenue) OVER () AS total_revenue
    FROM rev
)
SELECT product_id, revenue,
       ROUND(revenue_before / NULLIF(total_revenue, 0), 4) AS cumulative_share_before,
       CASE WHEN revenue_before / NULLIF(total_revenue, 0) < 0.80 THEN 'A'
            WHEN revenue_before / NULLIF(total_revenue, 0) < 0.95 THEN 'B'
            ELSE 'C' END AS abc_class
FROM ranked;
```

Using the share **before** the product ensures the single largest product is always class A.

### 3.9 `analytics.v_stockout_episodes` (gaps and islands)

```sql
DROP VIEW IF EXISTS analytics.v_stockout_episodes CASCADE;
CREATE VIEW analytics.v_stockout_episodes AS
WITH flagged AS (
    SELECT store_id, product_id, position_date, is_censored,
           position_date - (ROW_NUMBER() OVER (
               PARTITION BY store_id, product_id, is_censored ORDER BY position_date))::int AS island_key
    FROM analytics.mv_daily_position
)
SELECT store_id, product_id,
       MIN(position_date) AS episode_start,
       MAX(position_date) AS episode_end,
       COUNT(*)::int      AS episode_days
FROM flagged
WHERE is_censored
GROUP BY store_id, product_id, island_key;
```

### 3.10 `analytics.v_inventory_reconciliation`

Built directly from `ops` tables (not the MV) so DQ01 can run before the MV is refreshed.

```sql
DROP VIEW IF EXISTS analytics.v_inventory_reconciliation CASCADE;
CREATE VIEW analytics.v_inventory_reconciliation AS
WITH rec AS (
    SELECT po.store_id, pol.product_id, r.received_date AS d, SUM(r.quantity_received)::int AS units_received
    FROM ops.inventory_receipts r
    JOIN ops.purchase_order_lines pol ON pol.po_line_id = r.po_line_id
    JOIN ops.purchase_orders po ON po.purchase_order_id = pol.purchase_order_id
    GROUP BY 1, 2, 3
),
adj AS (
    SELECT store_id, product_id, adjustment_date AS d, SUM(quantity_delta)::int AS net_adjustment
    FROM ops.inventory_adjustments GROUP BY 1, 2, 3
)
SELECT i.store_id, i.product_id, i.snapshot_date,
       i.opening_on_hand, COALESCE(rec.units_received, 0) AS units_received,
       s.units_sold, COALESCE(adj.net_adjustment, 0) AS net_adjustment, i.closing_on_hand,
       i.opening_on_hand + COALESCE(rec.units_received, 0) - s.units_sold + COALESCE(adj.net_adjustment, 0)
           AS expected_closing,
       i.closing_on_hand
         - (i.opening_on_hand + COALESCE(rec.units_received, 0) - s.units_sold + COALESCE(adj.net_adjustment, 0))
           AS discrepancy
FROM ops.inventory_snapshots i
JOIN ops.daily_sales s ON s.store_id = i.store_id AND s.product_id = i.product_id AND s.sales_date = i.snapshot_date
LEFT JOIN rec ON rec.store_id = i.store_id AND rec.product_id = i.product_id AND rec.d = i.snapshot_date
LEFT JOIN adj ON adj.store_id = i.store_id AND adj.product_id = i.product_id AND adj.d = i.snapshot_date;
```

### 3.11 `analytics.v_current_risk`

The read model for the Risk Monitor: current-run risk joined to dimensions and recommendations.

```sql
DROP VIEW IF EXISTS analytics.v_current_risk CASCADE;
CREATE VIEW analytics.v_current_risk AS
SELECT r.run_id, r.store_id, st.store_code, st.store_name, st.region_id, rg.region_name,
       r.product_id, p.sku, p.product_name, p.category_id, pc.category_name,
       r.supplier_id, su.supplier_name,
       p.unit_price, p.unit_cost,
       r.on_hand_units, r.on_order_units, r.inventory_position_units,
       r.avg_daily_demand_units, r.days_of_cover,
       r.next_receipt_date, r.next_receipt_units, r.next_receipt_po_id, npo.po_number AS next_receipt_po_number,
       r.next_receipt_overdue,
       r.lead_time_mean_days, r.safety_stock_units, r.reorder_point_units, r.order_up_to_units,
       r.below_reorder_point, r.stockout_probability, r.risk_tier, r.risk_drivers,
       r.expected_shortage_units, r.revenue_at_risk_usd, r.margin_at_risk_usd,
       r.projected_stockout_date, r.days_until_projected_stockout, r.currently_out_of_stock,
       rr.action_type, rr.urgency, rr.priority_rank, rr.recommended_order_units, rr.recommended_order_cost_usd,
       rr.related_purchase_order_id
FROM analytics.inventory_risk_snapshots r
JOIN analytics.v_current_run cr ON cr.run_id = r.run_id
JOIN ops.stores st              ON st.store_id = r.store_id
JOIN ops.regions rg             ON rg.region_id = st.region_id
JOIN ops.products p             ON p.product_id = r.product_id
JOIN ops.product_categories pc  ON pc.category_id = p.category_id
JOIN ops.suppliers su           ON su.supplier_id = r.supplier_id
JOIN analytics.replenishment_recommendations rr
  ON rr.run_id = r.run_id AND rr.store_id = r.store_id AND rr.product_id = r.product_id
LEFT JOIN ops.purchase_orders npo ON npo.purchase_order_id = r.next_receipt_po_id;
```

### 3.12 `analytics.v_risk_trend`

One row per (as-of date, store, category, tier) using the latest successful run per as-of date.

```sql
DROP VIEW IF EXISTS analytics.v_risk_trend CASCADE;
CREATE VIEW analytics.v_risk_trend AS
WITH latest_runs AS (
    SELECT DISTINCT ON (as_of_date) run_id, as_of_date, run_type
    FROM analytics.analytics_runs
    WHERE status = 'succeeded'
    ORDER BY as_of_date, (run_type = 'current') DESC, completed_at DESC
)
SELECT lr.as_of_date, lr.run_id, r.store_id, st.region_id, p.category_id, r.risk_tier,
       COUNT(*)::int                 AS positions,
       SUM(r.margin_at_risk_usd)     AS margin_at_risk_usd,
       SUM(r.revenue_at_risk_usd)    AS revenue_at_risk_usd
FROM latest_runs lr
JOIN analytics.inventory_risk_snapshots r ON r.run_id = lr.run_id
JOIN ops.products p ON p.product_id = r.product_id
JOIN ops.stores st  ON st.store_id = r.store_id
GROUP BY lr.as_of_date, lr.run_id, r.store_id, st.region_id, p.category_id, r.risk_tier;
```

---

## 4. Pipeline extraction queries (`sql/pipeline/`) — point-in-time

All pipeline queries take `:as_of` (date) and must not read any row dated after `:as_of`. This guarantees backfill runs and backtests are leakage-free. Each has a test asserting that results for `as_of = D` are unchanged when rows after `D` are deleted (10 §4.3).

| File | Output grain | Columns (key) | Notes |
|------|--------------|---------------|-------|
| `extract_daily_history.sql` | store × product × date for `[:as_of − :history_days + 1, :as_of]` | `units_sold`, `availability_status`, `is_promo_day`, `iso_day_of_week`, `category_id` | From `mv_daily_position`; `:history_days` = 56 for forecasting, full history for backtest |
| `extract_category_dow_profile.sql` | category × weekday | `dow_index`, `n_obs` | Same logic as §3.7 with `:as_of` |
| `extract_store_scale.sql` | store × category | `store_scale` = store's mean clean-day units per position ÷ chain mean | Trailing 56 days |
| `extract_product_chain_rate.sql` | product | chain mean clean non-promo units per position-day over 56 days, `n_clean_chain` | For chain fallback |
| `extract_on_hand.sql` | store × product | `closing_on_hand` at `:as_of`, `recent_censored_days` (last 28) | |
| `extract_open_po_lines.sql` | PO line open at `:as_of` | `purchase_order_id`, `po_number`, `store_id`, `product_id`, `supplier_id`, `order_date`, `promised_delivery_date`, `open_quantity_as_of` | See below |
| `extract_lane_lead_times.sql` | supplier × store | `n_received`, mean/std lead time, mean/std delay, mean delay when late, on-time rate (90d) | POs with first receipt ≤ `:as_of` within trailing 180 days |
| `extract_supplier_lead_times.sql` | supplier | same stats pooled across stores | Fallback level |
| `extract_planned_promotions.sql` | store × product × date for `(:as_of, :as_of + 42]` | `promotion_id`, `planned_lift` | Promotions are plans known in advance |
| `extract_positions.sql` | store × product | `supplier_id` (primary), `case_pack_qty`, `min_order_qty`, `unit_price`, `unit_cost`, `category_code`, `contract_lead_time_days` | |
| `extract_latent_demand.sql` | store × product × date | `latent_units` | **Backtest simulation-only basis only** |

### 4.1 `extract_open_po_lines.sql` (point-in-time)

```sql
-- Open PO lines as of :as_of. A line is open if it was ordered on/before :as_of and
-- quantity ordered − cancelled − received-by-:as_of > 0.
-- Cancellation is recorded when the short shipment is received; treat quantity_cancelled
-- as known only if the line's first receipt happened on/before :as_of.
WITH rec AS (
    SELECT po_line_id,
           SUM(quantity_received) FILTER (WHERE received_date <= :as_of)::int AS received_as_of,
           MIN(received_date) AS first_receipt_date
    FROM ops.inventory_receipts
    GROUP BY po_line_id
)
SELECT po.purchase_order_id, po.po_number, po.supplier_id, po.store_id, pol.product_id,
       po.order_date, po.promised_delivery_date,
       pol.quantity_ordered
         - CASE WHEN rec.first_receipt_date <= :as_of THEN pol.quantity_cancelled ELSE 0 END
         - COALESCE(rec.received_as_of, 0) AS open_quantity_as_of
FROM ops.purchase_order_lines pol
JOIN ops.purchase_orders po ON po.purchase_order_id = pol.purchase_order_id
LEFT JOIN rec ON rec.po_line_id = pol.po_line_id
WHERE po.order_date <= :as_of
  AND pol.quantity_ordered
        - CASE WHEN rec.first_receipt_date <= :as_of THEN pol.quantity_cancelled ELSE 0 END
        - COALESCE(rec.received_as_of, 0) > 0;
```

### 4.2 `extract_lane_lead_times.sql` (point-in-time)

```sql
WITH po_first AS (
    SELECT po.purchase_order_id, po.supplier_id, po.store_id, po.order_date, po.promised_delivery_date,
           MIN(r.received_date) AS first_receipt_date
    FROM ops.purchase_orders po
    JOIN ops.purchase_order_lines pol ON pol.purchase_order_id = po.purchase_order_id
    LEFT JOIN ops.inventory_receipts r ON r.po_line_id = pol.po_line_id AND r.received_date <= :as_of
    WHERE po.order_date <= :as_of
    GROUP BY po.purchase_order_id, po.supplier_id, po.store_id, po.order_date, po.promised_delivery_date
),
received AS (
    SELECT *, first_receipt_date - order_date AS lead_time_days,
              first_receipt_date - promised_delivery_date AS delay_days
    FROM po_first
    WHERE first_receipt_date IS NOT NULL AND first_receipt_date > :as_of - 180
)
SELECT l.supplier_id, l.store_id, l.contract_lead_time_days,
       COUNT(r.purchase_order_id)                              AS n_received,
       AVG(r.lead_time_days)::numeric(6,2)                     AS mean_lead_time_days,
       STDDEV_SAMP(r.lead_time_days)::numeric(6,2)             AS std_lead_time_days,
       AVG(r.delay_days)::numeric(6,2)                         AS mean_delay_days,
       STDDEV_SAMP(r.delay_days)::numeric(6,2)                 AS std_delay_days,
       AVG(r.delay_days) FILTER (WHERE r.delay_days > 0)::numeric(6,2) AS mean_delay_when_late_days,
       (SELECT COUNT(*) FILTER (WHERE pf.first_receipt_date <= pf.promised_delivery_date)::numeric
               / NULLIF(COUNT(*), 0)
          FROM po_first pf
         WHERE pf.supplier_id = l.supplier_id AND pf.store_id = l.store_id
           AND pf.promised_delivery_date BETWEEN :as_of - 89 AND :as_of)  AS on_time_rate_90d
FROM ops.supplier_store_lanes l
LEFT JOIN received r ON r.supplier_id = l.supplier_id AND r.store_id = l.store_id
GROUP BY l.supplier_id, l.store_id, l.contract_lead_time_days;
```

Note: In `on_time_rate_90d`, a PO due in the window with no receipt by `:as_of` has `first_receipt_date IS NULL`, so the comparison is NULL and the PO counts in the denominator but not the numerator (i.e., **late**). This is intentional.

---

## 5. Portfolio analyses (`sql/analyses/`)

Each file is standalone (`psql -f`). Ops-only analyses take their as-of from `ops.dataset_manifest.history_end_date`; analyses over model outputs use `analytics.v_current_run`. Each has a DB test asserting it executes, returns the documented columns, and satisfies one invariant (listed).

### 5.1 `01_rolling_sales_velocity.sql` — Rolling sales velocity by store and SKU

- **Question:** How fast is each position selling, and how much do stockouts distort a naive average?
- **Constructs:** CTE, window `AVG … OVER` with `ROWS` frames, `COUNT(*) FILTER … OVER`, joins.
- **Grain:** store × SKU at as-of date.

```sql
WITH params AS (SELECT history_end_date AS as_of FROM ops.dataset_manifest),
daily AS (
    SELECT m.store_id, m.product_id, m.position_date, m.units_sold, m.availability_status
    FROM analytics.mv_daily_position m, params
    WHERE m.position_date > params.as_of - 90
),
rolling AS (
    SELECT d.*,
           AVG(units_sold) OVER w7                                                AS avg_units_7d,
           AVG(units_sold) OVER w28                                               AS avg_units_28d,
           AVG(units_sold) FILTER (WHERE availability_status = 'in_stock') OVER w28 AS avg_units_28d_in_stock,
           COUNT(*) FILTER (WHERE availability_status <> 'in_stock') OVER w28      AS censored_days_28d
    FROM daily d
    WINDOW w7  AS (PARTITION BY store_id, product_id ORDER BY position_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW),
           w28 AS (PARTITION BY store_id, product_id ORDER BY position_date ROWS BETWEEN 27 PRECEDING AND CURRENT ROW)
)
SELECT s.store_code, p.sku, p.product_name,
       ROUND(r.avg_units_7d, 2)  AS avg_units_7d,
       ROUND(r.avg_units_28d, 2) AS avg_units_28d,
       ROUND(r.avg_units_28d_in_stock, 2) AS avg_units_28d_in_stock,
       r.censored_days_28d,
       ROUND(r.avg_units_28d_in_stock - r.avg_units_28d, 2) AS censoring_gap_units
FROM rolling r
JOIN params ON r.position_date = params.as_of
JOIN ops.stores s   ON s.store_id = r.store_id
JOIN ops.products p ON p.product_id = r.product_id
ORDER BY censoring_gap_units DESC NULLS LAST
LIMIT 50;
```

- **Invariant test:** `avg_units_28d_in_stock >= avg_units_28d` is **not** guaranteed; test instead that `censored_days_28d BETWEEN 0 AND 28`.

### 5.2 `02_demand_trends.sql` — Demand trends over time

- **Question:** How are category demand and availability trending week over week by region?
- **Constructs:** 6-table join, `LAG`, moving average frame, `COUNT FILTER`, partial-week exclusion.

```sql
WITH weekly AS (
    SELECT c.week_start_date, pc.category_name, rg.region_name,
           COUNT(DISTINCT m.position_date)              AS days_in_week,
           SUM(m.units_sold)                            AS units,
           SUM(m.net_sales_amount)                      AS revenue,
           AVG(m.is_censored::int)::numeric(6,4)        AS censored_share
    FROM analytics.mv_daily_position m
    JOIN ops.calendar c            ON c.calendar_date = m.position_date
    JOIN ops.products p            ON p.product_id = m.product_id
    JOIN ops.product_categories pc ON pc.category_id = p.category_id
    JOIN ops.stores s              ON s.store_id = m.store_id
    JOIN ops.regions rg            ON rg.region_id = s.region_id
    GROUP BY c.week_start_date, pc.category_name, rg.region_name
)
SELECT week_start_date, category_name, region_name, units, revenue, censored_share,
       LAG(units) OVER w AS prior_week_units,
       ROUND(100.0 * (units - LAG(units) OVER w) / NULLIF(LAG(units) OVER w, 0), 1) AS wow_change_pct,
       ROUND(AVG(units) OVER (PARTITION BY category_name, region_name ORDER BY week_start_date
                              ROWS BETWEEN 3 PRECEDING AND CURRENT ROW), 1) AS units_4wk_moving_avg
FROM weekly
WHERE days_in_week = 7
WINDOW w AS (PARTITION BY category_name, region_name ORDER BY week_start_date)
ORDER BY category_name, region_name, week_start_date;
```

- **Invariant:** every row has `days_in_week = 7`; 8 categories × 4 regions × (complete weeks) rows.

### 5.3 `03_days_of_cover.sql` — Inventory days of cover

- **Question:** How many days will current stock last, and how is cover distributed?
- **Constructs:** CTEs, `CASE` bucketing, `percentile_cont`, `GROUPING SETS`.
- **Note:** This is the *descriptive* days of cover (on hand ÷ trailing 28-day in-stock sales rate). The application's `days_of_cover` uses the forecast (05 §5.7). The analysis outputs both when a current run exists, for comparison.

```sql
WITH params AS (SELECT history_end_date AS as_of FROM ops.dataset_manifest),
rate AS (
    SELECT m.store_id, m.product_id,
           AVG(m.units_sold) FILTER (WHERE m.availability_status = 'in_stock') AS in_stock_rate_28d
    FROM analytics.mv_daily_position m, params
    WHERE m.position_date BETWEEN params.as_of - 27 AND params.as_of
    GROUP BY m.store_id, m.product_id
),
cover AS (
    SELECT i.store_id, i.product_id, i.closing_on_hand,
           r.in_stock_rate_28d,
           CASE WHEN COALESCE(r.in_stock_rate_28d, 0) = 0 THEN NULL
                ELSE LEAST(i.closing_on_hand / r.in_stock_rate_28d, 365) END AS days_of_cover_descriptive
    FROM ops.inventory_snapshots i
    JOIN params ON i.snapshot_date = params.as_of
    JOIN rate r ON r.store_id = i.store_id AND r.product_id = i.product_id
),
bucketed AS (
    SELECT c.*, pc.category_name,
           CASE WHEN c.closing_on_hand = 0 THEN '0 · out of stock'
                WHEN c.days_of_cover_descriptive IS NULL THEN '— · no recent demand'
                WHEN c.days_of_cover_descriptive < 7  THEN '1 · < 7 days'
                WHEN c.days_of_cover_descriptive < 14 THEN '2 · 7–13 days'
                WHEN c.days_of_cover_descriptive < 28 THEN '3 · 14–27 days'
                WHEN c.days_of_cover_descriptive < 56 THEN '4 · 28–55 days'
                ELSE '5 · 56+ days' END AS cover_bucket
    FROM cover c
    JOIN ops.products p ON p.product_id = c.product_id
    JOIN ops.product_categories pc ON pc.category_id = p.category_id
)
SELECT COALESCE(category_name, 'All categories') AS category_name, cover_bucket,
       COUNT(*) AS positions,
       ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY days_of_cover_descriptive)::numeric, 1) AS median_cover_days
FROM bucketed
GROUP BY GROUPING SETS ((category_name, cover_bucket), (cover_bucket))
ORDER BY category_name NULLS FIRST, cover_bucket;
```

### 5.4 `04_supplier_lead_time.sql` — Lead-time performance by supplier

- **Constructs:** joins, `AVG`, `STDDEV_SAMP`, `percentile_cont` (P50/P90), CV, `RANK`.

```sql
WITH params AS (SELECT history_end_date AS as_of FROM ops.dataset_manifest),
received AS (
    SELECT p.*, l.contract_lead_time_days
    FROM analytics.v_po_status p
    JOIN ops.supplier_store_lanes l ON l.supplier_id = p.supplier_id AND l.store_id = p.store_id
    CROSS JOIN params
    WHERE p.first_receipt_date IS NOT NULL AND p.first_receipt_date > params.as_of - 180
)
SELECT s.supplier_code, s.supplier_name,
       COUNT(*)                                                         AS received_pos,
       ROUND(AVG(contract_lead_time_days), 1)                           AS avg_contract_lead_time_days,
       ROUND(AVG(lead_time_days), 2)                                    AS mean_lead_time_days,
       ROUND(STDDEV_SAMP(lead_time_days), 2)                            AS std_lead_time_days,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY lead_time_days)      AS p50_lead_time_days,
       percentile_cont(0.9) WITHIN GROUP (ORDER BY lead_time_days)      AS p90_lead_time_days,
       ROUND(STDDEV_SAMP(lead_time_days) / NULLIF(AVG(lead_time_days), 0), 3) AS lead_time_cv,
       ROUND(AVG(lead_time_days - contract_lead_time_days), 2)          AS mean_days_over_contract,
       RANK() OVER (ORDER BY STDDEV_SAMP(lead_time_days) / NULLIF(AVG(lead_time_days), 0) DESC) AS variability_rank
FROM received r
JOIN ops.suppliers s ON s.supplier_id = r.supplier_id
GROUP BY s.supplier_code, s.supplier_name
ORDER BY variability_rank;
```

- **Invariant:** `p50 <= p90`; `received_pos > 0` for every supplier in standard preset.

### 5.5 `05_supplier_reliability.sql` — Supplier delivery reliability (trailing vs prior 90 days)

- **Constructs:** conditional aggregation over two periods, `LAG`-free period comparison, `DENSE_RANK`.

```sql
WITH params AS (SELECT history_end_date AS as_of FROM ops.dataset_manifest),
due AS (
    SELECT p.supplier_id,
           CASE WHEN p.promised_delivery_date BETWEEN params.as_of - 89  AND params.as_of      THEN 'recent'
                WHEN p.promised_delivery_date BETWEEN params.as_of - 179 AND params.as_of - 90 THEN 'prior' END AS period,
           (p.first_receipt_date IS NOT NULL AND p.first_receipt_date <= p.promised_delivery_date) AS on_time,
           COALESCE(p.in_full, false) AS in_full
    FROM analytics.v_po_status p CROSS JOIN params
    WHERE p.promised_delivery_date BETWEEN params.as_of - 179 AND params.as_of
)
SELECT s.supplier_code, s.supplier_name,
       COUNT(*) FILTER (WHERE period = 'recent') AS pos_recent,
       ROUND(AVG(on_time::int) FILTER (WHERE period = 'recent'), 4)            AS on_time_rate_recent,
       ROUND(AVG(on_time::int) FILTER (WHERE period = 'prior'), 4)             AS on_time_rate_prior,
       ROUND(AVG(in_full::int) FILTER (WHERE period = 'recent'), 4)            AS in_full_rate_recent,
       ROUND(AVG((on_time AND in_full)::int) FILTER (WHERE period = 'recent'), 4) AS otif_rate_recent,
       ROUND(AVG(on_time::int) FILTER (WHERE period = 'recent')
           - AVG(on_time::int) FILTER (WHERE period = 'prior'), 4)             AS on_time_rate_change,
       DENSE_RANK() OVER (ORDER BY AVG(on_time::int) FILTER (WHERE period = 'recent')) AS worst_first_rank
FROM due JOIN ops.suppliers s ON s.supplier_id = due.supplier_id
GROUP BY s.supplier_code, s.supplier_name
ORDER BY worst_first_rank;
```

- **Invariant:** all rates in [0, 1]; `otif_rate_recent <= least(on_time_rate_recent, in_full_rate_recent)`.

### 5.6 `06_stockout_frequency.sql` — Historical stockout frequency

- **Constructs:** gaps-and-islands via `v_stockout_episodes`, conditional aggregation, `MAX`, joins.

```sql
WITH freq AS (
    SELECT m.store_id, m.product_id,
           COUNT(*)                                         AS days_observed,
           COUNT(*) FILTER (WHERE m.availability_status = 'out_all_day') AS out_all_day_days,
           COUNT(*) FILTER (WHERE m.availability_status = 'sold_out')    AS sold_out_days,
           MAX(m.position_date) FILTER (WHERE m.is_censored)             AS last_stockout_date
    FROM analytics.mv_daily_position m
    GROUP BY m.store_id, m.product_id
),
episodes AS (
    SELECT store_id, product_id, COUNT(*) AS episodes, MAX(episode_days) AS longest_episode_days
    FROM analytics.v_stockout_episodes GROUP BY store_id, product_id
)
SELECT s.store_code, p.sku, p.product_name,
       f.out_all_day_days, f.sold_out_days,
       ROUND((f.out_all_day_days + f.sold_out_days)::numeric / f.days_observed, 4) AS stockout_day_rate,
       COALESCE(e.episodes, 0)              AS stockout_episodes,
       COALESCE(e.longest_episode_days, 0)  AS longest_episode_days,
       f.last_stockout_date
FROM freq f
LEFT JOIN episodes e ON e.store_id = f.store_id AND e.product_id = f.product_id
JOIN ops.stores s   ON s.store_id = f.store_id
JOIN ops.products p ON p.product_id = f.product_id
ORDER BY stockout_day_rate DESC, longest_episode_days DESC
LIMIT 50;
```

- **Invariant:** Σ `episode_days` per position = `out_all_day_days + sold_out_days`.

### 5.7 `07_high_risk_identification.sql` — High-risk inventory identification

- **Constructs:** model output join, `ROW_NUMBER` per store, `CASE`.

```sql
WITH ranked AS (
    SELECT v.*,
           ROW_NUMBER() OVER (PARTITION BY v.store_id
                              ORDER BY v.risk_tier DESC, v.margin_at_risk_usd DESC, v.product_id) AS rank_in_store
    FROM analytics.v_current_risk v
    WHERE v.risk_tier IN ('critical', 'high')
)
SELECT store_code, rank_in_store, sku, product_name, category_name, risk_tier,
       ROUND(stockout_probability * 100, 1) AS stockout_probability_pct,
       on_hand_units, ROUND(avg_daily_demand_units, 1) AS avg_daily_demand_units,
       days_of_cover, next_receipt_date, margin_at_risk_usd, action_type
FROM ranked
WHERE rank_in_store <= 5
ORDER BY store_code, rank_in_store;
```

### 5.8 `08_margin_exposure.sql` — Product-level gross margin exposure (Pareto)

- **Constructs:** aggregation, running total window, share-of-total window, `CASE`.

```sql
WITH by_product AS (
    SELECT v.product_id, v.sku, v.product_name, v.category_name,
           SUM(v.margin_at_risk_usd)  AS margin_at_risk_usd,
           SUM(v.revenue_at_risk_usd) AS revenue_at_risk_usd,
           COUNT(*) FILTER (WHERE v.risk_tier IN ('critical','high')) AS at_risk_stores
    FROM analytics.v_current_risk v
    GROUP BY v.product_id, v.sku, v.product_name, v.category_name
    HAVING SUM(v.margin_at_risk_usd) > 0
)
SELECT sku, product_name, category_name, at_risk_stores, margin_at_risk_usd, revenue_at_risk_usd,
       ROUND(margin_at_risk_usd / SUM(margin_at_risk_usd) OVER (), 4) AS share_of_total,
       ROUND(SUM(margin_at_risk_usd) OVER (ORDER BY margin_at_risk_usd DESC, product_id
                                           ROWS UNBOUNDED PRECEDING)
             / SUM(margin_at_risk_usd) OVER (), 4)                    AS cumulative_share
FROM by_product
ORDER BY margin_at_risk_usd DESC;
```

- **Invariant:** final `cumulative_share = 1.0000`; equals Overview KPI sum.

### 5.9 `09_regional_risk_comparison.sql` — Regional inventory risk comparison

- **Constructs:** conditional aggregation by tier, `ROLLUP`, window comparison to chain average.

```sql
WITH agg AS (
    SELECT COALESCE(region_name, 'Chain total') AS region_name,
           COUNT(*)                                             AS positions,
           COUNT(*) FILTER (WHERE risk_tier = 'critical')       AS critical,
           COUNT(*) FILTER (WHERE risk_tier = 'high')           AS high,
           COUNT(*) FILTER (WHERE risk_tier = 'moderate')       AS moderate,
           COUNT(*) FILTER (WHERE risk_tier = 'low')            AS low,
           SUM(margin_at_risk_usd)                              AS margin_at_risk_usd,
           AVG(stockout_probability)                            AS mean_stockout_probability,
           GROUPING(region_name)                                AS is_total
    FROM analytics.v_current_risk
    GROUP BY ROLLUP (region_name)
)
SELECT region_name, positions, critical, high, moderate, low,
       ROUND((critical + high)::numeric / positions, 4) AS at_risk_share,
       ROUND((critical + high)::numeric / positions
             - MAX(CASE WHEN is_total = 1 THEN (critical + high)::numeric / positions END) OVER (), 4)
                                                       AS at_risk_share_vs_chain,
       ROUND(margin_at_risk_usd, 2) AS margin_at_risk_usd,
       ROUND(mean_stockout_probability, 4) AS mean_stockout_probability
FROM agg
ORDER BY is_total, at_risk_share DESC;
```

### 5.10 `10_demand_volatility.sql` — Demand volatility analysis

- **Constructs:** statistical aggregates (`STDDEV_SAMP`, `regr_slope`), Syntetos–Boylan classification via `CASE`, conditional aggregation over clean days.

```sql
WITH params AS (SELECT history_end_date AS as_of FROM ops.dataset_manifest),
clean AS (
    SELECT m.store_id, m.product_id, m.units_sold,
           (m.position_date - (params.as_of - 55)) AS day_index
    FROM analytics.mv_daily_position m, params
    WHERE m.position_date BETWEEN params.as_of - 55 AND params.as_of
      AND m.availability_status = 'in_stock' AND NOT m.is_promo_day
),
stats AS (
    SELECT store_id, product_id,
           COUNT(*)                                        AS clean_days,
           COUNT(*) FILTER (WHERE units_sold > 0)          AS nonzero_days,
           AVG(units_sold)                                 AS mean_units,
           STDDEV_SAMP(units_sold)                         AS std_units,
           AVG(units_sold) FILTER (WHERE units_sold > 0)   AS mean_nonzero,
           STDDEV_SAMP(units_sold) FILTER (WHERE units_sold > 0) AS std_nonzero,
           REGR_SLOPE(units_sold, day_index)               AS trend_units_per_day
    FROM clean GROUP BY store_id, product_id
),
classified AS (
    SELECT *,
           clean_days::numeric / NULLIF(nonzero_days, 0)          AS adi,
           POWER(std_nonzero / NULLIF(mean_nonzero, 0), 2)        AS cv_squared,
           std_units / NULLIF(mean_units, 0)                      AS cv
    FROM stats
)
SELECT s.store_code, p.sku, p.product_name, clean_days, nonzero_days,
       ROUND(mean_units, 3) AS mean_units, ROUND(cv, 3) AS cv,
       ROUND(adi, 2) AS adi, ROUND(cv_squared, 3) AS cv_squared,
       ROUND(trend_units_per_day, 4) AS trend_units_per_day,
       CASE WHEN nonzero_days = 0                 THEN 'no_demand'
            WHEN adi <= 1.32 AND COALESCE(cv_squared,0) < 0.49 THEN 'smooth'
            WHEN adi <= 1.32                      THEN 'erratic'
            WHEN COALESCE(cv_squared,0) < 0.49    THEN 'intermittent'
            ELSE 'lumpy' END AS demand_pattern
FROM classified c
JOIN ops.stores s   ON s.store_id = c.store_id
JOIN ops.products p ON p.product_id = c.product_id
ORDER BY cv DESC NULLS LAST;
```

- **Invariant:** the `demand_pattern` distribution matches `analytics.demand_forecasts.demand_pattern` for the current run on every position with `clean_days >= 14` (same thresholds; test compares). Positions with fewer clean days may differ because the model applies fallbacks.

### 5.11 `11_po_fulfillment.sql` — Purchase order fulfillment performance

- **Constructs:** joins, monthly grouping via `date_trunc`, conditional aggregation, fill rate.

```sql
WITH params AS (SELECT history_end_date AS as_of FROM ops.dataset_manifest),
lines AS (
    SELECT l.*, date_trunc('month', l.promised_delivery_date)::date AS promised_month
    FROM analytics.v_po_line_status l, params
    WHERE l.promised_delivery_date BETWEEN params.as_of - 179 AND params.as_of
)
SELECT s.supplier_code, promised_month,
       COUNT(DISTINCT purchase_order_id)                                    AS pos,
       COUNT(*)                                                             AS lines,
       SUM(quantity_ordered)                                                AS units_ordered,
       SUM(quantity_received)                                               AS units_received,
       ROUND(SUM(quantity_received)::numeric / NULLIF(SUM(quantity_ordered), 0), 4) AS unit_fill_rate,
       COUNT(*) FILTER (WHERE receipt_count > 1)                            AS split_deliveries,
       COUNT(*) FILTER (WHERE line_status = 'closed_short')                 AS lines_closed_short,
       COUNT(*) FILTER (WHERE line_status IN ('open','partially_received')) AS lines_still_open
FROM lines JOIN ops.suppliers s ON s.supplier_id = lines.supplier_id
GROUP BY s.supplier_code, promised_month
ORDER BY s.supplier_code, promised_month;
```

### 5.12 `12_replenishment_prioritization.sql` — Replenishment prioritization

- **Constructs:** model outputs + dims, `ROW_NUMBER` per store, running total of order cost.

```sql
WITH actions AS (
    SELECT v.*,
           ROW_NUMBER() OVER (PARTITION BY v.store_id ORDER BY v.priority_rank) AS store_rank,
           SUM(COALESCE(v.recommended_order_cost_usd, 0)) OVER (ORDER BY v.priority_rank
                                                               ROWS UNBOUNDED PRECEDING) AS cumulative_order_cost_usd
    FROM analytics.v_current_risk v
    WHERE v.action_type <> 'no_action'
)
SELECT priority_rank, store_code, store_rank, sku, product_name, risk_tier, action_type, urgency,
       ROUND(stockout_probability, 4) AS stockout_probability,
       margin_at_risk_usd, recommended_order_units, recommended_order_cost_usd, cumulative_order_cost_usd
FROM actions
ORDER BY priority_rank
LIMIT 100;
```

- **Invariant:** `priority_rank` is contiguous from 1 with no gaps.

### 5.13 `13_inventory_reconciliation.sql` — Inventory reconciliation and shrink summary

```sql
SELECT COALESCE(s.store_code, 'ALL') AS store_code,
       COALESCE(a.reason_code::text, 'all_reasons') AS reason_code,
       COUNT(*)                 AS adjustment_events,
       SUM(a.quantity_delta)    AS net_units,
       SUM(a.quantity_delta * p.unit_cost) AS net_value_at_cost_usd
FROM ops.inventory_adjustments a
JOIN ops.stores s   ON s.store_id = a.store_id
JOIN ops.products p ON p.product_id = a.product_id
GROUP BY ROLLUP (s.store_code, a.reason_code)
ORDER BY s.store_code NULLS LAST, a.reason_code NULLS LAST;
-- Companion check (must return 0):
-- SELECT COUNT(*) FROM analytics.v_inventory_reconciliation WHERE discrepancy <> 0;
```

### 5.14 `14_abc_xyz_matrix.sql` — ABC × XYZ segmentation

- **Question:** Which SKUs are both high-value and volatile (the hardest to stock)?
- XYZ by chain-level CV of daily clean-day units: X < 0.5, Y 0.5–1.0, Z > 1.0. Cross-tab with conditional aggregation.

```sql
WITH params AS (SELECT history_end_date AS as_of FROM ops.dataset_manifest),
chain_daily AS (
    SELECT m.product_id, m.position_date, SUM(m.units_sold) AS units
    FROM analytics.mv_daily_position m, params
    WHERE m.position_date BETWEEN params.as_of - 55 AND params.as_of
    GROUP BY m.product_id, m.position_date
),
xyz AS (
    SELECT product_id,
           CASE WHEN STDDEV_SAMP(units) / NULLIF(AVG(units), 0) < 0.5 THEN 'X'
                WHEN STDDEV_SAMP(units) / NULLIF(AVG(units), 0) <= 1.0 THEN 'Y'
                ELSE 'Z' END AS xyz_class
    FROM chain_daily GROUP BY product_id
)
SELECT a.abc_class,
       COUNT(*) FILTER (WHERE x.xyz_class = 'X') AS x_products,
       COUNT(*) FILTER (WHERE x.xyz_class = 'Y') AS y_products,
       COUNT(*) FILTER (WHERE x.xyz_class = 'Z') AS z_products,
       ROUND(SUM(a.revenue), 2)                  AS revenue_56d
FROM analytics.v_product_abc_class a
JOIN xyz x ON x.product_id = a.product_id
GROUP BY a.abc_class
ORDER BY a.abc_class;
```

(Requires a current run because `v_product_abc_class` is anchored to it.)

### 5.15 `15_in_stock_rate_trend.sql` — End-of-day in-stock rate by region and week

```sql
SELECT c.week_start_date, rg.region_name,
       ROUND(AVG((m.closing_on_hand > 0)::int), 4)                                   AS in_stock_rate,
       ROUND(AVG((m.closing_on_hand > 0)::int) FILTER (WHERE m.is_promo_day), 4)     AS in_stock_rate_promo,
       ROUND(AVG((m.closing_on_hand > 0)::int) FILTER (WHERE NOT m.is_promo_day), 4) AS in_stock_rate_non_promo
FROM analytics.mv_daily_position m
JOIN ops.calendar c ON c.calendar_date = m.position_date
JOIN ops.stores s   ON s.store_id = m.store_id
JOIN ops.regions rg ON rg.region_id = s.region_id
GROUP BY c.week_start_date, rg.region_name
ORDER BY c.week_start_date, rg.region_name;
```

---

## 6. KPI definitions and lineage

All KPIs are computed in `sql/api/overview_summary.sql` from the current run (`:run_id`) and `:as_of_date`, honoring filters `:store_ids`, `:region_ids`, `:category_ids` (NULL = no filter).

| KPI | API field | Definition (SQL semantics) | Aggregation level | Source tables | Python involvement | Time window |
|-----|-----------|----------------------------|-------------------|---------------|--------------------|-------------|
| Active positions | `active_positions` | `COUNT(*)` of risk snapshots in run (active products only) | position | `inventory_risk_snapshots`, `products` | forecast/risk produce rows | as-of |
| Active SKUs | `active_skus` | `COUNT(DISTINCT product_id)` | product | same | — | as-of |
| At-risk positions | `at_risk_positions` | `COUNT(*) FILTER (WHERE risk_tier IN ('critical','high'))` | position | same | tiers from `risk.py` | as-of |
| Critical positions | `critical_positions` | `COUNT(*) FILTER (WHERE risk_tier = 'critical')` | position | same | same | as-of |
| At-risk share | `at_risk_rate` | at-risk ÷ active | ratio | same | — | as-of |
| At-risk delta | `at_risk_positions_change` | current − value in run with `as_of_date = :as_of_date − 7` | position | `analytics_runs`, snapshots | — | week over week |
| Gross margin at risk | `gross_margin_at_risk_usd` | `SUM(margin_at_risk_usd)` | position sum | snapshots | `exposure.py` | protection window per position |
| Revenue at risk | `revenue_at_risk_usd` | `SUM(revenue_at_risk_usd)` | position sum | snapshots | `exposure.py` | same |
| Median days of cover | `median_days_of_cover` | `percentile_cont(0.5) WITHIN GROUP (ORDER BY days_of_cover) FILTER (WHERE days_of_cover IS NOT NULL)` | position | snapshots | `risk.py` | as-of |
| Supplier on-time rate | `supplier_on_time_rate` | POs with `promised_delivery_date ∈ [as_of−89, as_of]`: on-time ÷ all (unreceived = late) | PO | `v_po_status` | — | trailing 90 days |
| In-stock rate | `in_stock_rate` | `AVG((closing_on_hand > 0)::int)` over position-days in `[as_of−27, as_of]` | position-day | `mv_daily_position` | — | trailing 28 days |
| In-stock rate (prior) | `in_stock_rate_prior` | same over `[as_of−55, as_of−28]` | position-day | same | — | prior 28 days |

**Filter semantics:** store/region filters restrict positions and POs by store. Category filters restrict positions by product category; for the supplier on-time KPI, category filters restrict to suppliers whose `primary_category_id` matches.

### 6.1 `sql/api/overview_summary.sql` (normative)

```sql
WITH f AS (
    SELECT CAST(:store_ids AS integer[])    AS store_ids,
           CAST(:region_ids AS integer[])   AS region_ids,
           CAST(:category_ids AS integer[]) AS category_ids
),
pos AS (
    SELECT r.*
    FROM analytics.inventory_risk_snapshots r
    JOIN ops.products p ON p.product_id = r.product_id
    JOIN ops.stores s   ON s.store_id = r.store_id
    CROSS JOIN f
    WHERE r.run_id = :run_id AND p.is_active
      AND (f.store_ids    IS NULL OR r.store_id    = ANY (f.store_ids))
      AND (f.region_ids   IS NULL OR s.region_id   = ANY (f.region_ids))
      AND (f.category_ids IS NULL OR p.category_id = ANY (f.category_ids))
),
prior AS (
    SELECT COUNT(*) FILTER (WHERE r.risk_tier IN ('critical','high')) AS at_risk_positions
    FROM analytics.inventory_risk_snapshots r
    JOIN ops.products p ON p.product_id = r.product_id
    JOIN ops.stores s   ON s.store_id = r.store_id
    CROSS JOIN f
    WHERE r.run_id = :prior_run_id
      AND (f.store_ids    IS NULL OR r.store_id    = ANY (f.store_ids))
      AND (f.region_ids   IS NULL OR s.region_id   = ANY (f.region_ids))
      AND (f.category_ids IS NULL OR p.category_id = ANY (f.category_ids))
),
po AS (
    SELECT COUNT(*) AS pos_due,
           COUNT(*) FILTER (WHERE v.first_receipt_date <= v.promised_delivery_date) AS pos_on_time
    FROM analytics.v_po_status v
    JOIN ops.stores s    ON s.store_id = v.store_id
    JOIN ops.suppliers su ON su.supplier_id = v.supplier_id
    CROSS JOIN f
    WHERE v.promised_delivery_date BETWEEN CAST(:as_of_date AS date) - 89 AND CAST(:as_of_date AS date)
      AND (f.store_ids    IS NULL OR v.store_id = ANY (f.store_ids))
      AND (f.region_ids   IS NULL OR s.region_id = ANY (f.region_ids))
      AND (f.category_ids IS NULL OR su.primary_category_id = ANY (f.category_ids))
),
instock AS (
    SELECT AVG((m.closing_on_hand > 0)::int) FILTER (WHERE m.position_date >  CAST(:as_of_date AS date) - 28) AS in_stock_rate,
           AVG((m.closing_on_hand > 0)::int) FILTER (WHERE m.position_date <= CAST(:as_of_date AS date) - 28) AS in_stock_rate_prior
    FROM analytics.mv_daily_position m
    JOIN ops.products p ON p.product_id = m.product_id
    JOIN ops.stores s   ON s.store_id = m.store_id
    CROSS JOIN f
    WHERE m.position_date BETWEEN CAST(:as_of_date AS date) - 55 AND CAST(:as_of_date AS date)
      AND (f.store_ids    IS NULL OR m.store_id    = ANY (f.store_ids))
      AND (f.region_ids   IS NULL OR s.region_id   = ANY (f.region_ids))
      AND (f.category_ids IS NULL OR p.category_id = ANY (f.category_ids))
)
SELECT
    (SELECT COUNT(*) FROM pos)                                                        AS active_positions,
    (SELECT COUNT(DISTINCT product_id) FROM pos)                                      AS active_skus,
    (SELECT COUNT(*) FILTER (WHERE risk_tier IN ('critical','high')) FROM pos)        AS at_risk_positions,
    (SELECT COUNT(*) FILTER (WHERE risk_tier = 'critical') FROM pos)                  AS critical_positions,
    (SELECT at_risk_positions FROM prior)                                             AS prior_at_risk_positions,
    (SELECT COALESCE(SUM(margin_at_risk_usd), 0) FROM pos)                            AS gross_margin_at_risk_usd,
    (SELECT COALESCE(SUM(revenue_at_risk_usd), 0) FROM pos)                           AS revenue_at_risk_usd,
    (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY days_of_cover)
       FROM pos WHERE days_of_cover IS NOT NULL)                                      AS median_days_of_cover,
    (SELECT pos_due FROM po)                                                          AS supplier_pos_due,
    (SELECT pos_on_time::numeric / NULLIF(pos_due, 0) FROM po)                        AS supplier_on_time_rate,
    (SELECT in_stock_rate FROM instock)                                               AS in_stock_rate,
    (SELECT in_stock_rate_prior FROM instock)                                         AS in_stock_rate_prior;
```

`:prior_run_id` is resolved by the service: the latest succeeded run with `as_of_date = current.as_of_date − 7` (NULL if absent → `prior_at_risk_positions` NULL → UI hides the delta).

### 6.2 Full lineage table for Overview and Detail metrics

| UI element | API endpoint · field | SQL file | Upstream tables/views | Python function |
|------------|----------------------|----------|-----------------------|-----------------|
| KPI: At-risk positions | `/overview/summary` · `at_risk_positions` | `api/overview_summary.sql` | `inventory_risk_snapshots` | `risk.assign_tier` |
| KPI: Est. gross margin at risk | `/overview/summary` · `gross_margin_at_risk_usd` | same | same | `exposure.compute_exposure` |
| KPI: Median days of cover | `/overview/summary` · `median_days_of_cover` | same | same | `risk.days_of_cover` |
| KPI: Supplier on-time | `/overview/summary` · `supplier_on_time_rate` | same | `v_po_status` ← POs, lines, receipts | — |
| KPI: In-stock rate | `/overview/summary` · `in_stock_rate` | same | `mv_daily_position` | — |
| Risk distribution bar | `/overview/risk-distribution` | `api/risk_distribution.sql` | snapshots | `risk.assign_tier` |
| Risk trend | `/overview/risk-trend` | `api/risk_trend.sql` | `v_risk_trend` | backfill runs |
| Category heatmap | `/overview/category-heatmap` | `api/category_heatmap.sql` | snapshots, products | — |
| Store comparison | `/overview/store-comparison` | `api/store_comparison.sql` | snapshots, stores | — |
| Priority actions | `/recommendations` | `api/recommendations.sql` | `v_current_risk` | `replenishment.rank` |
| Top at-risk products | `/overview/top-products` | `api/top_products.sql` | `v_current_risk` | — |
| Detail: purchase orders | `/positions/{s}/{p}/purchase-orders` | `api/position_purchase_orders.sql` | `v_po_line_status`, `extract_open_po_lines` logic at run as-of, `supplier_lane_estimates` | `leadtime.expected_arrival` |
| Scenario Lab | `/scenarios/evaluate` | `inventory_risk_snapshots`, `demand_forecast_daily`, `supplier_lane_estimates`, `extract_open_po_lines.sql` (baseline cache) | same | `scenario.evaluate` → `risk`, `policy`, `exposure` |
| Risk Monitor rows | `/risk/positions` | `api/risk_positions.sql` | `v_current_risk` | — |
| Detail: breakdown | `/positions/{s}/{p}` | `api/position_detail.sql`, `api/position_checkpoints.sql` | snapshots, checkpoints, forecasts, lane estimates | all |
| Detail: sales history | `/positions/{s}/{p}/history` | `api/position_history.sql` | `mv_daily_position` | — |
| Detail: projection | `/positions/{s}/{p}/projection` | `api/position_projection_inputs.sql` | `demand_forecast_daily`, snapshots, open POs | `risk.project_inventory` (service calls analytics function on stored inputs) |
| Supplier table | `/suppliers` | `api/suppliers_list.sql` | `v_supplier_performance` | — |

---

## 7. API query conventions

1. **Named SQL files** under `sql/api/` loaded by `db/sql_loader.load_sql(name)` (cached in memory).
2. **Bound parameters only.** Never format values into SQL strings. Arrays are passed as Python lists and cast in SQL: `CAST(:store_ids AS integer[])`; `NULL` means "no filter".
3. **Sorting:** column names cannot be bound parameters. Repositories map a validated `sort_by` enum to a fixed SQL fragment via a whitelist dict (e.g., `{"stockout_probability": "stockout_probability"}`) and append `ORDER BY <col> <ASC|DESC>, store_id, product_id` (stable tiebreak).
4. **Pagination:** `LIMIT :limit OFFSET :offset` with a separate `COUNT(*)` over the same filtered CTE (window `COUNT(*) OVER ()` is acceptable).
5. **Run scoping:** Every analytics query filters by `:run_id` explicitly (resolved per request), not by joining `v_current_run`, so a single response is internally consistent even if a new run completes mid-request.
6. **Rounding:** SQL returns full precision; Pydantic schemas round money to 2 decimals, probabilities to 4, days to 1, units per day to 2.

---

## 8. Edge cases

| Case | Handling |
|------|----------|
| Position with zero sales in window | `mean_units = 0`; `adi` NULL; class `no_demand`; days of cover NULL (displayed "No recent demand") |
| Position out of stock for the entire lookback | No clean days; forecasting falls back to chain rate (05 §3.6); analyses show `censored_days_28d = 28` |
| Division by zero | Always `NULLIF(denominator, 0)` |
| Partial weeks at window edges | Excluded via `days_in_week = 7` |
| POs ordered during burn-in | Included in lead-time stats if received within window; `order_date` may precede history start |
| PO not received by as-of but due | Counts as late in on-time KPI; open in risk |
| Line short-closed | `quantity_cancelled` known from first receipt date onward (point-in-time) |
| Supplier with no POs due in last 90 days | `on_time_rate` NULL → UI "—" with tooltip "No deliveries due in window" |
| Overlapping promotions | Prevented by DQ09; MV would otherwise duplicate rows (unique index on MV would fail refresh — a second safety net) |
| Analytics not run | Views anchored to `v_current_run` return 0 rows; API returns 503 `ANALYTICS_NOT_READY` |
| Store or category filter that matches nothing | KPIs return zeros/NULLs; UI shows empty state |
| Multiple runs for same as-of | `v_risk_trend` uses `DISTINCT ON` picking `current` over `backfill`, then latest |

---

## 9. Query optimization plan

### 9.1 Expected expensive queries

| # | Query | Why expensive | Mitigation |
|---|-------|--------------|------------|
| Q1 | `REFRESH MATERIALIZED VIEW mv_daily_position` | Joins 864k × 864k + aggregates receipts/adjustments | Done once per load; PK indexes on both dense tables make the join a merge join; `maintenance_work_mem=256MB` |
| Q2 | `extract_daily_history.sql` (56 days × 4,800) | ~269k rows | `ix_mv_daily_position_date` range scan |
| Q3 | Backtest full-history extract | 864k rows | Sequential scan acceptable (single pass, ~1 s target) |
| Q4 | `risk_positions.sql` with filters + sort + offset | Called on every Risk Monitor interaction | `ix_risk_run_tier_margin`, `ix_risk_run_store`; 4,800 rows per run so worst case is a sort of 4,800 rows |
| Q5 | `overview_summary.sql` | Multiple CTEs incl. 28/56-day MV scan (269k rows) | Date index; consider a small `analytics.mv_daily_store_category` rollup **only if** p95 > 300 ms after measurement |
| Q6 | `position_history.sql` (one position, 56 days) | Frequent | MV unique index (store, product, date) → index range scan |
| Q7 | `v_supplier_performance` | Aggregates all POs (~17k) and lines (~60k) | Small; indexes on PO dates and receipts |
| Q8 | `v_risk_trend` with filters | 13 runs × 4,800 = 62k rows | `ix_risk_run_store`; acceptable |

### 9.2 Procedure (`make explain`, Phase 8)

1. Load the **standard** preset and run analytics.
2. `VACUUM ANALYZE;`
3. For each Q1–Q8, run `sql/explain/qN_*.sql` containing `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) <query with representative params>` three times; record the third (warm cache) execution time.
4. Record in `docs/perf/QUERY_PERFORMANCE.md`: query, plan summary (scan types, join types), execution time, buffers, and any index added with before/after timings.
5. Demonstrate at least one measured improvement: run Q6 and Q2 against a copy of the logic that reads `ops` tables directly versus the MV, and record the difference (this is the evidence for keeping the MV).
6. Never claim a timing that wasn't measured; the document starts as a template with empty result cells.

### 9.3 Performance targets (to be verified, standard preset, Apple Silicon laptop, warm cache)

| Query | Target |
|-------|--------|
| Q1 MV refresh | < 20 s |
| Q2 extract | < 1.5 s |
| Q4 risk positions page | < 100 ms |
| Q5 overview summary | < 300 ms |
| Q6 position history | < 30 ms |
| Q7 supplier performance | < 200 ms |

Assumptions: 16 GB RAM, Docker Desktop with ≥ 4 GB allocated, PostgreSQL settings from 02 §9.1.

### 9.4 Index review checklist

- Every FK column used in joins on large tables is the leading column of some index (or part of the PK).
- No unused indexes on dense fact tables (they slow `COPY`); confirm with `pg_stat_user_indexes` after a demo session.
- BRIN on `daily_sales.sales_date` is only kept if the date-range plan uses it; otherwise drop it (record the decision).
