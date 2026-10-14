-- File: sql/api/position_forecast.sql
-- Purpose: Return next 28 stored demand forecast days.
-- Grain: one forecast day.
-- Constructs: current-run key and ordered horizon filter.
-- Business question: What daily demand does the selected analytics run predict?
SELECT target_date AS date,horizon_day,forecast_units,promo_multiplier
FROM analytics.demand_forecast_daily
WHERE run_id=:run_id AND store_id=:store_id AND product_id=:product_id AND horizon_day<=28
ORDER BY horizon_day;
