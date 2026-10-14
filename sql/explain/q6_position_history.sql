-- File: sql/explain/q6_position_history.sql
-- Purpose: Measure q6_position_history on the standard preset.
-- Grain: execution plan.
-- Constructs: EXPLAIN ANALYZE BUFFERS; underlying query per docs/04.
-- Business question: What work and time does PostgreSQL require?
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM analytics.mv_daily_position WHERE store_id=1 AND product_id=1 AND position_date BETWEEN DATE '2026-08-06' AND DATE '2026-09-30' ORDER BY position_date;
