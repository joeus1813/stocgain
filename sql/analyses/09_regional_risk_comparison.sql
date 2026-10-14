-- File: sql/analyses/09_regional_risk_comparison.sql
-- Purpose: Regional inventory risk comparison; docs/04 section 5.9.
-- Grain: region plus chain total.
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: Regional inventory risk comparison.
WITH agg AS (
    SELECT COALESCE(region_name, 'Chain total') AS region_name,
           COUNT(*)                                             AS positions,
           COUNT(*) FILTER (WHERE risk_tier = 'critical')       AS critical,
           COUNT(*) FILTER (WHERE risk_tier = 'high')           AS high,
           COUNT(*) FILTER (WHERE risk_tier = 'moderate')       AS moderate,
           COUNT(*) FILTER (WHERE risk_tier = 'low')            AS low,
           SUM(margin_at_risk_usd)                              AS margin_at_risk_usd,
           AVG(stockout_probability)                            AS mean_stockout_probability,
           GROUPING(region_name)                                AS is_total
    FROM analytics.v_current_risk
    GROUP BY ROLLUP (region_name)
)
SELECT region_name, positions, critical, high, moderate, low,
       ROUND((critical + high)::numeric / NULLIF(positions, 0), 4) AS at_risk_share,
       ROUND((critical + high)::numeric / NULLIF(positions, 0)
             - MAX(CASE WHEN is_total = 1 THEN (critical + high)::numeric / NULLIF(positions, 0) END) OVER (), 4)
                                                       AS at_risk_share_vs_chain,
       ROUND(margin_at_risk_usd, 2) AS margin_at_risk_usd,
       ROUND(mean_stockout_probability, 4) AS mean_stockout_probability
FROM agg
ORDER BY is_total, at_risk_share DESC;
