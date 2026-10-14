-- File: sql/pipeline/extract_daily_history.sql
-- Purpose: Observed history bounded by as-of.
-- Grain: store × product × date.
-- Constructs: date bounds, joins and aggregation.
-- Business question: Observed history bounded by as-of?
SELECT m.*, c.iso_day_of_week, p.category_id
FROM analytics.mv_daily_position m
JOIN ops.calendar c ON c.calendar_date = m.position_date
JOIN ops.products p ON p.product_id = m.product_id
WHERE m.position_date BETWEEN CAST(:as_of AS date) - CAST(:history_days AS integer) + 1 AND CAST(:as_of AS date)
ORDER BY m.store_id, m.product_id, m.position_date;
