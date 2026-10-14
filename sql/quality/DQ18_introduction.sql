-- File: sql/quality/DQ18_introduction.sql
-- Purpose: introduction
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: warning
SELECT l.po_line_id,p.order_date,pr.introduced_date FROM ops.purchase_order_lines l JOIN ops.purchase_orders p USING(purchase_order_id) JOIN ops.products pr USING(product_id) WHERE p.order_date<pr.introduced_date;
