-- File: sql/quality/DQ11_cogs.sql
-- Purpose: cogs
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: error
SELECT s.* FROM ops.daily_sales s JOIN ops.products p USING(product_id) WHERE abs(s.cogs_amount-s.units_sold*p.unit_cost)>.01;
