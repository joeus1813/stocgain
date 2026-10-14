-- File: sql/api/risk_trend.sql
-- Purpose: How has filtered risk changed over selected weekly dates?
-- Grain: selected date
-- Constructs: run-bound CTEs, joins and aggregates.
-- Business question: How has filtered risk changed over selected weekly dates?
WITH selected AS (
 SELECT DISTINCT ON (as_of_date) run_id,as_of_date
 FROM analytics.analytics_runs
 WHERE status='succeeded' AND as_of_date <= CAST(:as_of_date AS date)
 AND as_of_date > CAST(:as_of_date AS date) - CAST(:weeks AS integer)*7
 AND (as_of_date < CAST(:as_of_date AS date) OR run_id=:run_id)
 ORDER BY as_of_date,(run_type='current') DESC,completed_at DESC,run_id DESC
 ), filtered AS (SELECT lr.as_of_date,r.* FROM selected lr
 JOIN analytics.inventory_risk_snapshots r ON r.run_id=lr.run_id
 JOIN ops.stores s USING(store_id) JOIN ops.products p USING(product_id)
 WHERE r.run_id = lr.run_id
 AND (CAST(:store_ids AS integer[]) IS NULL OR r.store_id = ANY(CAST(:store_ids AS integer[])))
 AND (CAST(:region_ids AS integer[]) IS NULL OR s.region_id = ANY(CAST(:region_ids AS integer[])))
 AND (CAST(:category_ids AS integer[]) IS NULL OR p.category_id = ANY(CAST(:category_ids AS integer[])))
 AND (CAST(:supplier_ids AS integer[]) IS NULL OR r.supplier_id = ANY(CAST(:supplier_ids AS integer[]))))
 SELECT lr.as_of_date,lr.run_id,
 count(f.store_id) FILTER(WHERE risk_tier='critical') AS critical,
 count(f.store_id) FILTER(WHERE risk_tier='high') AS high,
 count(f.store_id) FILTER(WHERE risk_tier='moderate') AS moderate,
 count(f.store_id) FILTER(WHERE risk_tier='low') AS low,
 coalesce(sum(f.margin_at_risk_usd),0) AS margin_at_risk_usd
 FROM selected lr LEFT JOIN filtered f ON f.run_id=lr.run_id
 GROUP BY lr.as_of_date,lr.run_id ORDER BY lr.as_of_date;
