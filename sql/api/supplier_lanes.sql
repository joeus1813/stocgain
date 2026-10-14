-- File: sql/api/supplier_lanes.sql
-- Purpose: Contract context and exposed positions for a supplier.
-- Grain: supplier-store lane.
-- Constructs: joins, bound parameters.
-- Business question: What lead times were contracted on these lanes?
SELECT l.store_id, s.store_code, l.contract_lead_time_days
FROM ops.supplier_store_lanes l JOIN ops.stores s USING (store_id)
WHERE l.supplier_id = :supplier_id ORDER BY s.store_code;
