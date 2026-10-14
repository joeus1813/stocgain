-- File: sql/quality/DQ09_promotion_overlap.sql
-- Purpose: promotion overlap
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: error
SELECT a.product_id,p.promotion_id AS first_promotion,q.promotion_id AS second_promotion FROM ops.promotion_products a JOIN ops.promotions p USING(promotion_id) JOIN ops.promotion_products b ON b.product_id=a.product_id AND b.promotion_id>a.promotion_id JOIN ops.promotions q ON q.promotion_id=b.promotion_id WHERE p.start_date<=q.end_date AND q.start_date<=p.end_date AND (p.region_id IS NULL OR q.region_id IS NULL OR p.region_id=q.region_id);
