-- File: sql/quality/DQ06_receipt_after_order.sql
-- Purpose: receipt after order
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: error
SELECT r.* FROM ops.inventory_receipts r JOIN ops.purchase_order_lines l USING(po_line_id) JOIN ops.purchase_orders p USING(purchase_order_id) WHERE r.received_date<=p.order_date;
