-- File: sql/quality/DQ01_inventory_equation.sql
-- Purpose: inventory equation
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: error
SELECT * FROM analytics.v_inventory_reconciliation WHERE discrepancy <> 0;
