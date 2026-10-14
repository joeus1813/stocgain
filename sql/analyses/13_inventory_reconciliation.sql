-- File: sql/analyses/13_inventory_reconciliation.sql
-- Purpose: Inventory reconciliation and shrink summary; docs/04 section 5.13.
-- Grain: store × adjustment reason, with subtotals.
-- Constructs: joins, CTEs and aggregates as specified in docs/04.
-- Business question: Inventory reconciliation and shrink summary.
SELECT COALESCE(s.store_code, 'ALL') AS store_code,
       COALESCE(a.reason_code::text, 'all_reasons') AS reason_code,
       COUNT(*)                 AS adjustment_events,
       SUM(a.quantity_delta)    AS net_units,
       SUM(a.quantity_delta * p.unit_cost) AS net_value_at_cost_usd
FROM ops.inventory_adjustments a
JOIN ops.stores s   ON s.store_id = a.store_id
JOIN ops.products p ON p.product_id = a.product_id
GROUP BY ROLLUP (s.store_code, a.reason_code)
ORDER BY s.store_code NULLS LAST, a.reason_code NULLS LAST;
-- Companion check (must return 0):
-- SELECT COUNT(*) FROM analytics.v_inventory_reconciliation WHERE discrepancy <> 0;
