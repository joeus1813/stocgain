-- File: sql/analyses/12_replenishment_prioritization.sql
-- Purpose: Replenishment prioritization; docs/04 section 5.12.
-- Grain: ranked actionable position (top 100).
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: Replenishment prioritization.
WITH actions AS (
    SELECT v.*,
           ROW_NUMBER() OVER (PARTITION BY v.store_id ORDER BY v.priority_rank) AS store_rank,
           SUM(COALESCE(v.recommended_order_cost_usd, 0)) OVER (ORDER BY v.priority_rank
                                                               ROWS UNBOUNDED PRECEDING) AS cumulative_order_cost_usd
    FROM analytics.v_current_risk v
    WHERE v.action_type <> 'no_action'
)
SELECT priority_rank, store_code, store_rank, sku, product_name, risk_tier, action_type, urgency,
       ROUND(stockout_probability, 4) AS stockout_probability,
       margin_at_risk_usd, recommended_order_units, recommended_order_cost_usd, cumulative_order_cost_usd
FROM actions
ORDER BY priority_rank
LIMIT 100;
