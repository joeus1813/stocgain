-- File: sql/views/040_v_po_status.sql
-- Purpose: PO fulfillment and first-receipt performance.
-- Grain: purchase order.
-- Constructs: CTEs, joins and window/conditional aggregates per docs/04.
-- Business question: Was this PO on time and in full?
DROP VIEW IF EXISTS analytics.v_po_status CASCADE;
CREATE VIEW analytics.v_po_status AS
SELECT purchase_order_id, po_number, supplier_id, store_id, order_date, promised_delivery_date,
       COUNT(*)::int                                   AS line_count,
       SUM(quantity_ordered)::int                      AS units_ordered,
       SUM(quantity_received)::int                     AS units_received,
       SUM(quantity_cancelled)::int                    AS units_cancelled,
       SUM(open_quantity)::int                         AS units_open,
       MIN(first_receipt_date)                         AS first_receipt_date,
       MIN(first_receipt_date) - order_date            AS lead_time_days,
       MIN(first_receipt_date) - promised_delivery_date AS delay_days,
       CASE WHEN MIN(first_receipt_date) IS NULL THEN NULL
            ELSE MIN(first_receipt_date) <= promised_delivery_date END AS on_time,
       BOOL_AND(quantity_cancelled = 0 AND receipt_count = 1
                AND quantity_received = quantity_ordered)              AS in_full,
       CASE
         WHEN SUM(open_quantity) = 0 AND SUM(quantity_cancelled) > 0 THEN 'closed_short'
         WHEN SUM(open_quantity) = 0                                 THEN 'received'
         WHEN SUM(quantity_received) > 0                             THEN 'partially_received'
         ELSE 'open'
       END AS po_status
FROM analytics.v_po_line_status
GROUP BY purchase_order_id, po_number, supplier_id, store_id, order_date, promised_delivery_date;
