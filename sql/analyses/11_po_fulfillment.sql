-- File: sql/analyses/11_po_fulfillment.sql
-- Purpose: Purchase order fulfillment performance; docs/04 section 5.11.
-- Grain: supplier × promised month.
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: Purchase order fulfillment performance.
WITH params AS (SELECT history_end_date AS as_of FROM ops.dataset_manifest),
lines AS (
    SELECT l.*, date_trunc('month', l.promised_delivery_date)::date AS promised_month
    FROM analytics.v_po_line_status l, params
    WHERE l.promised_delivery_date BETWEEN params.as_of - 179 AND params.as_of
)
SELECT s.supplier_code, promised_month,
       COUNT(DISTINCT purchase_order_id)                                    AS pos,
       COUNT(*)                                                             AS lines,
       SUM(quantity_ordered)                                                AS units_ordered,
       SUM(quantity_received)                                               AS units_received,
       ROUND(SUM(quantity_received)::numeric / NULLIF(SUM(quantity_ordered), 0), 4) AS unit_fill_rate,
       COUNT(*) FILTER (WHERE receipt_count > 1)                            AS split_deliveries,
       COUNT(*) FILTER (WHERE line_status = 'closed_short')                 AS lines_closed_short,
       COUNT(*) FILTER (WHERE line_status IN ('open','partially_received')) AS lines_still_open
FROM lines JOIN ops.suppliers s ON s.supplier_id = lines.supplier_id
GROUP BY s.supplier_code, promised_month
ORDER BY s.supplier_code, promised_month;
