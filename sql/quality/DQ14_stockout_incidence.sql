-- File: sql/quality/DQ14_stockout_incidence.sql
-- Purpose: stockout incidence
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: warning
SELECT avg((opening_on_hand+units_received=0)::int) AS out_all_day_share FROM analytics.v_inventory_reconciliation HAVING avg((opening_on_hand+units_received=0)::int) NOT BETWEEN .01 AND .12;
