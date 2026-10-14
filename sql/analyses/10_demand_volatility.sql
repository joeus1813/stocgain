-- File: sql/analyses/10_demand_volatility.sql
-- Purpose: Demand volatility analysis; docs/04 section 5.10.
-- Grain: store × product with clean history.
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: Demand volatility analysis.
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
       ROUND(trend_units_per_day::numeric, 4) AS trend_units_per_day,
       CASE WHEN nonzero_days = 0                 THEN 'no_demand'
            WHEN adi <= 1.32 AND COALESCE(cv_squared,0) < 0.49 THEN 'smooth'
            WHEN adi <= 1.32                      THEN 'erratic'
            WHEN COALESCE(cv_squared,0) < 0.49    THEN 'intermittent'
            ELSE 'lumpy' END AS demand_pattern
FROM classified c
JOIN ops.stores s   ON s.store_id = c.store_id
JOIN ops.products p ON p.product_id = c.product_id
ORDER BY cv DESC NULLS LAST;
