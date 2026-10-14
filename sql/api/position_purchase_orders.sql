-- File: sql/api/position_purchase_orders.sql
-- Purpose: Derive open and completed product lines at the model cutoff.
-- Grain: one purchase-order line for this product.
-- Constructs: cutoff-bounded receipt aggregation, cancellation observability, status CASE.
-- Business question: Which orders remain open and which have recently completed?
WITH receipts AS (
  SELECT po_line_id,SUM(quantity_received)::int AS quantity_received,MIN(received_date) AS first_receipt_date
  FROM ops.inventory_receipts WHERE received_date<=CAST(:as_of_date AS date) GROUP BY po_line_id
), lines AS (
  SELECT po.purchase_order_id,po.po_number,po.order_date,po.promised_delivery_date,
         pol.quantity_ordered,COALESCE(r.quantity_received,0) AS quantity_received,
         CASE WHEN r.first_receipt_date IS NOT NULL THEN pol.quantity_cancelled ELSE 0 END AS quantity_cancelled,
         r.first_receipt_date
  FROM ops.purchase_orders po JOIN ops.purchase_order_lines pol USING(purchase_order_id)
  LEFT JOIN receipts r USING(po_line_id)
  WHERE po.store_id=:store_id AND pol.product_id=:product_id AND po.order_date<=CAST(:as_of_date AS date)
)
SELECT *,quantity_ordered-quantity_received-quantity_cancelled AS open_quantity,
       CASE WHEN quantity_ordered-quantity_received-quantity_cancelled>0
            THEN CASE WHEN quantity_received>0 THEN 'partially_received' ELSE 'open' END
            WHEN quantity_cancelled>0 THEN 'closed_short' ELSE 'received' END AS status,
       first_receipt_date-promised_delivery_date AS delay_days
FROM lines
ORDER BY first_receipt_date DESC NULLS FIRST, purchase_order_id DESC;
