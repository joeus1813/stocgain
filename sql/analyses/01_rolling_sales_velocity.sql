-- File: sql/analyses/01_rolling_sales_velocity.sql
-- Purpose: Rolling sales velocity by store and SKU; docs/04 section 5.1.
-- Grain: store × SKU at history end (top 50).
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: Rolling sales velocity by store and SKU.
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
