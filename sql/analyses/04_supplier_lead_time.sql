-- File: sql/analyses/04_supplier_lead_time.sql
-- Purpose: Lead-time performance by supplier; docs/04 section 5.4.
-- Grain: supplier.
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: Lead-time performance by supplier.
WITH params AS (SELECT history_end_date AS as_of FROM ops.dataset_manifest),
received AS (
    SELECT p.*, l.contract_lead_time_days
    FROM analytics.v_po_status p
    JOIN ops.supplier_store_lanes l ON l.supplier_id = p.supplier_id AND l.store_id = p.store_id
    CROSS JOIN params
    WHERE p.first_receipt_date IS NOT NULL AND p.first_receipt_date > params.as_of - 180
)
SELECT s.supplier_code, s.supplier_name,
       COUNT(*)                                                         AS received_pos,
       ROUND(AVG(contract_lead_time_days), 1)                           AS avg_contract_lead_time_days,
       ROUND(AVG(lead_time_days), 2)                                    AS mean_lead_time_days,
       ROUND(STDDEV_SAMP(lead_time_days), 2)                            AS std_lead_time_days,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY lead_time_days)      AS p50_lead_time_days,
       percentile_cont(0.9) WITHIN GROUP (ORDER BY lead_time_days)      AS p90_lead_time_days,
       ROUND(STDDEV_SAMP(lead_time_days) / NULLIF(AVG(lead_time_days), 0), 3) AS lead_time_cv,
       ROUND(AVG(lead_time_days - contract_lead_time_days), 2)          AS mean_days_over_contract,
       RANK() OVER (ORDER BY STDDEV_SAMP(lead_time_days) / NULLIF(AVG(lead_time_days), 0) DESC) AS variability_rank
FROM received r
JOIN ops.suppliers s ON s.supplier_id = r.supplier_id
GROUP BY s.supplier_code, s.supplier_name
ORDER BY variability_rank;
