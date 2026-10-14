-- File: sql/pipeline/extract_positions.sql
-- Purpose: Active position and primary sourcing configuration at cutoff.
-- Grain: store × product.
-- Constructs: date bounds, joins and aggregation.
-- Business question: Active position and primary sourcing configuration at cutoff?
SELECT s.store_id, p.product_id, ps.supplier_id, ps.case_pack_qty, ps.min_order_qty,
       p.unit_price, p.unit_cost, p.category_id, c.category_code, s.region_id,
       l.contract_lead_time_days, l.review_weekday
FROM ops.stores s CROSS JOIN ops.products p
JOIN ops.product_categories c USING (category_id)
JOIN ops.product_suppliers ps ON ps.product_id = p.product_id AND ps.is_primary
JOIN ops.supplier_store_lanes l ON l.supplier_id = ps.supplier_id AND l.store_id = s.store_id
WHERE s.is_active AND p.is_active AND l.is_active
  AND s.opened_date <= CAST(:as_of AS date) AND p.introduced_date <= CAST(:as_of AS date);
