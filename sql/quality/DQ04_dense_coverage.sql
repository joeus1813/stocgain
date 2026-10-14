-- File: sql/quality/DQ04_dense_coverage.sql
-- Purpose: dense coverage
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: error
WITH expected AS (
 SELECT s.store_id,p.product_id,d::date AS day FROM ops.stores s CROSS JOIN ops.products p CROSS JOIN ops.dataset_manifest m CROSS JOIN LATERAL generate_series(m.history_start_date,m.history_end_date,interval '1 day') d
), problems AS (
 SELECT 'daily_sales' AS source,e.* FROM expected e LEFT JOIN ops.daily_sales s ON (s.store_id,s.product_id,s.sales_date)=(e.store_id,e.product_id,e.day) WHERE s.store_id IS NULL
 UNION ALL SELECT 'inventory_snapshots',e.* FROM expected e LEFT JOIN ops.inventory_snapshots s ON (s.store_id,s.product_id,s.snapshot_date)=(e.store_id,e.product_id,e.day) WHERE s.store_id IS NULL
 UNION ALL SELECT 'daily_sales_extra',s.store_id,s.product_id,s.sales_date FROM ops.daily_sales s CROSS JOIN ops.dataset_manifest m WHERE s.sales_date NOT BETWEEN m.history_start_date AND m.history_end_date
 UNION ALL SELECT 'inventory_snapshots_extra',s.store_id,s.product_id,s.snapshot_date FROM ops.inventory_snapshots s CROSS JOIN ops.dataset_manifest m WHERE s.snapshot_date NOT BETWEEN m.history_start_date AND m.history_end_date
) SELECT * FROM problems;
