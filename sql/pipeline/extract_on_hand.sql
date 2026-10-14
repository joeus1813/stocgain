-- File: sql/pipeline/extract_on_hand.sql
-- Purpose: Closing stock and trailing 28-day censoring at cutoff.
-- Grain: store × product.
-- Constructs: date bounds, joins and aggregation.
-- Business question: Closing stock and trailing 28-day censoring at cutoff?
WITH recent AS (
    SELECT store_id, product_id, COUNT(*) FILTER (WHERE is_censored) AS recent_censored_days
    FROM analytics.mv_daily_position
    WHERE position_date BETWEEN CAST(:as_of AS date) - 27 AND CAST(:as_of AS date)
    GROUP BY store_id, product_id
)
SELECT i.store_id, i.product_id, i.closing_on_hand, COALESCE(r.recent_censored_days,0) AS recent_censored_days
FROM ops.inventory_snapshots i LEFT JOIN recent r USING (store_id, product_id)
WHERE i.snapshot_date = CAST(:as_of AS date);
