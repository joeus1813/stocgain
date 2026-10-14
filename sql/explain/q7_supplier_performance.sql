-- File: sql/explain/q7_supplier_performance.sql
-- Purpose: Measure q7_supplier_performance on the standard preset.
-- Grain: execution plan.
-- Constructs: EXPLAIN ANALYZE BUFFERS; underlying query per docs/04.
-- Business question: What work and time does PostgreSQL require?
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM analytics.v_supplier_performance;
