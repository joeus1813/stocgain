-- File: sql/api/risk_distribution.sql
-- Purpose: How is filtered risk distributed across all four tiers?
-- Grain: risk tier
-- Constructs: run-bound CTEs, joins and aggregates.
-- Business question: How is filtered risk distributed across all four tiers?
WITH tiers(risk_tier,ordinal) AS (VALUES ('critical',1),('high',2),('moderate',3),('low',4)),
 filtered AS (SELECT r.* FROM analytics.inventory_risk_snapshots r
 JOIN ops.stores s USING(store_id)
 JOIN ops.products p USING(product_id) WHERE r.run_id = :run_id
 AND (CAST(:store_ids AS integer[]) IS NULL OR r.store_id = ANY(CAST(:store_ids AS integer[])))
 AND (CAST(:region_ids AS integer[]) IS NULL OR s.region_id = ANY(CAST(:region_ids AS integer[])))
 AND (CAST(:category_ids AS integer[]) IS NULL OR p.category_id = ANY(CAST(:category_ids AS integer[])))
 AND (CAST(:supplier_ids AS integer[]) IS NULL OR r.supplier_id = ANY(CAST(:supplier_ids AS integer[]))))
 SELECT t.risk_tier, count(f.store_id) AS positions,
 coalesce(count(f.store_id)::numeric / nullif((SELECT count(*) FROM filtered),0),0) AS share_of_positions,
 coalesce(sum(f.margin_at_risk_usd),0) AS margin_at_risk_usd
 FROM tiers t LEFT JOIN filtered f ON f.risk_tier::text=t.risk_tier
 GROUP BY t.risk_tier,t.ordinal ORDER BY t.ordinal;
