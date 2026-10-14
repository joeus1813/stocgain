-- File: sql/explain/q3_full_history.sql
-- Purpose: Measure q3_full_history on the standard preset.
-- Grain: execution plan.
-- Constructs: EXPLAIN ANALYZE BUFFERS; underlying query per docs/04.
-- Business question: What work and time does PostgreSQL require?
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM analytics.mv_daily_position ORDER BY store_id,product_id,position_date;
