-- File: sql/views/100_v_inventory_reconciliation.sql
-- Purpose: Reconcile inventory independently of materialized analytics.
-- Grain: store-product-day
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
DROP VIEW IF EXISTS analytics.v_inventory_reconciliation CASCADE;
CREATE VIEW analytics.v_inventory_reconciliation AS
WITH rec AS (
    SELECT po.store_id, pol.product_id, r.received_date AS d, SUM(r.quantity_received)::int AS units_received
    FROM ops.inventory_receipts r
    JOIN ops.purchase_order_lines pol ON pol.po_line_id = r.po_line_id
    JOIN ops.purchase_orders po ON po.purchase_order_id = pol.purchase_order_id
    GROUP BY 1, 2, 3
),
adj AS (
    SELECT store_id, product_id, adjustment_date AS d, SUM(quantity_delta)::int AS net_adjustment
    FROM ops.inventory_adjustments GROUP BY 1, 2, 3
)
SELECT i.store_id, i.product_id, i.snapshot_date,
       i.opening_on_hand, COALESCE(rec.units_received, 0) AS units_received,
       s.units_sold, COALESCE(adj.net_adjustment, 0) AS net_adjustment, i.closing_on_hand,
       i.opening_on_hand + COALESCE(rec.units_received, 0) - s.units_sold + COALESCE(adj.net_adjustment, 0)
           AS expected_closing,
       i.closing_on_hand
         - (i.opening_on_hand + COALESCE(rec.units_received, 0) - s.units_sold + COALESCE(adj.net_adjustment, 0))
           AS discrepancy
FROM ops.inventory_snapshots i
JOIN ops.daily_sales s ON s.store_id = i.store_id AND s.product_id = i.product_id AND s.sales_date = i.snapshot_date
LEFT JOIN rec ON rec.store_id = i.store_id AND rec.product_id = i.product_id AND rec.d = i.snapshot_date
LEFT JOIN adj ON adj.store_id = i.store_id AND adj.product_id = i.product_id AND adj.d = i.snapshot_date;
