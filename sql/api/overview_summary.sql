-- File: sql/api/overview_summary.sql
-- Purpose: Overview KPIs with run-scoped risk and observed operational measures.
-- Grain: one filtered summary for the selected run and as-of date.
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: What are the filtered risk, availability and delivery KPIs?
WITH f AS (
    SELECT CAST(:store_ids AS integer[])    AS store_ids,
           CAST(:region_ids AS integer[])   AS region_ids,
           CAST(:category_ids AS integer[]) AS category_ids
),
pos AS (
    SELECT r.*
    FROM analytics.inventory_risk_snapshots r
    JOIN ops.products p ON p.product_id = r.product_id
    JOIN ops.stores s   ON s.store_id = r.store_id
    CROSS JOIN f
    WHERE r.run_id = :run_id AND p.is_active
      AND (f.store_ids    IS NULL OR r.store_id    = ANY (f.store_ids))
      AND (f.region_ids   IS NULL OR s.region_id   = ANY (f.region_ids))
      AND (f.category_ids IS NULL OR p.category_id = ANY (f.category_ids))
),
prior AS (
    SELECT COUNT(*) FILTER (WHERE r.risk_tier IN ('critical','high')) AS at_risk_positions
    FROM analytics.inventory_risk_snapshots r
    JOIN ops.products p ON p.product_id = r.product_id
    JOIN ops.stores s   ON s.store_id = r.store_id
    CROSS JOIN f
    WHERE r.run_id = :prior_run_id
      AND (f.store_ids    IS NULL OR r.store_id    = ANY (f.store_ids))
      AND (f.region_ids   IS NULL OR s.region_id   = ANY (f.region_ids))
      AND (f.category_ids IS NULL OR p.category_id = ANY (f.category_ids))
),
po AS (
    SELECT COUNT(*) AS pos_due,
           COUNT(*) FILTER (WHERE v.first_receipt_date <= v.promised_delivery_date) AS pos_on_time
    FROM analytics.v_po_status v
    JOIN ops.stores s    ON s.store_id = v.store_id
    JOIN ops.suppliers su ON su.supplier_id = v.supplier_id
    CROSS JOIN f
    WHERE v.promised_delivery_date BETWEEN CAST(:as_of_date AS date) - 89 AND CAST(:as_of_date AS date)
      AND (f.store_ids    IS NULL OR v.store_id = ANY (f.store_ids))
      AND (f.region_ids   IS NULL OR s.region_id = ANY (f.region_ids))
      AND (f.category_ids IS NULL OR su.primary_category_id = ANY (f.category_ids))
),
instock AS (
    SELECT AVG((m.closing_on_hand > 0)::int) FILTER (WHERE m.position_date >  CAST(:as_of_date AS date) - 28) AS in_stock_rate,
           AVG((m.closing_on_hand > 0)::int) FILTER (WHERE m.position_date <= CAST(:as_of_date AS date) - 28) AS in_stock_rate_prior
    FROM analytics.mv_daily_position m
    JOIN ops.products p ON p.product_id = m.product_id
    JOIN ops.stores s   ON s.store_id = m.store_id
    CROSS JOIN f
    WHERE m.position_date BETWEEN CAST(:as_of_date AS date) - 55 AND CAST(:as_of_date AS date)
      AND (f.store_ids    IS NULL OR m.store_id    = ANY (f.store_ids))
      AND (f.region_ids   IS NULL OR s.region_id   = ANY (f.region_ids))
      AND (f.category_ids IS NULL OR p.category_id = ANY (f.category_ids))
)
SELECT
    (SELECT COUNT(*) FROM pos)                                                        AS active_positions,
    (SELECT COUNT(DISTINCT product_id) FROM pos)                                      AS active_skus,
    (SELECT COUNT(*) FILTER (WHERE risk_tier IN ('critical','high')) FROM pos)        AS at_risk_positions,
    (SELECT COUNT(*) FILTER (WHERE risk_tier = 'critical') FROM pos)                  AS critical_positions,
    (CASE WHEN CAST(:prior_run_id AS bigint) IS NULL THEN NULL ELSE (SELECT at_risk_positions FROM prior) END)                                             AS prior_at_risk_positions,
    (SELECT COALESCE(SUM(margin_at_risk_usd), 0) FROM pos)                            AS gross_margin_at_risk_usd,
    (SELECT COALESCE(SUM(revenue_at_risk_usd), 0) FROM pos)                           AS revenue_at_risk_usd,
    (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY days_of_cover)
       FROM pos WHERE days_of_cover IS NOT NULL)                                      AS median_days_of_cover,
    (SELECT pos_due FROM po)                                                          AS supplier_pos_due,
    (SELECT pos_on_time::numeric / NULLIF(pos_due, 0) FROM po)                        AS supplier_on_time_rate,
    (SELECT in_stock_rate FROM instock)                                               AS in_stock_rate,
    (SELECT in_stock_rate_prior FROM instock)                                         AS in_stock_rate_prior;
