-- File: sql/analyses/14_abc_xyz_matrix.sql
-- Purpose: ABC × XYZ segmentation; docs/04 section 5.14.
-- Grain: ABC class × XYZ product counts.
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: ABC × XYZ segmentation.
WITH params AS (SELECT history_end_date AS as_of FROM ops.dataset_manifest),
chain_daily AS (
    SELECT m.product_id, m.position_date, SUM(m.units_sold) AS units
    FROM analytics.mv_daily_position m, params
    WHERE m.position_date BETWEEN params.as_of - 55 AND params.as_of
    GROUP BY m.product_id, m.position_date
),
xyz AS (
    SELECT product_id,
           CASE WHEN STDDEV_SAMP(units) / NULLIF(AVG(units), 0) < 0.5 THEN 'X'
                WHEN STDDEV_SAMP(units) / NULLIF(AVG(units), 0) <= 1.0 THEN 'Y'
                ELSE 'Z' END AS xyz_class
    FROM chain_daily GROUP BY product_id
)
SELECT a.abc_class,
       COUNT(*) FILTER (WHERE x.xyz_class = 'X') AS x_products,
       COUNT(*) FILTER (WHERE x.xyz_class = 'Y') AS y_products,
       COUNT(*) FILTER (WHERE x.xyz_class = 'Z') AS z_products,
       ROUND(SUM(a.revenue), 2)                  AS revenue_56d
FROM analytics.v_product_abc_class a
JOIN xyz x ON x.product_id = a.product_id
GROUP BY a.abc_class
ORDER BY a.abc_class;
