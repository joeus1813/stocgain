-- File: sql/api/position_detail.sql
-- Purpose: Fetch persisted position calculations and descriptive dimensions.
-- Grain: one scored store-product position.
-- Constructs: run-key joins and JSON records.
-- Business question: What stored evidence explains this position's risk?
SELECT to_jsonb(r) AS risk, to_jsonb(f) AS demand, to_jsonb(l) AS supply,
       to_jsonb(a) AS recommendation,
       s.store_code,s.store_name,g.region_name,
       p.sku,p.product_name,c.category_name,p.brand_name,p.unit_of_measure,
       p.unit_price AS unit_price_usd,p.unit_cost AS unit_cost_usd,
       su.supplier_code,su.supplier_name,ps.case_pack_qty,ps.min_order_qty,
       po.po_number AS next_po_number,related.po_number AS related_po_number
FROM analytics.inventory_risk_snapshots r
JOIN analytics.demand_forecasts f USING(run_id,store_id,product_id)
JOIN analytics.supplier_lane_estimates l USING(run_id,store_id,supplier_id)
JOIN analytics.replenishment_recommendations a USING(run_id,store_id,product_id,supplier_id)
JOIN ops.stores s USING(store_id)
JOIN ops.regions g USING(region_id)
JOIN ops.products p USING(product_id)
JOIN ops.product_categories c USING(category_id)
JOIN ops.suppliers su USING(supplier_id)
JOIN ops.product_suppliers ps ON ps.product_id=r.product_id AND ps.supplier_id=r.supplier_id
LEFT JOIN ops.purchase_orders po ON po.purchase_order_id=r.next_receipt_po_id
LEFT JOIN ops.purchase_orders related ON related.purchase_order_id=a.related_purchase_order_id
WHERE r.run_id=:run_id AND r.store_id=:store_id AND r.product_id=:product_id;
