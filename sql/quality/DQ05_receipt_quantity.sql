-- File: sql/quality/DQ05_receipt_quantity.sql
-- Purpose: receipt quantity
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: error
SELECT l.po_line_id,l.quantity_ordered,l.quantity_cancelled,coalesce(sum(r.quantity_received),0) AS received FROM ops.purchase_order_lines l LEFT JOIN ops.inventory_receipts r USING(po_line_id) GROUP BY l.po_line_id HAVING coalesce(sum(r.quantity_received),0)+l.quantity_cancelled>l.quantity_ordered;
