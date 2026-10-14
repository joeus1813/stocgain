-- File: sql/analyses/08_margin_exposure.sql
-- Purpose: Product-level gross margin exposure (Pareto); docs/04 section 5.8.
-- Grain: product with positive model-estimated exposure.
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: Product-level gross margin exposure (Pareto).
WITH by_product AS (
    SELECT v.product_id, v.sku, v.product_name, v.category_name,
           SUM(v.margin_at_risk_usd)  AS margin_at_risk_usd,
           SUM(v.revenue_at_risk_usd) AS revenue_at_risk_usd,
           COUNT(*) FILTER (WHERE v.risk_tier IN ('critical','high')) AS at_risk_stores
    FROM analytics.v_current_risk v
    GROUP BY v.product_id, v.sku, v.product_name, v.category_name
    HAVING SUM(v.margin_at_risk_usd) > 0
)
SELECT sku, product_name, category_name, at_risk_stores, margin_at_risk_usd, revenue_at_risk_usd,
       ROUND(margin_at_risk_usd / SUM(margin_at_risk_usd) OVER (), 4) AS share_of_total,
       ROUND(SUM(margin_at_risk_usd) OVER (ORDER BY margin_at_risk_usd DESC, product_id
                                           ROWS UNBOUNDED PRECEDING)
             / SUM(margin_at_risk_usd) OVER (), 4)                    AS cumulative_share
FROM by_product
ORDER BY margin_at_risk_usd DESC;
