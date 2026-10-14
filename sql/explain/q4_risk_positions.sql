-- File: sql/explain/q4_risk_positions.sql
-- Purpose: Measure q4_risk_positions on the standard preset.
-- Grain: execution plan.
-- Constructs: EXPLAIN ANALYZE BUFFERS; underlying query per docs/04.
-- Business question: What work and time does PostgreSQL require?
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM analytics.v_current_risk WHERE risk_tier IN ('high','critical') ORDER BY margin_at_risk_usd DESC,store_id,product_id LIMIT 50;
