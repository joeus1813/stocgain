-- File: sql/pipeline/extract_category_dow_profile.sql
-- Purpose: Clean non-promotion weekday indices at cutoff.
-- Grain: category × weekday.
-- Constructs: date bounds, joins and aggregation.
-- Business question: Clean non-promotion weekday indices at cutoff?
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
FROM by_dow;
