-- File: sql/api/position_checkpoints.sql
-- Purpose: Return ordered stored checkpoint calculations.
-- Grain: one checkpoint.
-- Constructs: run-bound join and deterministic ordering.
-- Business question: Which receipt or window boundary binds this position's risk?
SELECT c.checkpoint_seq,c.checkpoint_type,c.purchase_order_id,p.po_number,c.arrival_date,
       c.window_days,c.window_std_days,c.supply_units,c.demand_mean_units,c.demand_std_units,
       c.distribution_family,c.stockout_probability,c.expected_shortage_units,c.is_binding
FROM analytics.risk_checkpoints c
LEFT JOIN ops.purchase_orders p USING(purchase_order_id)
WHERE c.run_id=:run_id AND c.store_id=:store_id AND c.product_id=:product_id
ORDER BY c.checkpoint_seq;
