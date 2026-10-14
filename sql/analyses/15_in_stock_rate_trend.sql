-- File: sql/analyses/15_in_stock_rate_trend.sql
-- Purpose: End-of-day in-stock rate by region and week; docs/04 section 5.15.
-- Grain: region × week.
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: End-of-day in-stock rate by region and week.
SELECT c.week_start_date, rg.region_name,
       ROUND(AVG((m.closing_on_hand > 0)::int), 4)                                   AS in_stock_rate,
       ROUND(AVG((m.closing_on_hand > 0)::int) FILTER (WHERE m.is_promo_day), 4)     AS in_stock_rate_promo,
       ROUND(AVG((m.closing_on_hand > 0)::int) FILTER (WHERE NOT m.is_promo_day), 4) AS in_stock_rate_non_promo
FROM analytics.mv_daily_position m
JOIN ops.calendar c ON c.calendar_date = m.position_date
JOIN ops.stores s   ON s.store_id = m.store_id
JOIN ops.regions rg ON rg.region_id = s.region_id
GROUP BY c.week_start_date, rg.region_name
ORDER BY c.week_start_date, rg.region_name;
