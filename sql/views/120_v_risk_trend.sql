-- File: sql/views/120_v_risk_trend.sql
-- Purpose: Risk aggregation using the selected run for each date.
-- Grain: as-of × store × category × tier.
-- Constructs: CTEs, joins and window/conditional aggregates per docs/04.
-- Business question: How do stored risk counts change by date?
DROP VIEW IF EXISTS analytics.v_risk_trend CASCADE;
CREATE VIEW analytics.v_risk_trend AS
WITH latest_runs AS (
    SELECT DISTINCT ON (as_of_date) run_id, as_of_date, run_type
    FROM analytics.analytics_runs
    WHERE status = 'succeeded'
    ORDER BY as_of_date, (run_type = 'current') DESC, completed_at DESC
)
SELECT lr.as_of_date, lr.run_id, r.store_id, st.region_id, p.category_id, r.risk_tier,
       COUNT(*)::int                 AS positions,
       SUM(r.margin_at_risk_usd)     AS margin_at_risk_usd,
       SUM(r.revenue_at_risk_usd)    AS revenue_at_risk_usd
FROM latest_runs lr
JOIN analytics.inventory_risk_snapshots r ON r.run_id = lr.run_id
JOIN ops.products p ON p.product_id = r.product_id
JOIN ops.stores st  ON st.store_id = r.store_id
GROUP BY lr.as_of_date, lr.run_id, r.store_id, st.region_id, p.category_id, r.risk_tier;
