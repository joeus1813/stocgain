-- File: sql/pipeline/extract_product_chain_rate.sql
-- Purpose: Deseasonalized chain fallback inputs per docs/05 section 3.6.
-- Grain: product, with trailing-56-day and full-history clean observations.
-- Constructs: bounded CTEs, weekday joins, filtered averages and counts.
-- Business question: What observable clean-day baseline is available for sparse positions?
WITH dow AS (
WITH cr AS (SELECT CAST(:as_of AS date) AS as_of_date),
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
FROM by_dow
), effective_dow AS (
    SELECT category_id, iso_day_of_week,
           CASE WHEN COUNT(*) OVER (PARTITION BY category_id) < 7
                  OR MIN(n_obs) OVER (PARTITION BY category_id) < 30
                THEN 1 ELSE dow_index END AS dow_index
    FROM dow
), clean AS (
    SELECT m.product_id, m.position_date,
           m.units_sold / COALESCE(NULLIF(d.dow_index, 0), 1) AS z
    FROM analytics.mv_daily_position m
    JOIN ops.products p USING (product_id)
    JOIN ops.calendar c ON c.calendar_date = m.position_date
    LEFT JOIN effective_dow d ON d.category_id = p.category_id AND d.iso_day_of_week = c.iso_day_of_week
    WHERE m.position_date <= CAST(:as_of AS date)
      AND m.availability_status = 'in_stock' AND NOT m.is_promo_day
)
SELECT product_id,
       AVG(z) FILTER (WHERE position_date >= CAST(:as_of AS date) - 55) AS chain_rate,
       COUNT(*) FILTER (WHERE position_date >= CAST(:as_of AS date) - 55) AS n_clean_chain,
       AVG(z) AS chain_rate_full_history, COUNT(*) AS n_clean_chain_full_history
FROM clean GROUP BY product_id;
