-- File: sql/api/position_identity.sql
-- Purpose: Distinguish missing stores, products, and scored positions.
-- Grain: one existence record.
-- Constructs: cutoff-independent identities and run-bound snapshot existence.
-- Business question: Does the requested position exist in this run?
SELECT EXISTS(SELECT 1 FROM ops.stores WHERE store_id=:store_id) AS store_exists,
       EXISTS(SELECT 1 FROM ops.products WHERE product_id=:product_id) AS product_exists,
       EXISTS(SELECT 1 FROM analytics.inventory_risk_snapshots
              WHERE run_id=:run_id AND store_id=:store_id AND product_id=:product_id) AS position_exists;
