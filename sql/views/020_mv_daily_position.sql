-- File: sql/views/020_mv_daily_position.sql
-- Purpose: Integrate observed daily sales, inventory, receipts and promotion plans.
-- Grain: store × product × date.
-- Constructs: materialized multi-source joins, CASE and unique/date indexes.
-- Business question: What stock was available and were sales censored?
DROP MATERIALIZED VIEW IF EXISTS analytics.mv_daily_position CASCADE;
CREATE MATERIALIZED VIEW analytics.mv_daily_position AS
WITH receipts_by_day AS (
    SELECT po.store_id, pol.product_id, r.received_date AS position_date,
           SUM(r.quantity_received)::int AS units_received
    FROM ops.inventory_receipts r
    JOIN ops.purchase_order_lines pol ON pol.po_line_id = r.po_line_id
    JOIN ops.purchase_orders po      ON po.purchase_order_id = pol.purchase_order_id
    GROUP BY po.store_id, pol.product_id, r.received_date
),
adjustments_by_day AS (
    SELECT store_id, product_id, adjustment_date AS position_date,
           SUM(quantity_delta)::int AS net_adjustment
    FROM ops.inventory_adjustments
    GROUP BY store_id, product_id, adjustment_date
),
promo_days AS (
    SELECT s.store_id, pp.product_id, gs.d::date AS position_date, p.promotion_id
    FROM ops.promotions p
    JOIN ops.promotion_products pp ON pp.promotion_id = p.promotion_id
    JOIN ops.stores s ON p.region_id IS NULL OR s.region_id = p.region_id
    CROSS JOIN LATERAL generate_series(p.start_date, p.end_date, interval '1 day') AS gs(d)
)
SELECT
    i.store_id,
    i.product_id,
    i.snapshot_date                                   AS position_date,
    i.opening_on_hand,
    COALESCE(rc.units_received, 0)                    AS units_received,
    ds.units_sold,
    COALESCE(ad.net_adjustment, 0)                    AS net_adjustment,
    i.closing_on_hand,
    i.opening_on_hand + COALESCE(rc.units_received, 0) AS available_units,
    CASE
        WHEN i.opening_on_hand + COALESCE(rc.units_received, 0) = 0             THEN 'out_all_day'
        WHEN ds.units_sold >= i.opening_on_hand + COALESCE(rc.units_received, 0) THEN 'sold_out'
        ELSE 'in_stock'
    END                                               AS availability_status,
    (i.opening_on_hand + COALESCE(rc.units_received, 0) = 0
       OR ds.units_sold >= i.opening_on_hand + COALESCE(rc.units_received, 0)) AS is_censored,
    ds.net_sales_amount,
    ds.cogs_amount,
    pd.promotion_id,
    (pd.promotion_id IS NOT NULL)                     AS is_promo_day
FROM ops.inventory_snapshots i
JOIN ops.daily_sales ds
  ON ds.store_id = i.store_id AND ds.product_id = i.product_id AND ds.sales_date = i.snapshot_date
LEFT JOIN receipts_by_day rc
  ON rc.store_id = i.store_id AND rc.product_id = i.product_id AND rc.position_date = i.snapshot_date
LEFT JOIN adjustments_by_day ad
  ON ad.store_id = i.store_id AND ad.product_id = i.product_id AND ad.position_date = i.snapshot_date
LEFT JOIN promo_days pd
  ON pd.store_id = i.store_id AND pd.product_id = i.product_id AND pd.position_date = i.snapshot_date;

CREATE UNIQUE INDEX ux_mv_daily_position ON analytics.mv_daily_position (store_id, product_id, position_date);
CREATE INDEX ix_mv_daily_position_date ON analytics.mv_daily_position (position_date);
