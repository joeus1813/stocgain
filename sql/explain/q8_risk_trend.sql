-- File: sql/explain/q8_risk_trend.sql
-- Purpose: Measure q8_risk_trend on the standard preset.
-- Grain: execution plan.
-- Constructs: EXPLAIN ANALYZE BUFFERS; underlying query per docs/04.
-- Business question: What work and time does PostgreSQL require?
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM analytics.v_risk_trend ORDER BY as_of_date,store_id,category_id,risk_tier;
