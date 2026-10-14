-- File: sql/analyses/05_supplier_reliability.sql
-- Purpose: Supplier delivery reliability (trailing vs prior 90 days); docs/04 section 5.5.
-- Grain: supplier over recent/prior 90-day windows.
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: Supplier delivery reliability (trailing vs prior 90 days).
WITH params AS (SELECT history_end_date AS as_of FROM ops.dataset_manifest),
due AS (
    SELECT p.supplier_id,
           CASE WHEN p.promised_delivery_date BETWEEN params.as_of - 89  AND params.as_of      THEN 'recent'
                WHEN p.promised_delivery_date BETWEEN params.as_of - 179 AND params.as_of - 90 THEN 'prior' END AS period,
           (p.first_receipt_date IS NOT NULL AND p.first_receipt_date <= p.promised_delivery_date) AS on_time,
           COALESCE(p.in_full, false) AS in_full
    FROM analytics.v_po_status p CROSS JOIN params
    WHERE p.promised_delivery_date BETWEEN params.as_of - 179 AND params.as_of
)
SELECT s.supplier_code, s.supplier_name,
       COUNT(*) FILTER (WHERE period = 'recent') AS pos_recent,
       ROUND(AVG(on_time::int) FILTER (WHERE period = 'recent'), 4)            AS on_time_rate_recent,
       ROUND(AVG(on_time::int) FILTER (WHERE period = 'prior'), 4)             AS on_time_rate_prior,
       ROUND(AVG(in_full::int) FILTER (WHERE period = 'recent'), 4)            AS in_full_rate_recent,
       ROUND(AVG((on_time AND in_full)::int) FILTER (WHERE period = 'recent'), 4) AS otif_rate_recent,
       ROUND(AVG(on_time::int) FILTER (WHERE period = 'recent')
           - AVG(on_time::int) FILTER (WHERE period = 'prior'), 4)             AS on_time_rate_change,
       DENSE_RANK() OVER (ORDER BY AVG(on_time::int) FILTER (WHERE period = 'recent')) AS worst_first_rank
FROM due JOIN ops.suppliers s ON s.supplier_id = due.supplier_id
GROUP BY s.supplier_code, s.supplier_name
ORDER BY worst_first_rank;
