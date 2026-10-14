-- File: sql/quality/DQ12_history_end.sql
-- Purpose: history end
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: error
SELECT 'sales' AS source, sales_date AS day FROM ops.daily_sales CROSS JOIN ops.dataset_manifest WHERE sales_date>history_end_date
UNION ALL SELECT 'snapshot',snapshot_date FROM ops.inventory_snapshots CROSS JOIN ops.dataset_manifest WHERE snapshot_date>history_end_date
UNION ALL SELECT 'receipt',received_date FROM ops.inventory_receipts CROSS JOIN ops.dataset_manifest WHERE received_date>history_end_date
UNION ALL SELECT 'adjustment',adjustment_date FROM ops.inventory_adjustments CROSS JOIN ops.dataset_manifest WHERE adjustment_date>history_end_date;
