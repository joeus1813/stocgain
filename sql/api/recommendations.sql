-- File: sql/api/recommendations.sql
-- Purpose: Which stored recommendations need action first?
-- Grain: position
-- Constructs: run-bound CTEs, joins and aggregates.
-- Business question: Which stored recommendations need action first?
SELECT rr.priority_rank,r.store_id,s.store_code,r.product_id,p.sku,p.product_name,c.category_name,
 r.risk_tier,r.stockout_probability,r.margin_at_risk_usd,rr.action_type,rr.urgency,
 rr.recommended_order_units,rr.recommended_order_cost_usd,
 CASE WHEN po.purchase_order_id IS NULL THEN NULL ELSE jsonb_build_object('purchase_order_id',po.purchase_order_id,'po_number',po.po_number) END AS related_purchase_order,
 rr.rationale,r.days_until_projected_stockout
 FROM analytics.inventory_risk_snapshots r
 JOIN ops.stores s USING(store_id)
 JOIN ops.products p USING(product_id) JOIN ops.product_categories c USING(category_id) JOIN analytics.replenishment_recommendations rr
 ON rr.run_id=r.run_id AND rr.store_id=r.store_id AND rr.product_id=r.product_id
 LEFT JOIN ops.purchase_orders po ON po.purchase_order_id=rr.related_purchase_order_id
 WHERE r.run_id = :run_id
 AND (CAST(:store_ids AS integer[]) IS NULL OR r.store_id = ANY(CAST(:store_ids AS integer[])))
 AND (CAST(:region_ids AS integer[]) IS NULL OR s.region_id = ANY(CAST(:region_ids AS integer[])))
 AND (CAST(:category_ids AS integer[]) IS NULL OR p.category_id = ANY(CAST(:category_ids AS integer[])))
 AND (CAST(:supplier_ids AS integer[]) IS NULL OR r.supplier_id = ANY(CAST(:supplier_ids AS integer[]))) AND rr.action_type::text=ANY(CAST(:action_types AS text[]))
 ORDER BY rr.priority_rank NULLS LAST,r.store_id,r.product_id LIMIT :limit;
