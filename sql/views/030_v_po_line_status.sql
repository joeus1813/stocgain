-- File: sql/views/030_v_po_line_status.sql
-- Purpose: Lifetime PO-line fulfillment status.
-- Grain: purchase-order line.
-- Constructs: CTEs, joins and window/conditional aggregates per docs/04.
-- Business question: What quantity remains open on each line?
DROP VIEW IF EXISTS analytics.v_po_line_status CASCADE;
CREATE VIEW analytics.v_po_line_status AS
WITH rec AS (
    SELECT po_line_id,
           SUM(quantity_received)::int AS quantity_received,
           MIN(received_date)          AS first_receipt_date,
           MAX(received_date)          AS last_receipt_date,
           COUNT(*)::int               AS receipt_count
    FROM ops.inventory_receipts
    GROUP BY po_line_id
)
SELECT pol.po_line_id, pol.purchase_order_id, po.po_number, po.supplier_id, po.store_id, pol.product_id,
       po.order_date, po.promised_delivery_date,
       pol.quantity_ordered, pol.quantity_cancelled,
       COALESCE(rec.quantity_received, 0) AS quantity_received,
       pol.quantity_ordered - pol.quantity_cancelled - COALESCE(rec.quantity_received, 0) AS open_quantity,
       rec.first_receipt_date, rec.last_receipt_date, COALESCE(rec.receipt_count, 0) AS receipt_count,
       pol.unit_cost,
       CASE
         WHEN pol.quantity_ordered - pol.quantity_cancelled - COALESCE(rec.quantity_received,0) > 0
              AND COALESCE(rec.quantity_received,0) = 0 THEN 'open'
         WHEN pol.quantity_ordered - pol.quantity_cancelled - COALESCE(rec.quantity_received,0) > 0
              THEN 'partially_received'
         WHEN pol.quantity_cancelled > 0 THEN 'closed_short'
         ELSE 'received'
       END AS line_status
FROM ops.purchase_order_lines pol
JOIN ops.purchase_orders po ON po.purchase_order_id = pol.purchase_order_id
LEFT JOIN rec ON rec.po_line_id = pol.po_line_id;
