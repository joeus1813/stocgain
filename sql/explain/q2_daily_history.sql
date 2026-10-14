-- File: sql/explain/q2_daily_history.sql
-- Purpose: Measure q2_daily_history on the standard preset.
-- Grain: execution plan.
-- Constructs: EXPLAIN ANALYZE BUFFERS; underlying query per docs/04.
-- Business question: What work and time does PostgreSQL require?
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT m.*, c.iso_day_of_week, p.category_id
FROM analytics.mv_daily_position m
JOIN ops.calendar c ON c.calendar_date = m.position_date
JOIN ops.products p ON p.product_id = m.product_id
WHERE m.position_date BETWEEN DATE '2026-09-30' - 56 + 1 AND DATE '2026-09-30'
ORDER BY m.store_id, m.product_id, m.position_date;
