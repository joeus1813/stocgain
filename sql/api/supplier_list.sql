-- File: sql/api/supplier_list.sql
-- Purpose: Scope-aware supplier performance with identical current-view semantics.
-- Grain: supplier.
-- Constructs: as-of CTEs, conditional aggregates, window rank.
-- Business question: Which suppliers warrant review within the selected scope?
WITH cr AS (SELECT CAST(:run_id AS bigint) AS run_id, CAST(:as_of_date AS date) AS as_of_date),
receipt_as_of AS (
    SELECT r.po_line_id, SUM(r.quantity_received) AS quantity_received,
           MIN(r.received_date) AS first_receipt_date, COUNT(*) AS receipt_count
    FROM ops.inventory_receipts r CROSS JOIN cr
    WHERE r.received_date <= cr.as_of_date
    GROUP BY r.po_line_id
),
po_as_of AS (
    SELECT po.purchase_order_id, po.supplier_id, po.store_id,
           po.order_date, po.promised_delivery_date,
           MIN(r.first_receipt_date) AS first_receipt_date,
           MIN(r.first_receipt_date) - po.order_date AS lead_time_days,
           BOOL_AND(COALESCE(r.quantity_received, 0) = pol.quantity_ordered
                    AND COALESCE(r.receipt_count, 0) = 1
                    AND pol.quantity_cancelled = 0) AS in_full
    FROM ops.purchase_orders po
    JOIN ops.purchase_order_lines pol USING (purchase_order_id)
    LEFT JOIN receipt_as_of r USING (po_line_id)
    CROSS JOIN cr
    WHERE po.order_date <= cr.as_of_date AND (CAST(:store_ids AS int[]) IS NULL OR po.store_id = ANY(CAST(:store_ids AS int[])))
      AND (CAST(:region_ids AS int[]) IS NULL OR po.store_id IN (SELECT store_id FROM ops.stores WHERE region_id = ANY(CAST(:region_ids AS int[]))))
    GROUP BY po.purchase_order_id
),
po_stats AS (
    SELECT p.supplier_id,
           COUNT(*) FILTER (WHERE p.first_receipt_date > cr.as_of_date - 180) AS received_180d,
           SUM(p.lead_time_days) FILTER (WHERE p.first_receipt_date > cr.as_of_date - 180) AS lead_days_sum,
           COUNT(*) FILTER (WHERE p.promised_delivery_date BETWEEN cr.as_of_date - 89 AND cr.as_of_date) AS pos_due_90d,
           COUNT(*) FILTER (WHERE p.promised_delivery_date BETWEEN cr.as_of_date - 89 AND cr.as_of_date
                              AND p.first_receipt_date <= p.promised_delivery_date)                AS on_time_pos_90d,
           COUNT(*) FILTER (WHERE p.promised_delivery_date BETWEEN cr.as_of_date - 89 AND cr.as_of_date
                              AND p.in_full)                                                       AS in_full_pos_90d,
           AVG(p.lead_time_days)        FILTER (WHERE p.first_receipt_date > cr.as_of_date - 180) AS mean_lead_time_days,
           STDDEV_SAMP(p.lead_time_days) FILTER (WHERE p.first_receipt_date > cr.as_of_date - 180) AS std_lead_time_days,
           percentile_cont(0.9) WITHIN GROUP (ORDER BY p.lead_time_days)
               FILTER (WHERE p.first_receipt_date > cr.as_of_date - 180)                          AS p90_lead_time_days,
           COUNT(*) FILTER (WHERE p.first_receipt_date IS NULL AND p.promised_delivery_date <= cr.as_of_date) AS overdue_open_pos
    FROM po_as_of p CROSS JOIN cr
    GROUP BY p.supplier_id
),
exposure AS (
    SELECT r.supplier_id,
           COUNT(*) FILTER (WHERE r.risk_tier IN ('critical','high')) AS at_risk_positions,
           SUM(r.margin_at_risk_usd)                                  AS margin_at_risk_usd
    FROM analytics.inventory_risk_snapshots r JOIN cr ON r.run_id = cr.run_id
    WHERE (CAST(:store_ids AS int[]) IS NULL OR r.store_id = ANY(CAST(:store_ids AS int[])))
      AND (CAST(:region_ids AS int[]) IS NULL OR r.store_id IN (SELECT store_id FROM ops.stores WHERE region_id = ANY(CAST(:region_ids AS int[]))))
    GROUP BY r.supplier_id
)
SELECT s.supplier_id, s.supplier_code, s.supplier_name, c.category_name,
       COALESCE(ps.pos_due_90d,0) AS pos_due_90d,
       COALESCE(ps.on_time_pos_90d,0) AS on_time_pos_90d, ps.received_180d, ps.lead_days_sum,
       ROUND(ps.on_time_pos_90d::numeric / NULLIF(ps.pos_due_90d, 0), 4) AS on_time_rate,
       ROUND(ps.in_full_pos_90d::numeric / NULLIF(ps.pos_due_90d, 0), 4) AS in_full_rate,
       ROUND(ps.mean_lead_time_days::numeric, 2) AS mean_lead_time_days,
       ROUND(ps.std_lead_time_days::numeric, 2)  AS std_lead_time_days,
       ROUND(ps.p90_lead_time_days::numeric, 1)  AS p90_lead_time_days,
       ROUND(ps.std_lead_time_days::numeric / NULLIF(ps.mean_lead_time_days, 0), 4) AS lead_time_cv,
       COALESCE(ps.overdue_open_pos,0) AS overdue_open_pos,
       COALESCE(e.at_risk_positions, 0)    AS at_risk_positions,
       COALESCE(e.margin_at_risk_usd, 0)   AS margin_at_risk_usd,
       ( (ps.on_time_pos_90d::numeric / NULLIF(ps.pos_due_90d,0) < 0.80
          OR ps.std_lead_time_days / NULLIF(ps.mean_lead_time_days,0) > 0.35)
         AND COALESCE(e.at_risk_positions,0) >= 1 )               AS review_flag,
       RANK() OVER (ORDER BY ps.on_time_pos_90d::numeric / NULLIF(ps.pos_due_90d,0) ASC NULLS LAST) AS reliability_rank
FROM ops.suppliers s
CROSS JOIN cr
JOIN ops.product_categories c ON c.category_id = s.primary_category_id
LEFT JOIN po_stats ps ON ps.supplier_id = s.supplier_id
LEFT JOIN exposure e  ON e.supplier_id = s.supplier_id
WHERE (CAST(:category_ids AS int[]) IS NULL OR s.primary_category_id = ANY(CAST(:category_ids AS int[])))
  AND (CAST(:supplier_ids AS int[]) IS NULL OR s.supplier_id = ANY(CAST(:supplier_ids AS int[])));
