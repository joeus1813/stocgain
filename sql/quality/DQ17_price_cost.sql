-- File: sql/quality/DQ17_price_cost.sql
-- Purpose: price cost
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: error
SELECT * FROM ops.products WHERE unit_price<=unit_cost;
