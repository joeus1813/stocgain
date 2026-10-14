-- File: sql/views/050_v_supplier_lane_performance.sql
-- Purpose: Current-run supplier/store delivery performance.
-- Grain: supplier × store.
-- Constructs: CTEs, joins and window/conditional aggregates per docs/04.
-- Business question: Which lanes have delayed or missing receipts?
DROP VIEW IF EXISTS analytics.v_supplier_lane_performance CASCADE;
CREATE VIEW analytics.v_supplier_lane_performance AS
WITH cr AS (SELECT as_of_date FROM analytics.v_current_run),
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
    WHERE po.order_date <= cr.as_of_date
    GROUP BY po.purchase_order_id
)
SELECT p.supplier_id, p.store_id,
       COUNT(*) FILTER (WHERE p.first_receipt_date <= cr.as_of_date)                       AS received_pos,
       ROUND(AVG(p.lead_time_days) FILTER (WHERE p.first_receipt_date <= cr.as_of_date), 2) AS mean_lead_time_days,
       ROUND(STDDEV_SAMP(p.lead_time_days) FILTER (WHERE p.first_receipt_date <= cr.as_of_date), 2) AS std_lead_time_days,
       COUNT(*) FILTER (WHERE p.promised_delivery_date BETWEEN cr.as_of_date - 89 AND cr.as_of_date) AS pos_due_90d,
       COUNT(*) FILTER (WHERE p.promised_delivery_date BETWEEN cr.as_of_date - 89 AND cr.as_of_date
                          AND p.first_receipt_date <= p.promised_delivery_date)                AS on_time_pos_90d,
       COUNT(*) FILTER (WHERE p.promised_delivery_date <= cr.as_of_date
                          AND p.first_receipt_date IS NULL)                                    AS overdue_open_pos
FROM po_as_of p
CROSS JOIN cr
GROUP BY p.supplier_id, p.store_id;
