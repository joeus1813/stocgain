-- File: sql/quality_support/supplier_advisories.sql
-- Purpose: Compare Phase 1 calibration's received-date sample with all-due-PO reliability.
-- Grain: supplier.
-- Constructs: conditional aggregation, left joins, bounded dates.
-- Business question: Do the two calibration advisories indicate invalid analytical inputs?
WITH params AS (SELECT history_end_date AS as_of FROM ops.dataset_manifest)
SELECT s.supplier_code,s.supplier_name,
 count(*) FILTER(WHERE p.first_receipt_date BETWEEN params.as_of-89 AND params.as_of) AS received_sample,
 avg((p.first_receipt_date<=p.promised_delivery_date)::int)
     FILTER(WHERE p.first_receipt_date BETWEEN params.as_of-89 AND params.as_of) AS received_sample_rate,
 count(*) FILTER(WHERE p.promised_delivery_date BETWEEN params.as_of-89 AND params.as_of) AS due_pos,
 count(*) FILTER(WHERE p.promised_delivery_date BETWEEN params.as_of-89 AND params.as_of
   AND p.first_receipt_date<=p.promised_delivery_date) AS on_time_pos,
 count(*) FILTER(WHERE p.promised_delivery_date BETWEEN params.as_of-89 AND params.as_of
   AND p.first_receipt_date IS NULL) AS unreceived_due,
 count(*) FILTER(WHERE p.promised_delivery_date BETWEEN params.as_of-89 AND params.as_of
   AND p.first_receipt_date<=p.promised_delivery_date)::numeric /
 nullif(count(*) FILTER(WHERE p.promised_delivery_date BETWEEN params.as_of-89 AND params.as_of),0) AS all_due_rate
FROM ops.suppliers s JOIN analytics.v_po_status p USING(supplier_id) CROSS JOIN params
GROUP BY s.supplier_id ORDER BY s.supplier_id;
