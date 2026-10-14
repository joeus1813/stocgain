-- File: sql/views/070_v_category_dow_profile.sql
-- Purpose: Clean-day category weekday profile.
-- Grain: category × weekday.
-- Constructs: CTEs, joins and window/conditional aggregates per docs/04.
-- Business question: How does observed demand vary by weekday?
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
