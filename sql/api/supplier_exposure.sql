-- File: sql/api/supplier_exposure.sql
-- Purpose: Current-run supplier exposure drilldown.
-- Grain: store-product.
-- Constructs: joins, ordered limited selection.
-- Business question: Which positions are most exposed?
SELECT r.store_id,r.product_id,p.sku,p.product_name,r.risk_tier,r.stockout_probability,r.margin_at_risk_usd
FROM analytics.inventory_risk_snapshots r JOIN ops.products p USING (product_id)
WHERE r.run_id=:run_id AND r.supplier_id=:supplier_id AND r.risk_tier != 'low'
ORDER BY CASE r.risk_tier WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END, r.margin_at_risk_usd DESC, r.store_id,r.product_id LIMIT 50;
