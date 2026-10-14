-- File: sql/quality/DQ08_primary_supplier.sql
-- Purpose: primary supplier
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: error
SELECT p.product_id FROM ops.products p LEFT JOIN ops.product_suppliers ps USING(product_id) GROUP BY p.product_id HAVING count(*) FILTER(WHERE ps.is_primary)<>1;
