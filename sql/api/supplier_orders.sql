-- File: sql/api/supplier_orders.sql
-- Purpose: Historical-safe supplier delivery evidence.
-- Grain: purchase order.
-- Constructs: receipt aggregation and multi-table joins.
-- Business question: What deliveries underlie this supplier performance?
WITH cr AS (SELECT CAST(:run_id AS bigint) AS run_id, CAST(:as_of_date AS date) AS as_of_date),
receipt_as_of AS (
    SELECT r.po_line_id, SUM(r.quantity_received) AS quantity_received,
           MIN(r.received_date) AS first_receipt_date, COUNT(*) AS receipt_count
    FROM ops.inventory_receipts r CROSS JOIN cr
    WHERE r.received_date <= cr.as_of_date
    GROUP BY r.po_line_id
),
po_as_of AS (
    SELECT po.purchase_order_id, po.supplier_id, po.store_id,
           po.order_date, po.promised_delivery_date,
           MIN(r.first_receipt_date) AS first_receipt_date,
           MIN(r.first_receipt_date) - po.order_date AS lead_time_days,
           BOOL_AND(COALESCE(r.quantity_received, 0) = pol.quantity_ordered
                    AND COALESCE(r.receipt_count, 0) = 1
                    AND pol.quantity_cancelled = 0) AS in_full
    FROM ops.purchase_orders po
    JOIN ops.purchase_order_lines pol USING (purchase_order_id)
    LEFT JOIN receipt_as_of r USING (po_line_id)
    CROSS JOIN cr
    WHERE po.order_date <= cr.as_of_date AND (CAST(:store_ids AS int[]) IS NULL OR po.store_id = ANY(CAST(:store_ids AS int[])))
      AND (CAST(:region_ids AS int[]) IS NULL OR po.store_id IN (SELECT store_id FROM ops.stores WHERE region_id = ANY(CAST(:region_ids AS int[]))))
    GROUP BY po.purchase_order_id
)
SELECT p.*, s.store_code FROM po_as_of p JOIN ops.stores s USING (store_id) WHERE p.supplier_id = :supplier_id ORDER BY p.purchase_order_id;
