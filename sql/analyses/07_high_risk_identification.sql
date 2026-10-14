-- File: sql/analyses/07_high_risk_identification.sql
-- Purpose: High-risk inventory identification; docs/04 section 5.7.
-- Grain: store × ranked high-risk position (top 5 per store).
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: High-risk inventory identification.
WITH ranked AS (
    SELECT v.*,
           ROW_NUMBER() OVER (PARTITION BY v.store_id
                              ORDER BY v.risk_tier DESC, v.margin_at_risk_usd DESC, v.product_id) AS rank_in_store
    FROM analytics.v_current_risk v
    WHERE v.risk_tier IN ('critical', 'high')
)
SELECT store_code, rank_in_store, sku, product_name, category_name, risk_tier,
       ROUND(stockout_probability * 100, 1) AS stockout_probability_pct,
       on_hand_units, ROUND(avg_daily_demand_units, 1) AS avg_daily_demand_units,
       days_of_cover, next_receipt_date, margin_at_risk_usd, action_type
FROM ranked
WHERE rank_in_store <= 5
ORDER BY store_code, rank_in_store;
