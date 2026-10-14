-- File: sql/pipeline/extract_store_scale.sql
-- Purpose: Store clean-day units relative to chain category mean.
-- Grain: store × category.
-- Constructs: date bounds, joins and aggregation.
-- Business question: Store clean-day units relative to chain category mean?
WITH clean AS (
    SELECT m.store_id, m.product_id, p.category_id, m.units_sold
    FROM analytics.mv_daily_position m JOIN ops.products p USING (product_id)
    WHERE m.position_date BETWEEN CAST(:as_of AS date) - 55 AND CAST(:as_of AS date)
      AND m.availability_status = 'in_stock' AND NOT m.is_promo_day
),
chain AS (SELECT category_id, AVG(units_sold) AS mean_units FROM clean GROUP BY category_id),
local AS (SELECT store_id, category_id, AVG(units_sold) AS mean_units FROM clean GROUP BY store_id, category_id)
SELECT l.store_id, l.category_id, l.mean_units / NULLIF(c.mean_units, 0) AS store_scale
FROM local l JOIN chain c USING (category_id);
