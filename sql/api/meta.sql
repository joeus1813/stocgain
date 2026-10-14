-- File: sql/api/meta.sql
-- Purpose: Loaded dataset provenance and dimensions, no fabricated metrics.
-- Grain: singleton dataset.
-- Constructs: JSON object and counted dimensions.
-- Business question: What generated dataset is currently loaded?
SELECT m.*, jsonb_build_object('stores',(SELECT count(*) FROM ops.stores),
 'regions',(SELECT count(*) FROM ops.regions),'products',(SELECT count(*) FROM ops.products),
 'suppliers',(SELECT count(*) FROM ops.suppliers),'categories',(SELECT count(*) FROM ops.product_categories)) AS counts,
 (SELECT count(*) FROM analytics.analytics_runs WHERE status='succeeded' AND run_type='backfill') AS backfill_runs_available
FROM ops.dataset_manifest m;
