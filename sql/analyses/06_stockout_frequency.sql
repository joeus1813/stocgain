-- File: sql/analyses/06_stockout_frequency.sql
-- Purpose: Historical stockout frequency; docs/04 section 5.6.
-- Grain: store × SKU (top 50).
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: Historical stockout frequency.
WITH freq AS (
    SELECT m.store_id, m.product_id,
           COUNT(*)                                         AS days_observed,
           COUNT(*) FILTER (WHERE m.availability_status = 'out_all_day') AS out_all_day_days,
           COUNT(*) FILTER (WHERE m.availability_status = 'sold_out')    AS sold_out_days,
           MAX(m.position_date) FILTER (WHERE m.is_censored)             AS last_stockout_date
    FROM analytics.mv_daily_position m
    GROUP BY m.store_id, m.product_id
),
episodes AS (
    SELECT store_id, product_id, COUNT(*) AS episodes, MAX(episode_days) AS longest_episode_days
    FROM analytics.v_stockout_episodes GROUP BY store_id, product_id
)
SELECT s.store_code, p.sku, p.product_name,
       f.out_all_day_days, f.sold_out_days,
       ROUND((f.out_all_day_days + f.sold_out_days)::numeric / f.days_observed, 4) AS stockout_day_rate,
       COALESCE(e.episodes, 0)              AS stockout_episodes,
       COALESCE(e.longest_episode_days, 0)  AS longest_episode_days,
       f.last_stockout_date
FROM freq f
LEFT JOIN episodes e ON e.store_id = f.store_id AND e.product_id = f.product_id
JOIN ops.stores s   ON s.store_id = f.store_id
JOIN ops.products p ON p.product_id = f.product_id
ORDER BY stockout_day_rate DESC, longest_episode_days DESC
LIMIT 50;
