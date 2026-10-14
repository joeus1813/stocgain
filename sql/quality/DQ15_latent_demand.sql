-- File: sql/quality/DQ15_latent_demand.sql
-- Purpose: latent demand
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: error
SELECT s.store_id,s.product_id,s.sales_date,l.latent_units,s.units_sold FROM ops.daily_sales s FULL JOIN sim_truth.latent_demand l ON (l.store_id,l.product_id,l.demand_date)=(s.store_id,s.product_id,s.sales_date) WHERE l.latent_units<s.units_sold OR l.store_id IS NULL OR s.store_id IS NULL;
