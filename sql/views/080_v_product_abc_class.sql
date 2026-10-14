-- File: sql/views/080_v_product_abc_class.sql
-- Purpose: Trailing 56-day revenue ABC segmentation.
-- Grain: product.
-- Constructs: CTEs, joins and window/conditional aggregates per docs/04.
-- Business question: Which products contribute the most revenue?
DROP VIEW IF EXISTS analytics.v_product_abc_class CASCADE;
CREATE VIEW analytics.v_product_abc_class AS
WITH cr AS (SELECT as_of_date FROM analytics.v_current_run),
rev AS (
    SELECT m.product_id, SUM(m.net_sales_amount) AS revenue
    FROM analytics.mv_daily_position m CROSS JOIN cr
    WHERE m.position_date BETWEEN cr.as_of_date - 55 AND cr.as_of_date
    GROUP BY m.product_id
),
ranked AS (
    SELECT product_id, revenue,
           SUM(revenue) OVER (ORDER BY revenue DESC, product_id ROWS UNBOUNDED PRECEDING) - revenue AS revenue_before,
           SUM(revenue) OVER () AS total_revenue
    FROM rev
)
SELECT product_id, revenue,
       ROUND(revenue_before / NULLIF(total_revenue, 0), 4) AS cumulative_share_before,
       CASE WHEN revenue_before / NULLIF(total_revenue, 0) < 0.80 THEN 'A'
            WHEN revenue_before / NULLIF(total_revenue, 0) < 0.95 THEN 'B'
            ELSE 'C' END AS abc_class
FROM ranked;
