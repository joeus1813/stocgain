-- File: sql/api/risk_positions.sql
-- Purpose: Which filtered positions need attention, with stable pages and full totals?
-- Grain: one page envelope
-- Constructs: run-bound CTEs, joins and aggregates.
-- Business question: Which filtered positions need attention, with stable pages and full totals?
WITH filtered AS (
 SELECT r.store_id,s.store_code,s.store_name,g.region_name,r.product_id,p.sku,p.product_name,
 p.category_id,c.category_name,r.supplier_id,su.supplier_name,
 r.on_hand_units,r.on_order_units,r.avg_daily_demand_units,r.days_of_cover,
 r.next_receipt_date,r.next_receipt_units,po.po_number AS next_receipt_po_number,r.next_receipt_overdue,
 r.stockout_probability,r.risk_tier,r.margin_at_risk_usd,r.revenue_at_risk_usd,r.below_reorder_point,
 rr.action_type,rr.urgency,rr.priority_rank,rr.recommended_order_units
 FROM analytics.inventory_risk_snapshots r
 JOIN ops.stores s USING(store_id)
 JOIN ops.products p USING(product_id) JOIN ops.regions g USING(region_id) JOIN ops.product_categories c USING(category_id)
 JOIN ops.suppliers su ON su.supplier_id=r.supplier_id JOIN analytics.replenishment_recommendations rr
 ON rr.run_id=r.run_id AND rr.store_id=r.store_id AND rr.product_id=r.product_id
 LEFT JOIN ops.purchase_orders po ON po.purchase_order_id=r.next_receipt_po_id
 WHERE r.run_id = :run_id
 AND (CAST(:store_ids AS integer[]) IS NULL OR r.store_id = ANY(CAST(:store_ids AS integer[])))
 AND (CAST(:region_ids AS integer[]) IS NULL OR s.region_id = ANY(CAST(:region_ids AS integer[])))
 AND (CAST(:category_ids AS integer[]) IS NULL OR p.category_id = ANY(CAST(:category_ids AS integer[])))
 AND (CAST(:supplier_ids AS integer[]) IS NULL OR r.supplier_id = ANY(CAST(:supplier_ids AS integer[])))
 AND (CAST(:risk_tiers AS text[]) IS NULL OR r.risk_tier::text=ANY(CAST(:risk_tiers AS text[])))
 AND (CAST(:action_types AS text[]) IS NULL OR rr.action_type::text=ANY(CAST(:action_types AS text[])))
 AND (CAST(:below_reorder_point AS boolean) IS NULL OR r.below_reorder_point=CAST(:below_reorder_point AS boolean))
 AND (CAST(:q AS text) IS NULL OR p.sku ILIKE :q_prefix ESCAPE '\' OR p.product_name ILIKE :q_contains ESCAPE '\')
 ), page AS (SELECT * FROM filtered ORDER BY CASE WHEN :sort_by='priority' AND :sort_dir='asc' THEN priority_rank END ASC NULLS LAST, CASE WHEN :sort_by='product_name' AND :sort_dir='asc' THEN product_name END ASC NULLS LAST, CASE WHEN :sort_by='store_code' AND :sort_dir='asc' THEN store_code END ASC NULLS LAST, CASE WHEN :sort_by='category_name' AND :sort_dir='asc' THEN category_name END ASC NULLS LAST, CASE WHEN :sort_by='on_hand_units' AND :sort_dir='asc' THEN on_hand_units END ASC NULLS LAST, CASE WHEN :sort_by='avg_daily_demand_units' AND :sort_dir='asc' THEN avg_daily_demand_units END ASC NULLS LAST, CASE WHEN :sort_by='days_of_cover' AND :sort_dir='asc' THEN days_of_cover END ASC NULLS LAST, CASE WHEN :sort_by='next_receipt_date' AND :sort_dir='asc' THEN next_receipt_date END ASC NULLS LAST, CASE WHEN :sort_by='stockout_probability' AND :sort_dir='asc' THEN stockout_probability END ASC NULLS LAST, CASE WHEN :sort_by='risk_tier' AND :sort_dir='asc' THEN CASE risk_tier WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'moderate' THEN 2 ELSE 1 END END ASC NULLS LAST, CASE WHEN :sort_by='margin_at_risk_usd' AND :sort_dir='asc' THEN margin_at_risk_usd END ASC NULLS LAST, CASE WHEN :sort_by='priority' AND :sort_dir='desc' THEN priority_rank END DESC NULLS LAST, CASE WHEN :sort_by='product_name' AND :sort_dir='desc' THEN product_name END DESC NULLS LAST, CASE WHEN :sort_by='store_code' AND :sort_dir='desc' THEN store_code END DESC NULLS LAST, CASE WHEN :sort_by='category_name' AND :sort_dir='desc' THEN category_name END DESC NULLS LAST, CASE WHEN :sort_by='on_hand_units' AND :sort_dir='desc' THEN on_hand_units END DESC NULLS LAST, CASE WHEN :sort_by='avg_daily_demand_units' AND :sort_dir='desc' THEN avg_daily_demand_units END DESC NULLS LAST, CASE WHEN :sort_by='days_of_cover' AND :sort_dir='desc' THEN days_of_cover END DESC NULLS LAST, CASE WHEN :sort_by='next_receipt_date' AND :sort_dir='desc' THEN next_receipt_date END DESC NULLS LAST, CASE WHEN :sort_by='stockout_probability' AND :sort_dir='desc' THEN stockout_probability END DESC NULLS LAST, CASE WHEN :sort_by='risk_tier' AND :sort_dir='desc' THEN CASE risk_tier WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'moderate' THEN 2 ELSE 1 END END DESC NULLS LAST, CASE WHEN :sort_by='margin_at_risk_usd' AND :sort_dir='desc' THEN margin_at_risk_usd END DESC NULLS LAST, CASE WHEN :sort_by='priority' THEN CASE risk_tier WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'moderate' THEN 2 ELSE 1 END END DESC, CASE WHEN :sort_by='priority' THEN margin_at_risk_usd END DESC, store_id, product_id LIMIT :limit OFFSET :offset),
 summary AS (SELECT count(*) AS positions,
 count(*) FILTER(WHERE risk_tier='critical') AS critical,count(*) FILTER(WHERE risk_tier='high') AS high,
 count(*) FILTER(WHERE risk_tier='moderate') AS moderate,count(*) FILTER(WHERE risk_tier='low') AS low,
 coalesce(sum(margin_at_risk_usd),0) AS margin_at_risk_usd FROM filtered)
 SELECT coalesce((SELECT jsonb_agg(to_jsonb(page)) FROM page),'[]'::jsonb) AS items,
 (SELECT to_jsonb(summary) FROM summary) AS summary;
