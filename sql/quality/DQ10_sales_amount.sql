-- File: sql/quality/DQ10_sales_amount.sql
-- Purpose: sales amount
-- Grain: violating records
-- Constructs: joins, aggregates, predicates.
-- Business question: Does the dataset satisfy its inventory contract?
-- Severity: error
SELECT s.* FROM ops.daily_sales s JOIN ops.products p USING(product_id) JOIN ops.stores st USING(store_id) LEFT JOIN LATERAL (SELECT max(pr.discount_rate) AS discount FROM ops.promotion_products pp JOIN ops.promotions pr USING(promotion_id) WHERE pp.product_id=s.product_id AND s.sales_date BETWEEN pr.start_date AND pr.end_date AND (pr.region_id IS NULL OR pr.region_id=st.region_id)) promo ON true WHERE s.net_sales_amount < s.units_sold*p.unit_price*(1-coalesce(promo.discount,0))-.01 OR s.net_sales_amount > s.units_sold*p.unit_price+.01;
