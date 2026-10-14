-- File: sql/api/filters.sql
-- Purpose: Sorted dimensional filter choices.
-- Grain: one JSON object of dimensions.
-- Constructs: JSON aggregation and scalar subqueries.
-- Business question: Which scope IDs exist?
SELECT
(SELECT coalesce(jsonb_agg(x ORDER BY region_code),'[]'::jsonb) FROM (SELECT region_id,region_code,region_name FROM ops.regions) x) AS regions,
(SELECT coalesce(jsonb_agg(x ORDER BY store_code),'[]'::jsonb) FROM (SELECT store_id,store_code,store_name,region_id FROM ops.stores) x) AS stores,
(SELECT coalesce(jsonb_agg(x ORDER BY category_code),'[]'::jsonb) FROM (SELECT category_id,category_code,category_name FROM ops.product_categories) x) AS categories,
(SELECT coalesce(jsonb_agg(x ORDER BY supplier_code),'[]'::jsonb) FROM (SELECT supplier_id,supplier_code,supplier_name,primary_category_id AS category_id FROM ops.suppliers) x) AS suppliers;
