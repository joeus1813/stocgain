-- File: sql/quality/DQ02_continuity.sql
-- Purpose: continuity
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: error
WITH history AS (SELECT *, lag(closing_on_hand) OVER (PARTITION BY store_id, product_id ORDER BY snapshot_date) AS prior_closing FROM ops.inventory_snapshots)
SELECT * FROM history WHERE prior_closing IS NOT NULL AND opening_on_hand <> prior_closing;
