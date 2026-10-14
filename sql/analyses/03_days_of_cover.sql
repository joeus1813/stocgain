-- File: sql/analyses/03_days_of_cover.sql
-- Purpose: Inventory days of cover; docs/04 section 5.3.
-- Grain: category × coverage bucket, plus chain buckets.
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: Inventory days of cover.
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
