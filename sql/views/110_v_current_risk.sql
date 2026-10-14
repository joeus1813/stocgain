-- File: sql/views/110_v_current_risk.sql
-- Purpose: Current-run risk and recommendation read model.
-- Grain: store × product in current run.
-- Constructs: CTEs, joins and window/conditional aggregates per docs/04.
-- Business question: Which stored actions apply to each position?
DROP VIEW IF EXISTS analytics.v_current_risk CASCADE;
CREATE VIEW analytics.v_current_risk AS
SELECT r.run_id, r.store_id, st.store_code, st.store_name, st.region_id, rg.region_name,
       r.product_id, p.sku, p.product_name, p.category_id, pc.category_name,
       r.supplier_id, su.supplier_name,
       p.unit_price, p.unit_cost,
       r.on_hand_units, r.on_order_units, r.inventory_position_units,
       r.avg_daily_demand_units, r.days_of_cover,
       r.next_receipt_date, r.next_receipt_units, r.next_receipt_po_id, npo.po_number AS next_receipt_po_number,
       r.next_receipt_overdue,
       r.lead_time_mean_days, r.safety_stock_units, r.reorder_point_units, r.order_up_to_units,
       r.below_reorder_point, r.stockout_probability, r.risk_tier, r.risk_drivers,
       r.expected_shortage_units, r.revenue_at_risk_usd, r.margin_at_risk_usd,
       r.projected_stockout_date, r.days_until_projected_stockout, r.currently_out_of_stock,
       rr.action_type, rr.urgency, rr.priority_rank, rr.recommended_order_units, rr.recommended_order_cost_usd,
       rr.related_purchase_order_id
FROM analytics.inventory_risk_snapshots r
JOIN analytics.v_current_run cr ON cr.run_id = r.run_id
JOIN ops.stores st              ON st.store_id = r.store_id
JOIN ops.regions rg             ON rg.region_id = st.region_id
JOIN ops.products p             ON p.product_id = r.product_id
JOIN ops.product_categories pc  ON pc.category_id = p.category_id
JOIN ops.suppliers su           ON su.supplier_id = r.supplier_id
JOIN analytics.replenishment_recommendations rr
  ON rr.run_id = r.run_id AND rr.store_id = r.store_id AND rr.product_id = r.product_id
LEFT JOIN ops.purchase_orders npo ON npo.purchase_order_id = r.next_receipt_po_id;
