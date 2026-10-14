-- File: sql/pipeline/extract_lane_lead_times.sql
-- Purpose: As-of received lead-time statistics and all-due-PO on-time rate.
-- Grain: supplier × store.
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: What as-of received lead-time statistics and all-due-po on-time rate are observable?
WITH po_first AS (
    SELECT po.purchase_order_id, po.supplier_id, po.store_id, po.order_date, po.promised_delivery_date,
           MIN(r.received_date) AS first_receipt_date
    FROM ops.purchase_orders po
    JOIN ops.purchase_order_lines pol ON pol.purchase_order_id = po.purchase_order_id
    LEFT JOIN ops.inventory_receipts r ON r.po_line_id = pol.po_line_id AND r.received_date <= CAST(:as_of AS date)
    WHERE po.order_date <= CAST(:as_of AS date)
    GROUP BY po.purchase_order_id, po.supplier_id, po.store_id, po.order_date, po.promised_delivery_date
),
received AS (
    SELECT *, first_receipt_date - order_date AS lead_time_days,
              first_receipt_date - promised_delivery_date AS delay_days
    FROM po_first
    WHERE first_receipt_date IS NOT NULL AND first_receipt_date > CAST(:as_of AS date) - 180
)
SELECT l.supplier_id, l.store_id, l.contract_lead_time_days,
       COUNT(r.purchase_order_id)                              AS n_received,
       AVG(r.lead_time_days)::numeric(6,2)                     AS mean_lead_time_days,
       STDDEV_SAMP(r.lead_time_days)::numeric(6,2)             AS std_lead_time_days,
       AVG(r.delay_days)::numeric(6,2)                         AS mean_delay_days,
       STDDEV_SAMP(r.delay_days)::numeric(6,2)                 AS std_delay_days,
       AVG(r.delay_days) FILTER (WHERE r.delay_days > 0)::numeric(6,2) AS mean_delay_when_late_days,
       (SELECT COUNT(*) FILTER (WHERE pf.first_receipt_date <= pf.promised_delivery_date)::numeric
               / NULLIF(COUNT(*), 0)
          FROM po_first pf
         WHERE pf.supplier_id = l.supplier_id AND pf.store_id = l.store_id
           AND pf.promised_delivery_date BETWEEN CAST(:as_of AS date) - 89 AND CAST(:as_of AS date))  AS on_time_rate_90d
FROM ops.supplier_store_lanes l
LEFT JOIN received r ON r.supplier_id = l.supplier_id AND r.store_id = l.store_id
GROUP BY l.supplier_id, l.store_id, l.contract_lead_time_days;
