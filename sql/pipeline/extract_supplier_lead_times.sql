-- File: sql/pipeline/extract_supplier_lead_times.sql
-- Purpose: Pooled supplier observations with unreceived due POs counted late.
-- Grain: supplier.
-- Constructs: date bounds, joins and aggregation.
-- Business question: Pooled supplier observations with unreceived due POs counted late?
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
SELECT s.supplier_id,
       COUNT(r.purchase_order_id) AS n_received,
       AVG(r.lead_time_days)::numeric(6,2) AS mean_lead_time_days,
       STDDEV_SAMP(r.lead_time_days)::numeric(6,2) AS std_lead_time_days,
       AVG(r.delay_days)::numeric(6,2) AS mean_delay_days,
       STDDEV_SAMP(r.delay_days)::numeric(6,2) AS std_delay_days,
       AVG(r.delay_days) FILTER (WHERE r.delay_days > 0)::numeric(6,2) AS mean_delay_when_late_days,
       (SELECT COUNT(*) FILTER (WHERE pf.first_receipt_date <= pf.promised_delivery_date)::numeric / NULLIF(COUNT(*),0)
        FROM po_first pf WHERE pf.supplier_id = s.supplier_id
          AND pf.promised_delivery_date BETWEEN CAST(:as_of AS date) - 89 AND CAST(:as_of AS date)) AS on_time_rate_90d
FROM ops.suppliers s LEFT JOIN received r USING (supplier_id)
GROUP BY s.supplier_id;
