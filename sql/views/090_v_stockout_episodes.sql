-- File: sql/views/090_v_stockout_episodes.sql
-- Purpose: Consecutive censored-day episodes.
-- Grain: store × product × episode.
-- Constructs: CTEs, joins and window/conditional aggregates per docs/04.
-- Business question: How long do stockout episodes persist?
DROP VIEW IF EXISTS analytics.v_stockout_episodes CASCADE;
CREATE VIEW analytics.v_stockout_episodes AS
WITH flagged AS (
    SELECT store_id, product_id, position_date, is_censored,
           position_date - (ROW_NUMBER() OVER (
               PARTITION BY store_id, product_id, is_censored ORDER BY position_date))::int AS island_key
    FROM analytics.mv_daily_position
)
SELECT store_id, product_id,
       MIN(position_date) AS episode_start,
       MAX(position_date) AS episode_end,
       COUNT(*)::int      AS episode_days
FROM flagged
WHERE is_censored
GROUP BY store_id, product_id, island_key;
