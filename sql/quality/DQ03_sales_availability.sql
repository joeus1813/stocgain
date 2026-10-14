-- File: sql/quality/DQ03_sales_availability.sql
-- Purpose: sales availability
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: error
SELECT * FROM analytics.v_inventory_reconciliation WHERE units_sold > opening_on_hand + units_received;
