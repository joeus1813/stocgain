-- File: sql/quality/DQ07_sourced_product.sql
-- Purpose: sourced product
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: error
SELECT l.* FROM ops.purchase_order_lines l JOIN ops.purchase_orders p USING(purchase_order_id) LEFT JOIN ops.product_suppliers ps ON ps.product_id=l.product_id AND ps.supplier_id=p.supplier_id WHERE ps.product_id IS NULL;
