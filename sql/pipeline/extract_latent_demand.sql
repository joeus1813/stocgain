-- File: sql/pipeline/extract_latent_demand.sql
-- Purpose: Simulation-only backtest evaluation truth; never observable operational input.
-- Grain: store × product × date.
-- Constructs: date bounds, joins and aggregation.
-- Business question: Simulation-only backtest evaluation truth; never observable operational input?
-- Restricted consumer: analytics/backtest.py simulation-only evaluation.
SELECT store_id, product_id, demand_date, latent_units
FROM sim_truth.latent_demand
WHERE demand_date BETWEEN CAST(:as_of AS date) - CAST(:history_days AS integer) + 1 AND CAST(:as_of AS date)
ORDER BY store_id, product_id, demand_date;
