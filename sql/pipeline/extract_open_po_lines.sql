-- File: sql/pipeline/extract_open_po_lines.sql
-- Purpose: Remaining PO quantity using only receipts and cancellations known by cutoff.
-- Grain: open PO line at cutoff.
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: What remaining po quantity using only receipts and cancellations known by cutoff are observable?
-- Open PO lines as of CAST(:as_of AS date). A line is open if it was ordered on/before CAST(:as_of AS date) and
-- quantity ordered − cancelled − received-by-CAST(:as_of AS date) > 0.
-- Cancellation is recorded when the short shipment is received; treat quantity_cancelled
-- as known only if the line's first receipt happened on/before CAST(:as_of AS date).
WITH rec AS (
    SELECT po_line_id,
           SUM(quantity_received) FILTER (WHERE received_date <= CAST(:as_of AS date))::int AS received_as_of,
           MIN(received_date) AS first_receipt_date
    FROM ops.inventory_receipts
    WHERE received_date <= CAST(:as_of AS date)
    GROUP BY po_line_id
)
SELECT po.purchase_order_id, po.po_number, po.supplier_id, po.store_id, pol.product_id,
       po.order_date, po.promised_delivery_date,
       pol.quantity_ordered
         - CASE WHEN rec.first_receipt_date <= CAST(:as_of AS date) THEN pol.quantity_cancelled ELSE 0 END
         - COALESCE(rec.received_as_of, 0) AS open_quantity_as_of
FROM ops.purchase_order_lines pol
JOIN ops.purchase_orders po ON po.purchase_order_id = pol.purchase_order_id
LEFT JOIN rec ON rec.po_line_id = pol.po_line_id
WHERE po.order_date <= CAST(:as_of AS date)
  AND pol.quantity_ordered
        - CASE WHEN rec.first_receipt_date <= CAST(:as_of AS date) THEN pol.quantity_cancelled ELSE 0 END
        - COALESCE(rec.received_as_of, 0) > 0;
