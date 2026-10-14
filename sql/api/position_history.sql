-- File: sql/api/position_history.sql
-- Purpose: Return observed history ending at the model cutoff.
-- Grain: one store-product-day.
-- Constructs: cutoff-bounded materialized view and promotion join.
-- Business question: What observed inventory and sales underpin the forecast?
SELECT d.position_date AS date,d.units_sold,d.opening_on_hand AS opening_on_hand_units,
       d.units_received,d.net_adjustment AS net_adjustment_units,
       d.closing_on_hand AS closing_on_hand_units,d.availability_status,d.is_censored,
       d.promotion_id,p.promotion_name
FROM analytics.mv_daily_position d
LEFT JOIN ops.promotions p USING(promotion_id)
WHERE d.store_id=:store_id AND d.product_id=:product_id
  AND d.position_date BETWEEN CAST(:as_of_date AS date)-CAST(:days AS integer)+1 AND CAST(:as_of_date AS date)
ORDER BY d.position_date;
