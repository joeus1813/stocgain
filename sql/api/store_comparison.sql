-- File: sql/api/store_comparison.sql
-- Purpose: Which stores have the greatest estimated margin at risk?
-- Grain: store
-- Constructs: run-bound CTEs, joins and aggregates.
-- Business question: Which stores have the greatest estimated margin at risk?
WITH risk AS (
 SELECT r.store_id,count(*) AS positions,
 count(*) FILTER(WHERE risk_tier IN ('critical','high')) AS at_risk_positions,
 count(*) FILTER(WHERE risk_tier='critical') AS critical_positions,
 sum(margin_at_risk_usd) AS margin_at_risk_usd
 FROM analytics.inventory_risk_snapshots r
 JOIN ops.stores s USING(store_id)
 JOIN ops.products p USING(product_id) WHERE r.run_id = :run_id

 AND (CAST(:region_ids AS integer[]) IS NULL OR s.region_id = ANY(CAST(:region_ids AS integer[])))
 AND (CAST(:category_ids AS integer[]) IS NULL OR p.category_id = ANY(CAST(:category_ids AS integer[])))
 AND (CAST(:supplier_ids AS integer[]) IS NULL OR r.supplier_id = ANY(CAST(:supplier_ids AS integer[])))
 GROUP BY r.store_id), instock AS (
 SELECT m.store_id,avg((m.closing_on_hand>0)::int) AS in_stock_rate
 FROM analytics.mv_daily_position m JOIN ops.products p USING(product_id)
 WHERE m.position_date BETWEEN CAST(:as_of_date AS date)-27 AND CAST(:as_of_date AS date)
 AND (CAST(:category_ids AS integer[]) IS NULL OR p.category_id=ANY(CAST(:category_ids AS integer[])))
 GROUP BY m.store_id)
 SELECT s.store_id,s.store_code,s.store_name,g.region_name,r.positions,r.at_risk_positions,
 r.critical_positions,r.margin_at_risk_usd,i.in_stock_rate
 FROM risk r JOIN ops.stores s USING(store_id) JOIN ops.regions g USING(region_id)
 LEFT JOIN instock i USING(store_id) ORDER BY r.margin_at_risk_usd DESC,s.store_id;
