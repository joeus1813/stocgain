-- File: sql/api/top_products.sql
-- Purpose: Which products have the most estimated margin at risk?
-- Grain: product
-- Constructs: run-bound CTEs, joins and aggregates.
-- Business question: Which products have the most estimated margin at risk?
SELECT p.product_id,p.sku,p.product_name,c.category_name,
 count(*) FILTER(WHERE risk_tier IN ('critical','high')) AS at_risk_stores,
 count(*) FILTER(WHERE risk_tier='critical') AS critical_stores,
 sum(margin_at_risk_usd) AS margin_at_risk_usd
 FROM analytics.inventory_risk_snapshots r
 JOIN ops.stores s USING(store_id)
 JOIN ops.products p USING(product_id) JOIN ops.product_categories c USING(category_id) WHERE r.run_id = :run_id
 AND (CAST(:store_ids AS integer[]) IS NULL OR r.store_id = ANY(CAST(:store_ids AS integer[])))
 AND (CAST(:region_ids AS integer[]) IS NULL OR s.region_id = ANY(CAST(:region_ids AS integer[])))
 AND (CAST(:category_ids AS integer[]) IS NULL OR p.category_id = ANY(CAST(:category_ids AS integer[])))
 AND (CAST(:supplier_ids AS integer[]) IS NULL OR r.supplier_id = ANY(CAST(:supplier_ids AS integer[])))
 GROUP BY p.product_id,p.sku,p.product_name,c.category_name
 HAVING count(*) FILTER(WHERE risk_tier IN ('critical','high'))>0
 ORDER BY margin_at_risk_usd DESC,at_risk_stores DESC,p.product_id LIMIT :limit;
