-- File: sql/analyses/02_demand_trends.sql
-- Purpose: Demand trends over time; docs/04 section 5.2.
-- Grain: complete week × category × region.
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: Demand trends over time.
WITH weekly AS (
    SELECT c.week_start_date, pc.category_name, rg.region_name,
           COUNT(DISTINCT m.position_date)              AS days_in_week,
           SUM(m.units_sold)                            AS units,
           SUM(m.net_sales_amount)                      AS revenue,
           AVG(m.is_censored::int)::numeric(6,4)        AS censored_share
    FROM analytics.mv_daily_position m
    JOIN ops.calendar c            ON c.calendar_date = m.position_date
    JOIN ops.products p            ON p.product_id = m.product_id
    JOIN ops.product_categories pc ON pc.category_id = p.category_id
    JOIN ops.stores s              ON s.store_id = m.store_id
    JOIN ops.regions rg            ON rg.region_id = s.region_id
    GROUP BY c.week_start_date, pc.category_name, rg.region_name
)
SELECT week_start_date, category_name, region_name, units, revenue, censored_share,
       LAG(units) OVER w AS prior_week_units,
       ROUND(100.0 * (units - LAG(units) OVER w) / NULLIF(LAG(units) OVER w, 0), 1) AS wow_change_pct,
       ROUND(AVG(units) OVER (PARTITION BY category_name, region_name ORDER BY week_start_date
                              ROWS BETWEEN 3 PRECEDING AND CURRENT ROW), 1) AS units_4wk_moving_avg
FROM weekly
WHERE days_in_week = 7
WINDOW w AS (PARTITION BY category_name, region_name ORDER BY week_start_date)
ORDER BY category_name, region_name, week_start_date;
