-- File: sql/pipeline/extract_planned_promotions.sql
-- Purpose: Known future promotion plans over the next 42 days.
-- Grain: store × product × target date.
-- Constructs: date bounds, joins and aggregation.
-- Business question: Known future promotion plans over the next 42 days?
SELECT s.store_id, pp.product_id, gs.d::date AS target_date, p.promotion_id, p.planned_lift, p.promotion_name, p.start_date
FROM ops.promotions p
JOIN ops.promotion_products pp USING (promotion_id)
JOIN ops.stores s ON p.region_id IS NULL OR p.region_id = s.region_id
CROSS JOIN LATERAL generate_series(GREATEST(p.start_date, CAST(:as_of AS date) + 1),
    LEAST(p.end_date, CAST(:as_of AS date) + 42), interval '1 day') AS gs(d)
WHERE p.end_date > CAST(:as_of AS date) AND p.start_date <= CAST(:as_of AS date) + 42;
