-- File: sql/quality/DQ13_primary_lanes.sql
-- Purpose: primary lanes
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: error
SELECT s.store_id,ps.product_id,ps.supplier_id FROM ops.stores s CROSS JOIN ops.product_suppliers ps LEFT JOIN ops.supplier_store_lanes l ON l.store_id=s.store_id AND l.supplier_id=ps.supplier_id WHERE ps.is_primary AND l.store_id IS NULL;
