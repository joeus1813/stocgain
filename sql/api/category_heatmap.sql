-- File: sql/api/category_heatmap.sql
-- Purpose: What is risk for every store-category cell in scope?
-- Grain: store-category
-- Constructs: run-bound CTEs, joins and aggregates.
-- Business question: What is risk for every store-category cell in scope?
WITH stores AS (
 SELECT store_id,store_code FROM ops.stores s WHERE s.is_active AND s.opened_date<=CAST(:as_of_date AS date)
 AND (CAST(:store_ids AS integer[]) IS NULL OR s.store_id=ANY(CAST(:store_ids AS integer[])))
 AND (CAST(:region_ids AS integer[]) IS NULL OR s.region_id=ANY(CAST(:region_ids AS integer[])))
 ), categories AS (SELECT category_id,category_name FROM ops.product_categories
 WHERE CAST(:category_ids AS integer[]) IS NULL OR category_id=ANY(CAST(:category_ids AS integer[]))),
 risk AS (SELECT r.store_id,p.category_id,count(*) AS positions,
 count(*) FILTER(WHERE risk_tier IN ('critical','high')) AS at_risk_positions,
 sum(margin_at_risk_usd) AS margin_at_risk_usd FROM analytics.inventory_risk_snapshots r
 JOIN ops.stores s USING(store_id)
 JOIN ops.products p USING(product_id) WHERE r.run_id = :run_id
 AND (CAST(:store_ids AS integer[]) IS NULL OR r.store_id = ANY(CAST(:store_ids AS integer[])))
 AND (CAST(:region_ids AS integer[]) IS NULL OR s.region_id = ANY(CAST(:region_ids AS integer[])))
 AND (CAST(:category_ids AS integer[]) IS NULL OR p.category_id = ANY(CAST(:category_ids AS integer[])))
 AND (CAST(:supplier_ids AS integer[]) IS NULL OR r.supplier_id = ANY(CAST(:supplier_ids AS integer[]))) GROUP BY r.store_id,p.category_id)
 SELECT s.store_id,s.store_code,c.category_id,c.category_name,
 coalesce(r.positions,0) AS positions,coalesce(r.at_risk_positions,0) AS at_risk_positions,
 coalesce(r.at_risk_positions::numeric/nullif(r.positions,0),0) AS at_risk_rate,
 coalesce(r.margin_at_risk_usd,0) AS margin_at_risk_usd
 FROM stores s CROSS JOIN categories c LEFT JOIN risk r USING(store_id,category_id)
 ORDER BY s.store_code,c.category_id;
