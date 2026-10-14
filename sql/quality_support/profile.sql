-- File: sql/quality_support/profile.sql
-- Purpose: Measure generator calibration using observable operational data.
-- Grain: one dataset.
-- Constructs: CTEs, aggregates, receipt joins and percentile.
-- Business question: Is the simulated retail dataset plausible?
WITH first_receipt AS (
 SELECT p.purchase_order_id,p.supplier_id,p.order_date,p.promised_delivery_date,
 min(r.received_date) AS first_received
 FROM ops.purchase_orders p JOIN ops.purchase_order_lines l USING(purchase_order_id)
 JOIN ops.inventory_receipts r USING(po_line_id)
 GROUP BY p.purchase_order_id
), supplier_rates AS (
 SELECT supplier_id,avg((first_received<=promised_delivery_date)::int) AS on_time
 FROM first_receipt CROSS JOIN ops.dataset_manifest m
 WHERE first_received BETWEEN m.history_end_date-89 AND m.history_end_date GROUP BY supplier_id
), line_fills AS (
 SELECT l.po_line_id,l.quantity_cancelled,count(r.receipt_id) AS shipments
 FROM ops.purchase_order_lines l LEFT JOIN ops.inventory_receipts r USING(po_line_id) GROUP BY l.po_line_id
)
SELECT (SELECT avg((opening_on_hand+units_received=0)::int) FROM analytics.v_inventory_reconciliation) AS out_all_day_share,
 (SELECT avg((opening_on_hand+units_received>0 AND units_sold=opening_on_hand+units_received)::int) FROM analytics.v_inventory_reconciliation) AS sold_out_share,
 (SELECT avg((closing_on_hand>0)::int) FROM ops.inventory_snapshots) AS end_of_day_in_stock_rate,
 (SELECT percentile_cont(.5) WITHIN GROUP (ORDER BY on_time) FROM supplier_rates) AS median_supplier_on_time_rate,
 (SELECT sr.on_time FROM supplier_rates sr JOIN ops.suppliers s USING(supplier_id) WHERE s.supplier_name='Gulfmark Plumbing Supply Co.') AS demo_pl_on_time_rate,
 (SELECT avg(first_received-order_date) FROM first_receipt) AS mean_po_lead_time_days,
 (SELECT avg((shipments>1 OR quantity_cancelled>0)::int) FROM line_fills) AS split_or_short_line_share,
 (SELECT sum(net_sales_amount-cogs_amount)/nullif(sum(net_sales_amount),0) FROM ops.daily_sales) AS gross_margin_rate,
 (SELECT avg((units_sold=0)::int) FROM ops.daily_sales) AS zero_sales_share;
