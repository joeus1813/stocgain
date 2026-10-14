--
-- PostgreSQL database dump
--

\restrict stocgainSchemaDump42

-- Dumped from database version 17.11 (Debian 17.11-1.pgdg13+2)
-- Dumped by pg_dump version 17.11 (Debian 17.11-1.pgdg13+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: analytics; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA analytics;


--
-- Name: ops; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA ops;


--
-- Name: sim_truth; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA sim_truth;


--
-- Name: action_type; Type: TYPE; Schema: analytics; Owner: -
--

CREATE TYPE analytics.action_type AS ENUM (
    'no_action',
    'monitor',
    'reorder',
    'expedite_po'
);


--
-- Name: checkpoint_type; Type: TYPE; Schema: analytics; Owner: -
--

CREATE TYPE analytics.checkpoint_type AS ENUM (
    'receipt',
    'window_end'
);


--
-- Name: demand_pattern; Type: TYPE; Schema: analytics; Owner: -
--

CREATE TYPE analytics.demand_pattern AS ENUM (
    'smooth',
    'erratic',
    'intermittent',
    'lumpy',
    'no_demand'
);


--
-- Name: distribution_family; Type: TYPE; Schema: analytics; Owner: -
--

CREATE TYPE analytics.distribution_family AS ENUM (
    'normal',
    'negative_binomial',
    'poisson',
    'degenerate'
);


--
-- Name: forecast_method; Type: TYPE; Schema: analytics; Owner: -
--

CREATE TYPE analytics.forecast_method AS ENUM (
    'store_sku',
    'blended',
    'chain_fallback',
    'insufficient_data'
);


--
-- Name: lead_time_source; Type: TYPE; Schema: analytics; Owner: -
--

CREATE TYPE analytics.lead_time_source AS ENUM (
    'lane',
    'supplier',
    'contract'
);


--
-- Name: risk_driver; Type: TYPE; Schema: analytics; Owner: -
--

CREATE TYPE analytics.risk_driver AS ENUM (
    'currently_out_of_stock',
    'coverage_gap',
    'no_inbound_supply',
    'overdue_po',
    'supplier_unreliable',
    'lead_time_variability',
    'demand_acceleration',
    'high_demand_variability',
    'recent_stockouts',
    'upcoming_promotion',
    'limited_history'
);


--
-- Name: risk_tier; Type: TYPE; Schema: analytics; Owner: -
--

CREATE TYPE analytics.risk_tier AS ENUM (
    'low',
    'moderate',
    'high',
    'critical'
);


--
-- Name: run_status; Type: TYPE; Schema: analytics; Owner: -
--

CREATE TYPE analytics.run_status AS ENUM (
    'running',
    'succeeded',
    'failed'
);


--
-- Name: run_type; Type: TYPE; Schema: analytics; Owner: -
--

CREATE TYPE analytics.run_type AS ENUM (
    'current',
    'backfill'
);


--
-- Name: adjustment_reason; Type: TYPE; Schema: ops; Owner: -
--

CREATE TYPE ops.adjustment_reason AS ENUM (
    'shrink',
    'damage',
    'cycle_count_correction',
    'vendor_return'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: analytics_runs; Type: TABLE; Schema: analytics; Owner: -
--

CREATE TABLE analytics.analytics_runs (
    run_id bigint NOT NULL,
    run_type analytics.run_type NOT NULL,
    as_of_date date NOT NULL,
    status analytics.run_status DEFAULT 'running'::analytics.run_status NOT NULL,
    model_version character varying(40) NOT NULL,
    config jsonb NOT NULL,
    dataset_checksum character(64) NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    step_timings jsonb,
    positions_scored integer,
    error_message text,
    CONSTRAINT analytics_runs_check CHECK (((status <> 'succeeded'::analytics.run_status) OR (completed_at IS NOT NULL))),
    CONSTRAINT analytics_runs_check1 CHECK (((status <> 'failed'::analytics.run_status) OR (error_message IS NOT NULL))),
    CONSTRAINT analytics_runs_positions_scored_check CHECK ((positions_scored >= 0))
);


--
-- Name: analytics_runs_run_id_seq; Type: SEQUENCE; Schema: analytics; Owner: -
--

ALTER TABLE analytics.analytics_runs ALTER COLUMN run_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME analytics.analytics_runs_run_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: demand_forecast_daily; Type: TABLE; Schema: analytics; Owner: -
--

CREATE TABLE analytics.demand_forecast_daily (
    run_id bigint NOT NULL,
    store_id smallint NOT NULL,
    product_id integer NOT NULL,
    target_date date NOT NULL,
    horizon_day smallint NOT NULL,
    forecast_units numeric(12,4) NOT NULL,
    dow_index numeric(6,4) NOT NULL,
    promo_multiplier numeric(4,2) NOT NULL,
    promotion_id integer,
    CONSTRAINT demand_forecast_daily_dow_index_check CHECK ((dow_index > (0)::numeric)),
    CONSTRAINT demand_forecast_daily_forecast_units_check CHECK ((forecast_units >= (0)::numeric)),
    CONSTRAINT demand_forecast_daily_horizon_day_check CHECK (((horizon_day >= 1) AND (horizon_day <= 42))),
    CONSTRAINT demand_forecast_daily_promo_multiplier_check CHECK ((promo_multiplier >= 1.00))
);


--
-- Name: demand_forecasts; Type: TABLE; Schema: analytics; Owner: -
--

CREATE TABLE analytics.demand_forecasts (
    run_id bigint NOT NULL,
    store_id smallint NOT NULL,
    product_id integer NOT NULL,
    method analytics.forecast_method NOT NULL,
    demand_pattern analytics.demand_pattern NOT NULL,
    lookback_days smallint NOT NULL,
    clean_days smallint NOT NULL,
    censored_days smallint NOT NULL,
    promo_days smallint NOT NULL,
    base_daily_demand numeric(12,4) NOT NULL,
    daily_demand_std numeric(12,4) NOT NULL,
    observed_demand_cv numeric(8,4),
    demand_trend_ratio numeric(8,4),
    adi numeric(8,3),
    cv_squared numeric(8,4),
    forecast_7d_units numeric(12,2) NOT NULL,
    forecast_14d_units numeric(12,2) NOT NULL,
    forecast_28d_units numeric(12,2) NOT NULL,
    forecast_7d_std_units numeric(12,2) NOT NULL,
    forecast_14d_std_units numeric(12,2) NOT NULL,
    forecast_28d_std_units numeric(12,2) NOT NULL,
    CONSTRAINT demand_forecasts_base_daily_demand_check CHECK ((base_daily_demand >= (0)::numeric)),
    CONSTRAINT demand_forecasts_censored_days_check CHECK ((censored_days >= 0)),
    CONSTRAINT demand_forecasts_check CHECK ((forecast_14d_units >= forecast_7d_units)),
    CONSTRAINT demand_forecasts_check1 CHECK ((forecast_28d_units >= forecast_14d_units)),
    CONSTRAINT demand_forecasts_clean_days_check CHECK ((clean_days >= 0)),
    CONSTRAINT demand_forecasts_daily_demand_std_check CHECK ((daily_demand_std >= (0)::numeric)),
    CONSTRAINT demand_forecasts_forecast_7d_units_check CHECK ((forecast_7d_units >= (0)::numeric)),
    CONSTRAINT demand_forecasts_lookback_days_check CHECK ((lookback_days > 0)),
    CONSTRAINT demand_forecasts_promo_days_check CHECK ((promo_days >= 0))
);


--
-- Name: forecast_evaluations; Type: TABLE; Schema: analytics; Owner: -
--

CREATE TABLE analytics.forecast_evaluations (
    evaluation_id bigint NOT NULL,
    run_id bigint NOT NULL,
    model_name character varying(40) NOT NULL,
    evaluation_basis character varying(20) NOT NULL,
    segment_type character varying(20) NOT NULL,
    segment_value character varying(20) NOT NULL,
    n_origins smallint NOT NULL,
    n_observations integer NOT NULL,
    actual_units numeric(14,2) NOT NULL,
    forecast_units numeric(14,2) NOT NULL,
    abs_error_units numeric(14,2) NOT NULL,
    mae numeric(12,4),
    wape numeric(8,4),
    bias_rate numeric(8,4),
    first_origin_date date NOT NULL,
    last_origin_date date NOT NULL,
    CONSTRAINT forecast_evaluations_evaluation_basis_check CHECK (((evaluation_basis)::text = ANY ((ARRAY['observed_in_stock'::character varying, 'simulated_latent'::character varying])::text[]))),
    CONSTRAINT forecast_evaluations_model_name_check CHECK (((model_name)::text = ANY ((ARRAY['stocgain_v1'::character varying, 'naive_28d_mean'::character varying, 'seasonal_naive_7d'::character varying])::text[]))),
    CONSTRAINT forecast_evaluations_n_observations_check CHECK ((n_observations >= 0)),
    CONSTRAINT forecast_evaluations_n_origins_check CHECK ((n_origins > 0)),
    CONSTRAINT forecast_evaluations_segment_type_check CHECK (((segment_type)::text = ANY ((ARRAY['overall'::character varying, 'horizon_bucket'::character varying, 'velocity_class'::character varying, 'demand_pattern'::character varying])::text[])))
);


--
-- Name: forecast_evaluations_evaluation_id_seq; Type: SEQUENCE; Schema: analytics; Owner: -
--

ALTER TABLE analytics.forecast_evaluations ALTER COLUMN evaluation_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME analytics.forecast_evaluations_evaluation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: inventory_risk_snapshots; Type: TABLE; Schema: analytics; Owner: -
--

CREATE TABLE analytics.inventory_risk_snapshots (
    run_id bigint NOT NULL,
    store_id smallint NOT NULL,
    product_id integer NOT NULL,
    supplier_id smallint NOT NULL,
    on_hand_units integer NOT NULL,
    on_order_units integer NOT NULL,
    inventory_position_units integer NOT NULL,
    open_po_count smallint NOT NULL,
    next_receipt_date date,
    next_receipt_units integer,
    next_receipt_po_id integer,
    next_receipt_overdue boolean DEFAULT false NOT NULL,
    avg_daily_demand_units numeric(12,4) NOT NULL,
    daily_demand_std_units numeric(12,4) NOT NULL,
    days_of_cover numeric(8,1),
    lead_time_mean_days numeric(6,2) NOT NULL,
    lead_time_std_days numeric(6,2) NOT NULL,
    protection_window_days numeric(6,2) NOT NULL,
    lead_time_demand_mean_units numeric(12,2) NOT NULL,
    lead_time_demand_std_units numeric(12,2) NOT NULL,
    distribution_family analytics.distribution_family NOT NULL,
    service_level numeric(5,4) NOT NULL,
    safety_stock_units numeric(12,2) NOT NULL,
    reorder_point_units integer NOT NULL,
    order_up_to_units integer NOT NULL,
    below_reorder_point boolean NOT NULL,
    binding_checkpoint_type analytics.checkpoint_type NOT NULL,
    binding_window_days numeric(6,2) NOT NULL,
    binding_supply_units integer NOT NULL,
    binding_demand_mean_units numeric(12,2) NOT NULL,
    binding_demand_std_units numeric(12,2) NOT NULL,
    stockout_probability numeric(5,4) NOT NULL,
    expected_shortage_units numeric(12,2) NOT NULL,
    lost_sale_rate numeric(4,3) NOT NULL,
    expected_lost_units numeric(12,2) NOT NULL,
    revenue_at_risk_usd numeric(12,2) NOT NULL,
    margin_at_risk_usd numeric(12,2) NOT NULL,
    projected_stockout_date date,
    days_until_projected_stockout smallint,
    currently_out_of_stock boolean NOT NULL,
    recent_censored_days smallint NOT NULL,
    risk_tier analytics.risk_tier NOT NULL,
    risk_drivers analytics.risk_driver[] DEFAULT '{}'::analytics.risk_driver[] NOT NULL,
    explanation text NOT NULL,
    CONSTRAINT inventory_risk_snapshots_check CHECK ((inventory_position_units = (on_hand_units + on_order_units))),
    CONSTRAINT inventory_risk_snapshots_check1 CHECK ((order_up_to_units >= reorder_point_units)),
    CONSTRAINT inventory_risk_snapshots_days_until_projected_stockout_check CHECK (((days_until_projected_stockout >= 1) AND (days_until_projected_stockout <= 42))),
    CONSTRAINT inventory_risk_snapshots_expected_lost_units_check CHECK ((expected_lost_units >= (0)::numeric)),
    CONSTRAINT inventory_risk_snapshots_expected_shortage_units_check CHECK ((expected_shortage_units >= (0)::numeric)),
    CONSTRAINT inventory_risk_snapshots_margin_at_risk_usd_check CHECK ((margin_at_risk_usd >= (0)::numeric)),
    CONSTRAINT inventory_risk_snapshots_next_receipt_units_check CHECK ((next_receipt_units > 0)),
    CONSTRAINT inventory_risk_snapshots_on_hand_units_check CHECK ((on_hand_units >= 0)),
    CONSTRAINT inventory_risk_snapshots_on_order_units_check CHECK ((on_order_units >= 0)),
    CONSTRAINT inventory_risk_snapshots_open_po_count_check CHECK ((open_po_count >= 0)),
    CONSTRAINT inventory_risk_snapshots_reorder_point_units_check CHECK ((reorder_point_units >= 0)),
    CONSTRAINT inventory_risk_snapshots_revenue_at_risk_usd_check CHECK ((revenue_at_risk_usd >= (0)::numeric)),
    CONSTRAINT inventory_risk_snapshots_safety_stock_units_check CHECK ((safety_stock_units >= (0)::numeric)),
    CONSTRAINT inventory_risk_snapshots_service_level_check CHECK (((service_level >= 0.5) AND (service_level <= 0.9999))),
    CONSTRAINT inventory_risk_snapshots_stockout_probability_check CHECK (((stockout_probability >= (0)::numeric) AND (stockout_probability <= (1)::numeric)))
);


--
-- Name: daily_sales; Type: TABLE; Schema: ops; Owner: -
--

CREATE TABLE ops.daily_sales (
    store_id smallint NOT NULL,
    product_id integer NOT NULL,
    sales_date date NOT NULL,
    units_sold integer NOT NULL,
    net_sales_amount numeric(12,2) NOT NULL,
    cogs_amount numeric(12,2) NOT NULL,
    CONSTRAINT daily_sales_check CHECK (((units_sold > 0) OR ((net_sales_amount = (0)::numeric) AND (cogs_amount = (0)::numeric)))),
    CONSTRAINT daily_sales_cogs_amount_check CHECK ((cogs_amount >= (0)::numeric)),
    CONSTRAINT daily_sales_net_sales_amount_check CHECK ((net_sales_amount >= (0)::numeric)),
    CONSTRAINT daily_sales_units_sold_check CHECK ((units_sold >= 0))
);


--
-- Name: inventory_adjustments; Type: TABLE; Schema: ops; Owner: -
--

CREATE TABLE ops.inventory_adjustments (
    adjustment_id integer NOT NULL,
    store_id smallint NOT NULL,
    product_id integer NOT NULL,
    adjustment_date date NOT NULL,
    quantity_delta integer NOT NULL,
    reason_code ops.adjustment_reason NOT NULL,
    CONSTRAINT inventory_adjustments_check CHECK (((reason_code = 'cycle_count_correction'::ops.adjustment_reason) OR (quantity_delta < 0))),
    CONSTRAINT inventory_adjustments_quantity_delta_check CHECK ((quantity_delta <> 0))
);


--
-- Name: inventory_receipts; Type: TABLE; Schema: ops; Owner: -
--

CREATE TABLE ops.inventory_receipts (
    receipt_id integer NOT NULL,
    po_line_id integer NOT NULL,
    received_date date NOT NULL,
    quantity_received integer NOT NULL,
    CONSTRAINT inventory_receipts_quantity_received_check CHECK ((quantity_received > 0))
);


--
-- Name: inventory_snapshots; Type: TABLE; Schema: ops; Owner: -
--

CREATE TABLE ops.inventory_snapshots (
    store_id smallint NOT NULL,
    product_id integer NOT NULL,
    snapshot_date date NOT NULL,
    opening_on_hand integer NOT NULL,
    closing_on_hand integer NOT NULL,
    CONSTRAINT inventory_snapshots_closing_on_hand_check CHECK ((closing_on_hand >= 0)),
    CONSTRAINT inventory_snapshots_opening_on_hand_check CHECK ((opening_on_hand >= 0))
);


--
-- Name: promotion_products; Type: TABLE; Schema: ops; Owner: -
--

CREATE TABLE ops.promotion_products (
    promotion_id integer NOT NULL,
    product_id integer NOT NULL
);


--
-- Name: promotions; Type: TABLE; Schema: ops; Owner: -
--

CREATE TABLE ops.promotions (
    promotion_id integer NOT NULL,
    promotion_code character varying(12) NOT NULL,
    promotion_name character varying(80) NOT NULL,
    region_id smallint,
    start_date date NOT NULL,
    end_date date NOT NULL,
    discount_rate numeric(4,3) NOT NULL,
    planned_lift numeric(4,2) NOT NULL,
    CONSTRAINT promotions_check CHECK ((end_date >= start_date)),
    CONSTRAINT promotions_check1 CHECK (((end_date - start_date) <= 30)),
    CONSTRAINT promotions_discount_rate_check CHECK (((discount_rate > (0)::numeric) AND (discount_rate < 0.6))),
    CONSTRAINT promotions_planned_lift_check CHECK (((planned_lift >= 1.00) AND (planned_lift <= 3.00))),
    CONSTRAINT promotions_promotion_code_check CHECK (((promotion_code)::text ~ '^PRM-[0-9]{4}$'::text))
);


--
-- Name: purchase_order_lines; Type: TABLE; Schema: ops; Owner: -
--

CREATE TABLE ops.purchase_order_lines (
    po_line_id integer NOT NULL,
    purchase_order_id integer NOT NULL,
    line_number smallint NOT NULL,
    product_id integer NOT NULL,
    quantity_ordered integer NOT NULL,
    quantity_cancelled integer DEFAULT 0 NOT NULL,
    unit_cost numeric(10,2) NOT NULL,
    CONSTRAINT purchase_order_lines_check CHECK (((quantity_cancelled >= 0) AND (quantity_cancelled <= quantity_ordered))),
    CONSTRAINT purchase_order_lines_line_number_check CHECK ((line_number >= 1)),
    CONSTRAINT purchase_order_lines_quantity_ordered_check CHECK ((quantity_ordered > 0)),
    CONSTRAINT purchase_order_lines_unit_cost_check CHECK ((unit_cost > (0)::numeric))
);


--
-- Name: purchase_orders; Type: TABLE; Schema: ops; Owner: -
--

CREATE TABLE ops.purchase_orders (
    purchase_order_id integer NOT NULL,
    po_number character varying(12) NOT NULL,
    supplier_id smallint NOT NULL,
    store_id smallint NOT NULL,
    order_date date NOT NULL,
    promised_delivery_date date NOT NULL,
    CONSTRAINT purchase_orders_check CHECK ((promised_delivery_date > order_date)),
    CONSTRAINT purchase_orders_po_number_check CHECK (((po_number)::text ~ '^PO-[0-9]{6}$'::text))
);


--
-- Name: stores; Type: TABLE; Schema: ops; Owner: -
--

CREATE TABLE ops.stores (
    store_id smallint NOT NULL,
    store_code character varying(4) NOT NULL,
    store_name character varying(60) NOT NULL,
    city character varying(40) NOT NULL,
    state_code character(2) NOT NULL,
    region_id smallint NOT NULL,
    opened_date date NOT NULL,
    sales_area_sqft integer NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT stores_sales_area_sqft_check CHECK ((sales_area_sqft > 0)),
    CONSTRAINT stores_state_code_check CHECK ((state_code ~ '^[A-Z]{2}$'::text)),
    CONSTRAINT stores_store_code_check CHECK (((store_code)::text ~ '^S[0-9]{2}$'::text))
);


--
-- Name: mv_daily_position; Type: MATERIALIZED VIEW; Schema: analytics; Owner: -
--

CREATE MATERIALIZED VIEW analytics.mv_daily_position AS
 WITH receipts_by_day AS (
         SELECT po.store_id,
            pol.product_id,
            r.received_date AS position_date,
            (sum(r.quantity_received))::integer AS units_received
           FROM ((ops.inventory_receipts r
             JOIN ops.purchase_order_lines pol ON ((pol.po_line_id = r.po_line_id)))
             JOIN ops.purchase_orders po ON ((po.purchase_order_id = pol.purchase_order_id)))
          GROUP BY po.store_id, pol.product_id, r.received_date
        ), adjustments_by_day AS (
         SELECT inventory_adjustments.store_id,
            inventory_adjustments.product_id,
            inventory_adjustments.adjustment_date AS position_date,
            (sum(inventory_adjustments.quantity_delta))::integer AS net_adjustment
           FROM ops.inventory_adjustments
          GROUP BY inventory_adjustments.store_id, inventory_adjustments.product_id, inventory_adjustments.adjustment_date
        ), promo_days AS (
         SELECT s.store_id,
            pp.product_id,
            (gs.d)::date AS position_date,
            p.promotion_id
           FROM (((ops.promotions p
             JOIN ops.promotion_products pp ON ((pp.promotion_id = p.promotion_id)))
             JOIN ops.stores s ON (((p.region_id IS NULL) OR (s.region_id = p.region_id))))
             CROSS JOIN LATERAL generate_series((p.start_date)::timestamp with time zone, (p.end_date)::timestamp with time zone, '1 day'::interval) gs(d))
        )
 SELECT i.store_id,
    i.product_id,
    i.snapshot_date AS position_date,
    i.opening_on_hand,
    COALESCE(rc.units_received, 0) AS units_received,
    ds.units_sold,
    COALESCE(ad.net_adjustment, 0) AS net_adjustment,
    i.closing_on_hand,
    (i.opening_on_hand + COALESCE(rc.units_received, 0)) AS available_units,
        CASE
            WHEN ((i.opening_on_hand + COALESCE(rc.units_received, 0)) = 0) THEN 'out_all_day'::text
            WHEN (ds.units_sold >= (i.opening_on_hand + COALESCE(rc.units_received, 0))) THEN 'sold_out'::text
            ELSE 'in_stock'::text
        END AS availability_status,
    (((i.opening_on_hand + COALESCE(rc.units_received, 0)) = 0) OR (ds.units_sold >= (i.opening_on_hand + COALESCE(rc.units_received, 0)))) AS is_censored,
    ds.net_sales_amount,
    ds.cogs_amount,
    pd.promotion_id,
    (pd.promotion_id IS NOT NULL) AS is_promo_day
   FROM ((((ops.inventory_snapshots i
     JOIN ops.daily_sales ds ON (((ds.store_id = i.store_id) AND (ds.product_id = i.product_id) AND (ds.sales_date = i.snapshot_date))))
     LEFT JOIN receipts_by_day rc ON (((rc.store_id = i.store_id) AND (rc.product_id = i.product_id) AND (rc.position_date = i.snapshot_date))))
     LEFT JOIN adjustments_by_day ad ON (((ad.store_id = i.store_id) AND (ad.product_id = i.product_id) AND (ad.position_date = i.snapshot_date))))
     LEFT JOIN promo_days pd ON (((pd.store_id = i.store_id) AND (pd.product_id = i.product_id) AND (pd.position_date = i.snapshot_date))))
  WITH NO DATA;


--
-- Name: replenishment_recommendations; Type: TABLE; Schema: analytics; Owner: -
--

CREATE TABLE analytics.replenishment_recommendations (
    recommendation_id bigint NOT NULL,
    run_id bigint NOT NULL,
    store_id smallint NOT NULL,
    product_id integer NOT NULL,
    supplier_id smallint NOT NULL,
    action_type analytics.action_type NOT NULL,
    urgency character varying(10),
    priority_rank integer,
    recommended_order_units integer,
    recommended_order_cost_usd numeric(12,2),
    related_purchase_order_id integer,
    rationale text NOT NULL,
    CONSTRAINT replenishment_recommendations_check CHECK (((action_type = 'no_action'::analytics.action_type) = (urgency IS NULL))),
    CONSTRAINT replenishment_recommendations_check1 CHECK (((action_type = 'no_action'::analytics.action_type) = (priority_rank IS NULL))),
    CONSTRAINT replenishment_recommendations_check2 CHECK (((action_type <> 'expedite_po'::analytics.action_type) OR (related_purchase_order_id IS NOT NULL))),
    CONSTRAINT replenishment_recommendations_check3 CHECK (((action_type <> 'reorder'::analytics.action_type) OR (recommended_order_units > 0))),
    CONSTRAINT replenishment_recommendations_priority_rank_check CHECK ((priority_rank >= 1)),
    CONSTRAINT replenishment_recommendations_recommended_order_units_check CHECK ((recommended_order_units >= 0)),
    CONSTRAINT replenishment_recommendations_urgency_check CHECK (((urgency)::text = ANY ((ARRAY['urgent'::character varying, 'standard'::character varying])::text[])))
);


--
-- Name: replenishment_recommendations_recommendation_id_seq; Type: SEQUENCE; Schema: analytics; Owner: -
--

ALTER TABLE analytics.replenishment_recommendations ALTER COLUMN recommendation_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME analytics.replenishment_recommendations_recommendation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: risk_checkpoints; Type: TABLE; Schema: analytics; Owner: -
--

CREATE TABLE analytics.risk_checkpoints (
    run_id bigint NOT NULL,
    store_id smallint NOT NULL,
    product_id integer NOT NULL,
    checkpoint_seq smallint NOT NULL,
    checkpoint_type analytics.checkpoint_type NOT NULL,
    purchase_order_id integer,
    arrival_date date,
    window_days numeric(6,2) NOT NULL,
    window_std_days numeric(6,2) NOT NULL,
    supply_units integer NOT NULL,
    demand_mean_units numeric(12,2) NOT NULL,
    demand_std_units numeric(12,2) NOT NULL,
    distribution_family analytics.distribution_family NOT NULL,
    stockout_probability numeric(5,4) NOT NULL,
    expected_shortage_units numeric(12,2) NOT NULL,
    is_binding boolean NOT NULL,
    CONSTRAINT risk_checkpoints_check CHECK (((checkpoint_type = 'receipt'::analytics.checkpoint_type) = (purchase_order_id IS NOT NULL))),
    CONSTRAINT risk_checkpoints_checkpoint_seq_check CHECK ((checkpoint_seq >= 1)),
    CONSTRAINT risk_checkpoints_expected_shortage_units_check CHECK ((expected_shortage_units >= (0)::numeric)),
    CONSTRAINT risk_checkpoints_stockout_probability_check CHECK (((stockout_probability >= (0)::numeric) AND (stockout_probability <= (1)::numeric))),
    CONSTRAINT risk_checkpoints_supply_units_check CHECK ((supply_units >= 0)),
    CONSTRAINT risk_checkpoints_window_days_check CHECK ((window_days >= (0)::numeric)),
    CONSTRAINT risk_checkpoints_window_std_days_check CHECK ((window_std_days >= (0)::numeric))
);


--
-- Name: supplier_lane_estimates; Type: TABLE; Schema: analytics; Owner: -
--

CREATE TABLE analytics.supplier_lane_estimates (
    run_id bigint NOT NULL,
    supplier_id smallint NOT NULL,
    store_id smallint NOT NULL,
    lead_time_source analytics.lead_time_source NOT NULL,
    n_received_pos integer NOT NULL,
    mean_lead_time_days numeric(6,2) NOT NULL,
    std_lead_time_days numeric(6,2) NOT NULL,
    mean_delay_days numeric(6,2) NOT NULL,
    std_delay_days numeric(6,2) NOT NULL,
    mean_delay_when_late_days numeric(6,2) NOT NULL,
    on_time_rate numeric(5,4),
    CONSTRAINT supplier_lane_estimates_mean_delay_when_late_days_check CHECK ((mean_delay_when_late_days >= (0)::numeric)),
    CONSTRAINT supplier_lane_estimates_mean_lead_time_days_check CHECK ((mean_lead_time_days > (0)::numeric)),
    CONSTRAINT supplier_lane_estimates_n_received_pos_check CHECK ((n_received_pos >= 0)),
    CONSTRAINT supplier_lane_estimates_on_time_rate_check CHECK (((on_time_rate >= (0)::numeric) AND (on_time_rate <= (1)::numeric))),
    CONSTRAINT supplier_lane_estimates_std_delay_days_check CHECK ((std_delay_days >= (0)::numeric)),
    CONSTRAINT supplier_lane_estimates_std_lead_time_days_check CHECK ((std_lead_time_days >= (0)::numeric))
);


--
-- Name: v_current_run; Type: VIEW; Schema: analytics; Owner: -
--

CREATE VIEW analytics.v_current_run AS
 SELECT run_id,
    as_of_date,
    model_version,
    completed_at
   FROM analytics.analytics_runs
  WHERE ((status = 'succeeded'::analytics.run_status) AND (run_type = 'current'::analytics.run_type))
  ORDER BY as_of_date DESC, completed_at DESC
 LIMIT 1;


--
-- Name: calendar; Type: TABLE; Schema: ops; Owner: -
--

CREATE TABLE ops.calendar (
    calendar_date date NOT NULL,
    iso_year smallint NOT NULL,
    iso_week smallint NOT NULL,
    iso_day_of_week smallint NOT NULL,
    day_name character varying(9) NOT NULL,
    month smallint NOT NULL,
    month_name character varying(9) NOT NULL,
    quarter smallint NOT NULL,
    week_start_date date NOT NULL,
    is_weekend boolean NOT NULL,
    holiday_name character varying(40),
    CONSTRAINT calendar_iso_day_of_week_check CHECK (((iso_day_of_week >= 1) AND (iso_day_of_week <= 7))),
    CONSTRAINT calendar_iso_week_check CHECK (((iso_week >= 1) AND (iso_week <= 53))),
    CONSTRAINT calendar_month_check CHECK (((month >= 1) AND (month <= 12))),
    CONSTRAINT calendar_quarter_check CHECK (((quarter >= 1) AND (quarter <= 4)))
);


--
-- Name: products; Type: TABLE; Schema: ops; Owner: -
--

CREATE TABLE ops.products (
    product_id integer NOT NULL,
    sku character varying(12) NOT NULL,
    product_name character varying(120) NOT NULL,
    category_id smallint NOT NULL,
    brand_name character varying(40) NOT NULL,
    unit_of_measure character varying(8) NOT NULL,
    unit_price numeric(10,2) NOT NULL,
    unit_cost numeric(10,2) NOT NULL,
    introduced_date date NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT products_check CHECK ((unit_price > unit_cost)),
    CONSTRAINT products_sku_check CHECK (((sku)::text ~ '^[A-Z]{2}-[0-9]{5}$'::text)),
    CONSTRAINT products_unit_cost_check CHECK ((unit_cost > (0)::numeric)),
    CONSTRAINT products_unit_of_measure_check CHECK (((unit_of_measure)::text = ANY ((ARRAY['each'::character varying, 'pack'::character varying, 'bag'::character varying, 'gallon'::character varying, 'roll'::character varying, 'box'::character varying])::text[]))),
    CONSTRAINT products_unit_price_check CHECK ((unit_price > (0)::numeric))
);


--
-- Name: v_category_dow_profile; Type: VIEW; Schema: analytics; Owner: -
--

CREATE VIEW analytics.v_category_dow_profile AS
 WITH cr AS (
         SELECT v_current_run.as_of_date
           FROM analytics.v_current_run
        ), base AS (
         SELECT p.category_id,
            c.iso_day_of_week,
            m.units_sold
           FROM (((analytics.mv_daily_position m
             JOIN ops.products p ON ((p.product_id = m.product_id)))
             JOIN ops.calendar c ON ((c.calendar_date = m.position_date)))
             CROSS JOIN cr)
          WHERE (((m.position_date >= (cr.as_of_date - 55)) AND (m.position_date <= cr.as_of_date)) AND (m.availability_status = 'in_stock'::text) AND (NOT m.is_promo_day))
        ), by_dow AS (
         SELECT base.category_id,
            base.iso_day_of_week,
            avg(base.units_sold) AS avg_units,
            count(*) AS n_obs
           FROM base
          GROUP BY base.category_id, base.iso_day_of_week
        )
 SELECT category_id,
    iso_day_of_week,
    avg_units,
    n_obs,
    (avg_units / NULLIF(avg(avg_units) OVER (PARTITION BY category_id), (0)::numeric)) AS dow_index
   FROM by_dow;


--
-- Name: product_categories; Type: TABLE; Schema: ops; Owner: -
--

CREATE TABLE ops.product_categories (
    category_id smallint NOT NULL,
    category_code character varying(4) NOT NULL,
    category_name character varying(40) NOT NULL,
    CONSTRAINT product_categories_category_code_check CHECK (((category_code)::text ~ '^[A-Z]{2}$'::text))
);


--
-- Name: regions; Type: TABLE; Schema: ops; Owner: -
--

CREATE TABLE ops.regions (
    region_id smallint NOT NULL,
    region_code character varying(4) NOT NULL,
    region_name character varying(40) NOT NULL,
    CONSTRAINT regions_region_code_check CHECK (((region_code)::text ~ '^[A-Z]{2}$'::text))
);


--
-- Name: suppliers; Type: TABLE; Schema: ops; Owner: -
--

CREATE TABLE ops.suppliers (
    supplier_id smallint NOT NULL,
    supplier_code character varying(8) NOT NULL,
    supplier_name character varying(80) NOT NULL,
    primary_category_id smallint NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT suppliers_supplier_code_check CHECK (((supplier_code)::text ~ '^SUP-[0-9]{3}$'::text))
);


--
-- Name: v_current_risk; Type: VIEW; Schema: analytics; Owner: -
--

CREATE VIEW analytics.v_current_risk AS
 SELECT r.run_id,
    r.store_id,
    st.store_code,
    st.store_name,
    st.region_id,
    rg.region_name,
    r.product_id,
    p.sku,
    p.product_name,
    p.category_id,
    pc.category_name,
    r.supplier_id,
    su.supplier_name,
    p.unit_price,
    p.unit_cost,
    r.on_hand_units,
    r.on_order_units,
    r.inventory_position_units,
    r.avg_daily_demand_units,
    r.days_of_cover,
    r.next_receipt_date,
    r.next_receipt_units,
    r.next_receipt_po_id,
    npo.po_number AS next_receipt_po_number,
    r.next_receipt_overdue,
    r.lead_time_mean_days,
    r.safety_stock_units,
    r.reorder_point_units,
    r.order_up_to_units,
    r.below_reorder_point,
    r.stockout_probability,
    r.risk_tier,
    r.risk_drivers,
    r.expected_shortage_units,
    r.revenue_at_risk_usd,
    r.margin_at_risk_usd,
    r.projected_stockout_date,
    r.days_until_projected_stockout,
    r.currently_out_of_stock,
    rr.action_type,
    rr.urgency,
    rr.priority_rank,
    rr.recommended_order_units,
    rr.recommended_order_cost_usd,
    rr.related_purchase_order_id
   FROM ((((((((analytics.inventory_risk_snapshots r
     JOIN analytics.v_current_run cr ON ((cr.run_id = r.run_id)))
     JOIN ops.stores st ON ((st.store_id = r.store_id)))
     JOIN ops.regions rg ON ((rg.region_id = st.region_id)))
     JOIN ops.products p ON ((p.product_id = r.product_id)))
     JOIN ops.product_categories pc ON ((pc.category_id = p.category_id)))
     JOIN ops.suppliers su ON ((su.supplier_id = r.supplier_id)))
     JOIN analytics.replenishment_recommendations rr ON (((rr.run_id = r.run_id) AND (rr.store_id = r.store_id) AND (rr.product_id = r.product_id))))
     LEFT JOIN ops.purchase_orders npo ON ((npo.purchase_order_id = r.next_receipt_po_id)));


--
-- Name: v_inventory_reconciliation; Type: VIEW; Schema: analytics; Owner: -
--

CREATE VIEW analytics.v_inventory_reconciliation AS
 WITH rec AS (
         SELECT po.store_id,
            pol.product_id,
            r.received_date AS d,
            (sum(r.quantity_received))::integer AS units_received
           FROM ((ops.inventory_receipts r
             JOIN ops.purchase_order_lines pol ON ((pol.po_line_id = r.po_line_id)))
             JOIN ops.purchase_orders po ON ((po.purchase_order_id = pol.purchase_order_id)))
          GROUP BY po.store_id, pol.product_id, r.received_date
        ), adj AS (
         SELECT inventory_adjustments.store_id,
            inventory_adjustments.product_id,
            inventory_adjustments.adjustment_date AS d,
            (sum(inventory_adjustments.quantity_delta))::integer AS net_adjustment
           FROM ops.inventory_adjustments
          GROUP BY inventory_adjustments.store_id, inventory_adjustments.product_id, inventory_adjustments.adjustment_date
        )
 SELECT i.store_id,
    i.product_id,
    i.snapshot_date,
    i.opening_on_hand,
    COALESCE(rec.units_received, 0) AS units_received,
    s.units_sold,
    COALESCE(adj.net_adjustment, 0) AS net_adjustment,
    i.closing_on_hand,
    (((i.opening_on_hand + COALESCE(rec.units_received, 0)) - s.units_sold) + COALESCE(adj.net_adjustment, 0)) AS expected_closing,
    (i.closing_on_hand - (((i.opening_on_hand + COALESCE(rec.units_received, 0)) - s.units_sold) + COALESCE(adj.net_adjustment, 0))) AS discrepancy
   FROM (((ops.inventory_snapshots i
     JOIN ops.daily_sales s ON (((s.store_id = i.store_id) AND (s.product_id = i.product_id) AND (s.sales_date = i.snapshot_date))))
     LEFT JOIN rec ON (((rec.store_id = i.store_id) AND (rec.product_id = i.product_id) AND (rec.d = i.snapshot_date))))
     LEFT JOIN adj ON (((adj.store_id = i.store_id) AND (adj.product_id = i.product_id) AND (adj.d = i.snapshot_date))));


--
-- Name: v_po_line_status; Type: VIEW; Schema: analytics; Owner: -
--

CREATE VIEW analytics.v_po_line_status AS
 WITH rec AS (
         SELECT inventory_receipts.po_line_id,
            (sum(inventory_receipts.quantity_received))::integer AS quantity_received,
            min(inventory_receipts.received_date) AS first_receipt_date,
            max(inventory_receipts.received_date) AS last_receipt_date,
            (count(*))::integer AS receipt_count
           FROM ops.inventory_receipts
          GROUP BY inventory_receipts.po_line_id
        )
 SELECT pol.po_line_id,
    pol.purchase_order_id,
    po.po_number,
    po.supplier_id,
    po.store_id,
    pol.product_id,
    po.order_date,
    po.promised_delivery_date,
    pol.quantity_ordered,
    pol.quantity_cancelled,
    COALESCE(rec.quantity_received, 0) AS quantity_received,
    ((pol.quantity_ordered - pol.quantity_cancelled) - COALESCE(rec.quantity_received, 0)) AS open_quantity,
    rec.first_receipt_date,
    rec.last_receipt_date,
    COALESCE(rec.receipt_count, 0) AS receipt_count,
    pol.unit_cost,
        CASE
            WHEN ((((pol.quantity_ordered - pol.quantity_cancelled) - COALESCE(rec.quantity_received, 0)) > 0) AND (COALESCE(rec.quantity_received, 0) = 0)) THEN 'open'::text
            WHEN (((pol.quantity_ordered - pol.quantity_cancelled) - COALESCE(rec.quantity_received, 0)) > 0) THEN 'partially_received'::text
            WHEN (pol.quantity_cancelled > 0) THEN 'closed_short'::text
            ELSE 'received'::text
        END AS line_status
   FROM ((ops.purchase_order_lines pol
     JOIN ops.purchase_orders po ON ((po.purchase_order_id = pol.purchase_order_id)))
     LEFT JOIN rec ON ((rec.po_line_id = pol.po_line_id)));


--
-- Name: v_po_status; Type: VIEW; Schema: analytics; Owner: -
--

CREATE VIEW analytics.v_po_status AS
 SELECT purchase_order_id,
    po_number,
    supplier_id,
    store_id,
    order_date,
    promised_delivery_date,
    (count(*))::integer AS line_count,
    (sum(quantity_ordered))::integer AS units_ordered,
    (sum(quantity_received))::integer AS units_received,
    (sum(quantity_cancelled))::integer AS units_cancelled,
    (sum(open_quantity))::integer AS units_open,
    min(first_receipt_date) AS first_receipt_date,
    (min(first_receipt_date) - order_date) AS lead_time_days,
    (min(first_receipt_date) - promised_delivery_date) AS delay_days,
        CASE
            WHEN (min(first_receipt_date) IS NULL) THEN NULL::boolean
            ELSE (min(first_receipt_date) <= promised_delivery_date)
        END AS on_time,
    bool_and(((quantity_cancelled = 0) AND (receipt_count = 1) AND (quantity_received = quantity_ordered))) AS in_full,
        CASE
            WHEN ((sum(open_quantity) = 0) AND (sum(quantity_cancelled) > 0)) THEN 'closed_short'::text
            WHEN (sum(open_quantity) = 0) THEN 'received'::text
            WHEN (sum(quantity_received) > 0) THEN 'partially_received'::text
            ELSE 'open'::text
        END AS po_status
   FROM analytics.v_po_line_status
  GROUP BY purchase_order_id, po_number, supplier_id, store_id, order_date, promised_delivery_date;


--
-- Name: v_product_abc_class; Type: VIEW; Schema: analytics; Owner: -
--

CREATE VIEW analytics.v_product_abc_class AS
 WITH cr AS (
         SELECT v_current_run.as_of_date
           FROM analytics.v_current_run
        ), rev AS (
         SELECT m.product_id,
            sum(m.net_sales_amount) AS revenue
           FROM (analytics.mv_daily_position m
             CROSS JOIN cr)
          WHERE ((m.position_date >= (cr.as_of_date - 55)) AND (m.position_date <= cr.as_of_date))
          GROUP BY m.product_id
        ), ranked AS (
         SELECT rev.product_id,
            rev.revenue,
            (sum(rev.revenue) OVER (ORDER BY rev.revenue DESC, rev.product_id ROWS UNBOUNDED PRECEDING) - rev.revenue) AS revenue_before,
            sum(rev.revenue) OVER () AS total_revenue
           FROM rev
        )
 SELECT product_id,
    revenue,
    round((revenue_before / NULLIF(total_revenue, (0)::numeric)), 4) AS cumulative_share_before,
        CASE
            WHEN ((revenue_before / NULLIF(total_revenue, (0)::numeric)) < 0.80) THEN 'A'::text
            WHEN ((revenue_before / NULLIF(total_revenue, (0)::numeric)) < 0.95) THEN 'B'::text
            ELSE 'C'::text
        END AS abc_class
   FROM ranked;


--
-- Name: v_risk_trend; Type: VIEW; Schema: analytics; Owner: -
--

CREATE VIEW analytics.v_risk_trend AS
 WITH latest_runs AS (
         SELECT DISTINCT ON (analytics_runs.as_of_date) analytics_runs.run_id,
            analytics_runs.as_of_date,
            analytics_runs.run_type
           FROM analytics.analytics_runs
          WHERE (analytics_runs.status = 'succeeded'::analytics.run_status)
          ORDER BY analytics_runs.as_of_date, (analytics_runs.run_type = 'current'::analytics.run_type) DESC, analytics_runs.completed_at DESC
        )
 SELECT lr.as_of_date,
    lr.run_id,
    r.store_id,
    st.region_id,
    p.category_id,
    r.risk_tier,
    (count(*))::integer AS positions,
    sum(r.margin_at_risk_usd) AS margin_at_risk_usd,
    sum(r.revenue_at_risk_usd) AS revenue_at_risk_usd
   FROM (((latest_runs lr
     JOIN analytics.inventory_risk_snapshots r ON ((r.run_id = lr.run_id)))
     JOIN ops.products p ON ((p.product_id = r.product_id)))
     JOIN ops.stores st ON ((st.store_id = r.store_id)))
  GROUP BY lr.as_of_date, lr.run_id, r.store_id, st.region_id, p.category_id, r.risk_tier;


--
-- Name: v_stockout_episodes; Type: VIEW; Schema: analytics; Owner: -
--

CREATE VIEW analytics.v_stockout_episodes AS
 WITH flagged AS (
         SELECT mv_daily_position.store_id,
            mv_daily_position.product_id,
            mv_daily_position.position_date,
            mv_daily_position.is_censored,
            (mv_daily_position.position_date - (row_number() OVER (PARTITION BY mv_daily_position.store_id, mv_daily_position.product_id, mv_daily_position.is_censored ORDER BY mv_daily_position.position_date))::integer) AS island_key
           FROM analytics.mv_daily_position
        )
 SELECT store_id,
    product_id,
    min(position_date) AS episode_start,
    max(position_date) AS episode_end,
    (count(*))::integer AS episode_days
   FROM flagged
  WHERE is_censored
  GROUP BY store_id, product_id, island_key;


--
-- Name: v_supplier_lane_performance; Type: VIEW; Schema: analytics; Owner: -
--

CREATE VIEW analytics.v_supplier_lane_performance AS
SELECT
    NULL::smallint AS supplier_id,
    NULL::smallint AS store_id,
    NULL::bigint AS received_pos,
    NULL::numeric AS mean_lead_time_days,
    NULL::numeric AS std_lead_time_days,
    NULL::bigint AS pos_due_90d,
    NULL::bigint AS on_time_pos_90d,
    NULL::bigint AS overdue_open_pos;


--
-- Name: v_supplier_performance; Type: VIEW; Schema: analytics; Owner: -
--

CREATE VIEW analytics.v_supplier_performance AS
SELECT
    NULL::smallint AS supplier_id,
    NULL::character varying(8) AS supplier_code,
    NULL::character varying(80) AS supplier_name,
    NULL::character varying(40) AS category_name,
    NULL::bigint AS pos_due_90d,
    NULL::numeric AS on_time_rate,
    NULL::numeric AS in_full_rate,
    NULL::numeric AS mean_lead_time_days,
    NULL::numeric AS std_lead_time_days,
    NULL::numeric AS p90_lead_time_days,
    NULL::numeric AS lead_time_cv,
    NULL::bigint AS overdue_open_pos,
    NULL::bigint AS at_risk_positions,
    NULL::numeric AS margin_at_risk_usd,
    NULL::boolean AS review_flag,
    NULL::bigint AS reliability_rank;


--
-- Name: dataset_manifest; Type: TABLE; Schema: ops; Owner: -
--

CREATE TABLE ops.dataset_manifest (
    dataset_id smallint NOT NULL,
    data_origin character varying(20) NOT NULL,
    generator_version character varying(20) NOT NULL,
    preset character varying(20) NOT NULL,
    seed integer NOT NULL,
    history_start_date date NOT NULL,
    history_end_date date NOT NULL,
    generated_at timestamp with time zone NOT NULL,
    loaded_at timestamp with time zone DEFAULT now() NOT NULL,
    row_counts jsonb NOT NULL,
    content_checksum character(64) NOT NULL,
    notes text NOT NULL,
    CONSTRAINT dataset_manifest_check CHECK ((history_end_date > history_start_date)),
    CONSTRAINT dataset_manifest_data_origin_check CHECK (((data_origin)::text = ANY ((ARRAY['synthetic'::character varying, 'public'::character varying])::text[]))),
    CONSTRAINT dataset_manifest_dataset_id_check CHECK ((dataset_id = 1)),
    CONSTRAINT dataset_manifest_preset_check CHECK (((preset)::text = ANY ((ARRAY['small'::character varying, 'standard'::character varying, 'large'::character varying])::text[])))
);


--
-- Name: dataset_manifest_dataset_id_seq; Type: SEQUENCE; Schema: ops; Owner: -
--

CREATE SEQUENCE ops.dataset_manifest_dataset_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: dataset_manifest_dataset_id_seq; Type: SEQUENCE OWNED BY; Schema: ops; Owner: -
--

ALTER SEQUENCE ops.dataset_manifest_dataset_id_seq OWNED BY ops.dataset_manifest.dataset_id;


--
-- Name: inventory_adjustments_adjustment_id_seq; Type: SEQUENCE; Schema: ops; Owner: -
--

CREATE SEQUENCE ops.inventory_adjustments_adjustment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inventory_adjustments_adjustment_id_seq; Type: SEQUENCE OWNED BY; Schema: ops; Owner: -
--

ALTER SEQUENCE ops.inventory_adjustments_adjustment_id_seq OWNED BY ops.inventory_adjustments.adjustment_id;


--
-- Name: inventory_receipts_receipt_id_seq; Type: SEQUENCE; Schema: ops; Owner: -
--

CREATE SEQUENCE ops.inventory_receipts_receipt_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inventory_receipts_receipt_id_seq; Type: SEQUENCE OWNED BY; Schema: ops; Owner: -
--

ALTER SEQUENCE ops.inventory_receipts_receipt_id_seq OWNED BY ops.inventory_receipts.receipt_id;


--
-- Name: product_categories_category_id_seq; Type: SEQUENCE; Schema: ops; Owner: -
--

CREATE SEQUENCE ops.product_categories_category_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: product_categories_category_id_seq; Type: SEQUENCE OWNED BY; Schema: ops; Owner: -
--

ALTER SEQUENCE ops.product_categories_category_id_seq OWNED BY ops.product_categories.category_id;


--
-- Name: product_suppliers; Type: TABLE; Schema: ops; Owner: -
--

CREATE TABLE ops.product_suppliers (
    product_id integer NOT NULL,
    supplier_id smallint NOT NULL,
    is_primary boolean NOT NULL,
    case_pack_qty integer NOT NULL,
    min_order_qty integer NOT NULL,
    CONSTRAINT product_suppliers_case_pack_qty_check CHECK ((case_pack_qty > 0)),
    CONSTRAINT product_suppliers_check CHECK (((min_order_qty % case_pack_qty) = 0)),
    CONSTRAINT product_suppliers_min_order_qty_check CHECK ((min_order_qty > 0))
);


--
-- Name: products_product_id_seq; Type: SEQUENCE; Schema: ops; Owner: -
--

CREATE SEQUENCE ops.products_product_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: products_product_id_seq; Type: SEQUENCE OWNED BY; Schema: ops; Owner: -
--

ALTER SEQUENCE ops.products_product_id_seq OWNED BY ops.products.product_id;


--
-- Name: promotions_promotion_id_seq; Type: SEQUENCE; Schema: ops; Owner: -
--

CREATE SEQUENCE ops.promotions_promotion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: promotions_promotion_id_seq; Type: SEQUENCE OWNED BY; Schema: ops; Owner: -
--

ALTER SEQUENCE ops.promotions_promotion_id_seq OWNED BY ops.promotions.promotion_id;


--
-- Name: purchase_order_lines_po_line_id_seq; Type: SEQUENCE; Schema: ops; Owner: -
--

CREATE SEQUENCE ops.purchase_order_lines_po_line_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: purchase_order_lines_po_line_id_seq; Type: SEQUENCE OWNED BY; Schema: ops; Owner: -
--

ALTER SEQUENCE ops.purchase_order_lines_po_line_id_seq OWNED BY ops.purchase_order_lines.po_line_id;


--
-- Name: purchase_orders_purchase_order_id_seq; Type: SEQUENCE; Schema: ops; Owner: -
--

CREATE SEQUENCE ops.purchase_orders_purchase_order_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: purchase_orders_purchase_order_id_seq; Type: SEQUENCE OWNED BY; Schema: ops; Owner: -
--

ALTER SEQUENCE ops.purchase_orders_purchase_order_id_seq OWNED BY ops.purchase_orders.purchase_order_id;


--
-- Name: regions_region_id_seq; Type: SEQUENCE; Schema: ops; Owner: -
--

CREATE SEQUENCE ops.regions_region_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: regions_region_id_seq; Type: SEQUENCE OWNED BY; Schema: ops; Owner: -
--

ALTER SEQUENCE ops.regions_region_id_seq OWNED BY ops.regions.region_id;


--
-- Name: stores_store_id_seq; Type: SEQUENCE; Schema: ops; Owner: -
--

CREATE SEQUENCE ops.stores_store_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stores_store_id_seq; Type: SEQUENCE OWNED BY; Schema: ops; Owner: -
--

ALTER SEQUENCE ops.stores_store_id_seq OWNED BY ops.stores.store_id;


--
-- Name: supplier_store_lanes; Type: TABLE; Schema: ops; Owner: -
--

CREATE TABLE ops.supplier_store_lanes (
    supplier_id smallint NOT NULL,
    store_id smallint NOT NULL,
    contract_lead_time_days smallint NOT NULL,
    review_weekday smallint NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT supplier_store_lanes_contract_lead_time_days_check CHECK (((contract_lead_time_days >= 1) AND (contract_lead_time_days <= 60))),
    CONSTRAINT supplier_store_lanes_review_weekday_check CHECK (((review_weekday >= 1) AND (review_weekday <= 7)))
);


--
-- Name: suppliers_supplier_id_seq; Type: SEQUENCE; Schema: ops; Owner: -
--

CREATE SEQUENCE ops.suppliers_supplier_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: suppliers_supplier_id_seq; Type: SEQUENCE OWNED BY; Schema: ops; Owner: -
--

ALTER SEQUENCE ops.suppliers_supplier_id_seq OWNED BY ops.suppliers.supplier_id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: latent_demand; Type: TABLE; Schema: sim_truth; Owner: -
--

CREATE TABLE sim_truth.latent_demand (
    store_id smallint NOT NULL,
    product_id integer NOT NULL,
    demand_date date NOT NULL,
    latent_units integer NOT NULL,
    CONSTRAINT latent_demand_latent_units_check CHECK ((latent_units >= 0))
);


--
-- Name: dataset_manifest dataset_id; Type: DEFAULT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.dataset_manifest ALTER COLUMN dataset_id SET DEFAULT nextval('ops.dataset_manifest_dataset_id_seq'::regclass);


--
-- Name: inventory_adjustments adjustment_id; Type: DEFAULT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.inventory_adjustments ALTER COLUMN adjustment_id SET DEFAULT nextval('ops.inventory_adjustments_adjustment_id_seq'::regclass);


--
-- Name: inventory_receipts receipt_id; Type: DEFAULT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.inventory_receipts ALTER COLUMN receipt_id SET DEFAULT nextval('ops.inventory_receipts_receipt_id_seq'::regclass);


--
-- Name: product_categories category_id; Type: DEFAULT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.product_categories ALTER COLUMN category_id SET DEFAULT nextval('ops.product_categories_category_id_seq'::regclass);


--
-- Name: products product_id; Type: DEFAULT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.products ALTER COLUMN product_id SET DEFAULT nextval('ops.products_product_id_seq'::regclass);


--
-- Name: promotions promotion_id; Type: DEFAULT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.promotions ALTER COLUMN promotion_id SET DEFAULT nextval('ops.promotions_promotion_id_seq'::regclass);


--
-- Name: purchase_order_lines po_line_id; Type: DEFAULT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.purchase_order_lines ALTER COLUMN po_line_id SET DEFAULT nextval('ops.purchase_order_lines_po_line_id_seq'::regclass);


--
-- Name: purchase_orders purchase_order_id; Type: DEFAULT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.purchase_orders ALTER COLUMN purchase_order_id SET DEFAULT nextval('ops.purchase_orders_purchase_order_id_seq'::regclass);


--
-- Name: regions region_id; Type: DEFAULT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.regions ALTER COLUMN region_id SET DEFAULT nextval('ops.regions_region_id_seq'::regclass);


--
-- Name: stores store_id; Type: DEFAULT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.stores ALTER COLUMN store_id SET DEFAULT nextval('ops.stores_store_id_seq'::regclass);


--
-- Name: suppliers supplier_id; Type: DEFAULT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.suppliers ALTER COLUMN supplier_id SET DEFAULT nextval('ops.suppliers_supplier_id_seq'::regclass);


--
-- Name: analytics_runs analytics_runs_pkey; Type: CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.analytics_runs
    ADD CONSTRAINT analytics_runs_pkey PRIMARY KEY (run_id);


--
-- Name: demand_forecast_daily demand_forecast_daily_pkey; Type: CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.demand_forecast_daily
    ADD CONSTRAINT demand_forecast_daily_pkey PRIMARY KEY (run_id, store_id, product_id, target_date);


--
-- Name: demand_forecasts demand_forecasts_pkey; Type: CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.demand_forecasts
    ADD CONSTRAINT demand_forecasts_pkey PRIMARY KEY (run_id, store_id, product_id);


--
-- Name: forecast_evaluations forecast_evaluations_pkey; Type: CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.forecast_evaluations
    ADD CONSTRAINT forecast_evaluations_pkey PRIMARY KEY (evaluation_id);


--
-- Name: forecast_evaluations forecast_evaluations_run_id_model_name_evaluation_basis_seg_key; Type: CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.forecast_evaluations
    ADD CONSTRAINT forecast_evaluations_run_id_model_name_evaluation_basis_seg_key UNIQUE (run_id, model_name, evaluation_basis, segment_type, segment_value);


--
-- Name: inventory_risk_snapshots inventory_risk_snapshots_pkey; Type: CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.inventory_risk_snapshots
    ADD CONSTRAINT inventory_risk_snapshots_pkey PRIMARY KEY (run_id, store_id, product_id);


--
-- Name: replenishment_recommendations replenishment_recommendations_pkey; Type: CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.replenishment_recommendations
    ADD CONSTRAINT replenishment_recommendations_pkey PRIMARY KEY (recommendation_id);


--
-- Name: replenishment_recommendations replenishment_recommendations_run_id_store_id_product_id_key; Type: CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.replenishment_recommendations
    ADD CONSTRAINT replenishment_recommendations_run_id_store_id_product_id_key UNIQUE (run_id, store_id, product_id);


--
-- Name: risk_checkpoints risk_checkpoints_pkey; Type: CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.risk_checkpoints
    ADD CONSTRAINT risk_checkpoints_pkey PRIMARY KEY (run_id, store_id, product_id, checkpoint_seq);


--
-- Name: supplier_lane_estimates supplier_lane_estimates_pkey; Type: CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.supplier_lane_estimates
    ADD CONSTRAINT supplier_lane_estimates_pkey PRIMARY KEY (run_id, supplier_id, store_id);


--
-- Name: calendar calendar_pkey; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.calendar
    ADD CONSTRAINT calendar_pkey PRIMARY KEY (calendar_date);


--
-- Name: daily_sales daily_sales_pkey; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.daily_sales
    ADD CONSTRAINT daily_sales_pkey PRIMARY KEY (store_id, product_id, sales_date);


--
-- Name: dataset_manifest dataset_manifest_pkey; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.dataset_manifest
    ADD CONSTRAINT dataset_manifest_pkey PRIMARY KEY (dataset_id);


--
-- Name: inventory_adjustments inventory_adjustments_pkey; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.inventory_adjustments
    ADD CONSTRAINT inventory_adjustments_pkey PRIMARY KEY (adjustment_id);


--
-- Name: inventory_adjustments inventory_adjustments_store_id_product_id_adjustment_date_r_key; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.inventory_adjustments
    ADD CONSTRAINT inventory_adjustments_store_id_product_id_adjustment_date_r_key UNIQUE (store_id, product_id, adjustment_date, reason_code);


--
-- Name: inventory_receipts inventory_receipts_pkey; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.inventory_receipts
    ADD CONSTRAINT inventory_receipts_pkey PRIMARY KEY (receipt_id);


--
-- Name: inventory_receipts inventory_receipts_po_line_id_received_date_key; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.inventory_receipts
    ADD CONSTRAINT inventory_receipts_po_line_id_received_date_key UNIQUE (po_line_id, received_date);


--
-- Name: inventory_snapshots inventory_snapshots_pkey; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.inventory_snapshots
    ADD CONSTRAINT inventory_snapshots_pkey PRIMARY KEY (store_id, product_id, snapshot_date);


--
-- Name: product_categories product_categories_category_code_key; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.product_categories
    ADD CONSTRAINT product_categories_category_code_key UNIQUE (category_code);


--
-- Name: product_categories product_categories_category_name_key; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.product_categories
    ADD CONSTRAINT product_categories_category_name_key UNIQUE (category_name);


--
-- Name: product_categories product_categories_pkey; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.product_categories
    ADD CONSTRAINT product_categories_pkey PRIMARY KEY (category_id);


--
-- Name: product_suppliers product_suppliers_pkey; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.product_suppliers
    ADD CONSTRAINT product_suppliers_pkey PRIMARY KEY (product_id, supplier_id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (product_id);


--
-- Name: products products_sku_key; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.products
    ADD CONSTRAINT products_sku_key UNIQUE (sku);


--
-- Name: promotion_products promotion_products_pkey; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.promotion_products
    ADD CONSTRAINT promotion_products_pkey PRIMARY KEY (promotion_id, product_id);


--
-- Name: promotions promotions_pkey; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.promotions
    ADD CONSTRAINT promotions_pkey PRIMARY KEY (promotion_id);


--
-- Name: promotions promotions_promotion_code_key; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.promotions
    ADD CONSTRAINT promotions_promotion_code_key UNIQUE (promotion_code);


--
-- Name: purchase_order_lines purchase_order_lines_pkey; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.purchase_order_lines
    ADD CONSTRAINT purchase_order_lines_pkey PRIMARY KEY (po_line_id);


--
-- Name: purchase_order_lines purchase_order_lines_purchase_order_id_line_number_key; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.purchase_order_lines
    ADD CONSTRAINT purchase_order_lines_purchase_order_id_line_number_key UNIQUE (purchase_order_id, line_number);


--
-- Name: purchase_order_lines purchase_order_lines_purchase_order_id_product_id_key; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.purchase_order_lines
    ADD CONSTRAINT purchase_order_lines_purchase_order_id_product_id_key UNIQUE (purchase_order_id, product_id);


--
-- Name: purchase_orders purchase_orders_pkey; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.purchase_orders
    ADD CONSTRAINT purchase_orders_pkey PRIMARY KEY (purchase_order_id);


--
-- Name: purchase_orders purchase_orders_po_number_key; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.purchase_orders
    ADD CONSTRAINT purchase_orders_po_number_key UNIQUE (po_number);


--
-- Name: regions regions_pkey; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.regions
    ADD CONSTRAINT regions_pkey PRIMARY KEY (region_id);


--
-- Name: regions regions_region_code_key; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.regions
    ADD CONSTRAINT regions_region_code_key UNIQUE (region_code);


--
-- Name: regions regions_region_name_key; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.regions
    ADD CONSTRAINT regions_region_name_key UNIQUE (region_name);


--
-- Name: stores stores_pkey; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.stores
    ADD CONSTRAINT stores_pkey PRIMARY KEY (store_id);


--
-- Name: stores stores_store_code_key; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.stores
    ADD CONSTRAINT stores_store_code_key UNIQUE (store_code);


--
-- Name: supplier_store_lanes supplier_store_lanes_pkey; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.supplier_store_lanes
    ADD CONSTRAINT supplier_store_lanes_pkey PRIMARY KEY (supplier_id, store_id);


--
-- Name: suppliers suppliers_pkey; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.suppliers
    ADD CONSTRAINT suppliers_pkey PRIMARY KEY (supplier_id);


--
-- Name: suppliers suppliers_supplier_code_key; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.suppliers
    ADD CONSTRAINT suppliers_supplier_code_key UNIQUE (supplier_code);


--
-- Name: suppliers suppliers_supplier_name_key; Type: CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.suppliers
    ADD CONSTRAINT suppliers_supplier_name_key UNIQUE (supplier_name);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: latent_demand latent_demand_pkey; Type: CONSTRAINT; Schema: sim_truth; Owner: -
--

ALTER TABLE ONLY sim_truth.latent_demand
    ADD CONSTRAINT latent_demand_pkey PRIMARY KEY (store_id, product_id, demand_date);


--
-- Name: ix_mv_daily_position_date; Type: INDEX; Schema: analytics; Owner: -
--

CREATE INDEX ix_mv_daily_position_date ON analytics.mv_daily_position USING btree (position_date);


--
-- Name: ix_risk_run_product; Type: INDEX; Schema: analytics; Owner: -
--

CREATE INDEX ix_risk_run_product ON analytics.inventory_risk_snapshots USING btree (run_id, product_id);


--
-- Name: ix_risk_run_store; Type: INDEX; Schema: analytics; Owner: -
--

CREATE INDEX ix_risk_run_store ON analytics.inventory_risk_snapshots USING btree (run_id, store_id);


--
-- Name: ix_risk_run_supplier; Type: INDEX; Schema: analytics; Owner: -
--

CREATE INDEX ix_risk_run_supplier ON analytics.inventory_risk_snapshots USING btree (run_id, supplier_id);


--
-- Name: ix_risk_run_tier_margin; Type: INDEX; Schema: analytics; Owner: -
--

CREATE INDEX ix_risk_run_tier_margin ON analytics.inventory_risk_snapshots USING btree (run_id, risk_tier DESC, margin_at_risk_usd DESC);


--
-- Name: ix_runs_status_type_asof; Type: INDEX; Schema: analytics; Owner: -
--

CREATE INDEX ix_runs_status_type_asof ON analytics.analytics_runs USING btree (status, run_type, as_of_date DESC, completed_at DESC);


--
-- Name: ux_checkpoints_one_binding; Type: INDEX; Schema: analytics; Owner: -
--

CREATE UNIQUE INDEX ux_checkpoints_one_binding ON analytics.risk_checkpoints USING btree (run_id, store_id, product_id) WHERE is_binding;


--
-- Name: ux_mv_daily_position; Type: INDEX; Schema: analytics; Owner: -
--

CREATE UNIQUE INDEX ux_mv_daily_position ON analytics.mv_daily_position USING btree (store_id, product_id, position_date);


--
-- Name: ux_recommendations_run_priority; Type: INDEX; Schema: analytics; Owner: -
--

CREATE UNIQUE INDEX ux_recommendations_run_priority ON analytics.replenishment_recommendations USING btree (run_id, priority_rank) WHERE (priority_rank IS NOT NULL);


--
-- Name: brin_daily_sales_sales_date; Type: INDEX; Schema: ops; Owner: -
--

CREATE INDEX brin_daily_sales_sales_date ON ops.daily_sales USING brin (sales_date);


--
-- Name: ix_calendar_week_start_date; Type: INDEX; Schema: ops; Owner: -
--

CREATE INDEX ix_calendar_week_start_date ON ops.calendar USING btree (week_start_date);


--
-- Name: ix_inventory_snapshots_date; Type: INDEX; Schema: ops; Owner: -
--

CREATE INDEX ix_inventory_snapshots_date ON ops.inventory_snapshots USING btree (snapshot_date);


--
-- Name: ix_lanes_store_id; Type: INDEX; Schema: ops; Owner: -
--

CREATE INDEX ix_lanes_store_id ON ops.supplier_store_lanes USING btree (store_id);


--
-- Name: ix_po_lines_product_id; Type: INDEX; Schema: ops; Owner: -
--

CREATE INDEX ix_po_lines_product_id ON ops.purchase_order_lines USING btree (product_id);


--
-- Name: ix_po_store_order_date; Type: INDEX; Schema: ops; Owner: -
--

CREATE INDEX ix_po_store_order_date ON ops.purchase_orders USING btree (store_id, order_date);


--
-- Name: ix_po_supplier_promised; Type: INDEX; Schema: ops; Owner: -
--

CREATE INDEX ix_po_supplier_promised ON ops.purchase_orders USING btree (supplier_id, promised_delivery_date);


--
-- Name: ix_product_suppliers_supplier_id; Type: INDEX; Schema: ops; Owner: -
--

CREATE INDEX ix_product_suppliers_supplier_id ON ops.product_suppliers USING btree (supplier_id);


--
-- Name: ix_products_category_id; Type: INDEX; Schema: ops; Owner: -
--

CREATE INDEX ix_products_category_id ON ops.products USING btree (category_id);


--
-- Name: ix_promotion_products_product_id; Type: INDEX; Schema: ops; Owner: -
--

CREATE INDEX ix_promotion_products_product_id ON ops.promotion_products USING btree (product_id);


--
-- Name: ix_promotions_dates; Type: INDEX; Schema: ops; Owner: -
--

CREATE INDEX ix_promotions_dates ON ops.promotions USING btree (start_date, end_date);


--
-- Name: ix_receipts_received_date; Type: INDEX; Schema: ops; Owner: -
--

CREATE INDEX ix_receipts_received_date ON ops.inventory_receipts USING btree (received_date);


--
-- Name: ix_stores_region_id; Type: INDEX; Schema: ops; Owner: -
--

CREATE INDEX ix_stores_region_id ON ops.stores USING btree (region_id);


--
-- Name: ix_suppliers_primary_category_id; Type: INDEX; Schema: ops; Owner: -
--

CREATE INDEX ix_suppliers_primary_category_id ON ops.suppliers USING btree (primary_category_id);


--
-- Name: ux_product_suppliers_one_primary; Type: INDEX; Schema: ops; Owner: -
--

CREATE UNIQUE INDEX ux_product_suppliers_one_primary ON ops.product_suppliers USING btree (product_id) WHERE is_primary;


--
-- Name: v_supplier_lane_performance _RETURN; Type: RULE; Schema: analytics; Owner: -
--

CREATE OR REPLACE VIEW analytics.v_supplier_lane_performance AS
 WITH cr AS (
         SELECT v_current_run.as_of_date
           FROM analytics.v_current_run
        ), receipt_as_of AS (
         SELECT r.po_line_id,
            sum(r.quantity_received) AS quantity_received,
            min(r.received_date) AS first_receipt_date,
            count(*) AS receipt_count
           FROM (ops.inventory_receipts r
             CROSS JOIN cr cr_1)
          WHERE (r.received_date <= cr_1.as_of_date)
          GROUP BY r.po_line_id
        ), po_as_of AS (
         SELECT po.purchase_order_id,
            po.supplier_id,
            po.store_id,
            po.order_date,
            po.promised_delivery_date,
            min(r.first_receipt_date) AS first_receipt_date,
            (min(r.first_receipt_date) - po.order_date) AS lead_time_days,
            bool_and(((COALESCE(r.quantity_received, (0)::bigint) = pol.quantity_ordered) AND (COALESCE(r.receipt_count, (0)::bigint) = 1) AND (pol.quantity_cancelled = 0))) AS in_full
           FROM (((ops.purchase_orders po
             JOIN ops.purchase_order_lines pol USING (purchase_order_id))
             LEFT JOIN receipt_as_of r USING (po_line_id))
             CROSS JOIN cr cr_1)
          WHERE (po.order_date <= cr_1.as_of_date)
          GROUP BY po.purchase_order_id
        )
 SELECT p.supplier_id,
    p.store_id,
    count(*) FILTER (WHERE (p.first_receipt_date <= cr.as_of_date)) AS received_pos,
    round(avg(p.lead_time_days) FILTER (WHERE (p.first_receipt_date <= cr.as_of_date)), 2) AS mean_lead_time_days,
    round(stddev_samp(p.lead_time_days) FILTER (WHERE (p.first_receipt_date <= cr.as_of_date)), 2) AS std_lead_time_days,
    count(*) FILTER (WHERE ((p.promised_delivery_date >= (cr.as_of_date - 89)) AND (p.promised_delivery_date <= cr.as_of_date))) AS pos_due_90d,
    count(*) FILTER (WHERE (((p.promised_delivery_date >= (cr.as_of_date - 89)) AND (p.promised_delivery_date <= cr.as_of_date)) AND (p.first_receipt_date <= p.promised_delivery_date))) AS on_time_pos_90d,
    count(*) FILTER (WHERE ((p.promised_delivery_date <= cr.as_of_date) AND (p.first_receipt_date IS NULL))) AS overdue_open_pos
   FROM (po_as_of p
     CROSS JOIN cr)
  GROUP BY p.supplier_id, p.store_id;


--
-- Name: v_supplier_performance _RETURN; Type: RULE; Schema: analytics; Owner: -
--

CREATE OR REPLACE VIEW analytics.v_supplier_performance AS
 WITH cr AS (
         SELECT v_current_run.run_id,
            v_current_run.as_of_date
           FROM analytics.v_current_run
        ), receipt_as_of AS (
         SELECT r.po_line_id,
            sum(r.quantity_received) AS quantity_received,
            min(r.received_date) AS first_receipt_date,
            count(*) AS receipt_count
           FROM (ops.inventory_receipts r
             CROSS JOIN cr cr_1)
          WHERE (r.received_date <= cr_1.as_of_date)
          GROUP BY r.po_line_id
        ), po_as_of AS (
         SELECT po.purchase_order_id,
            po.supplier_id,
            po.store_id,
            po.order_date,
            po.promised_delivery_date,
            min(r.first_receipt_date) AS first_receipt_date,
            (min(r.first_receipt_date) - po.order_date) AS lead_time_days,
            bool_and(((COALESCE(r.quantity_received, (0)::bigint) = pol.quantity_ordered) AND (COALESCE(r.receipt_count, (0)::bigint) = 1) AND (pol.quantity_cancelled = 0))) AS in_full
           FROM (((ops.purchase_orders po
             JOIN ops.purchase_order_lines pol USING (purchase_order_id))
             LEFT JOIN receipt_as_of r USING (po_line_id))
             CROSS JOIN cr cr_1)
          WHERE (po.order_date <= cr_1.as_of_date)
          GROUP BY po.purchase_order_id
        ), po_stats AS (
         SELECT p.supplier_id,
            count(*) FILTER (WHERE ((p.promised_delivery_date >= (cr_1.as_of_date - 89)) AND (p.promised_delivery_date <= cr_1.as_of_date))) AS pos_due_90d,
            count(*) FILTER (WHERE (((p.promised_delivery_date >= (cr_1.as_of_date - 89)) AND (p.promised_delivery_date <= cr_1.as_of_date)) AND (p.first_receipt_date <= p.promised_delivery_date))) AS on_time_pos_90d,
            count(*) FILTER (WHERE (((p.promised_delivery_date >= (cr_1.as_of_date - 89)) AND (p.promised_delivery_date <= cr_1.as_of_date)) AND p.in_full)) AS in_full_pos_90d,
            avg(p.lead_time_days) FILTER (WHERE (p.first_receipt_date > (cr_1.as_of_date - 180))) AS mean_lead_time_days,
            stddev_samp(p.lead_time_days) FILTER (WHERE (p.first_receipt_date > (cr_1.as_of_date - 180))) AS std_lead_time_days,
            percentile_cont((0.9)::double precision) WITHIN GROUP (ORDER BY ((p.lead_time_days)::double precision)) FILTER (WHERE (p.first_receipt_date > (cr_1.as_of_date - 180))) AS p90_lead_time_days,
            count(*) FILTER (WHERE ((p.first_receipt_date IS NULL) AND (p.promised_delivery_date <= cr_1.as_of_date))) AS overdue_open_pos
           FROM (po_as_of p
             CROSS JOIN cr cr_1)
          GROUP BY p.supplier_id
        ), exposure AS (
         SELECT r.supplier_id,
            count(*) FILTER (WHERE (r.risk_tier = ANY (ARRAY['critical'::analytics.risk_tier, 'high'::analytics.risk_tier]))) AS at_risk_positions,
            sum(r.margin_at_risk_usd) AS margin_at_risk_usd
           FROM (analytics.inventory_risk_snapshots r
             JOIN cr cr_1 ON ((r.run_id = cr_1.run_id)))
          GROUP BY r.supplier_id
        )
 SELECT s.supplier_id,
    s.supplier_code,
    s.supplier_name,
    c.category_name,
    ps.pos_due_90d,
    round(((ps.on_time_pos_90d)::numeric / (NULLIF(ps.pos_due_90d, 0))::numeric), 4) AS on_time_rate,
    round(((ps.in_full_pos_90d)::numeric / (NULLIF(ps.pos_due_90d, 0))::numeric), 4) AS in_full_rate,
    round(ps.mean_lead_time_days, 2) AS mean_lead_time_days,
    round(ps.std_lead_time_days, 2) AS std_lead_time_days,
    round((ps.p90_lead_time_days)::numeric, 1) AS p90_lead_time_days,
    round((ps.std_lead_time_days / NULLIF(ps.mean_lead_time_days, (0)::numeric)), 4) AS lead_time_cv,
    ps.overdue_open_pos,
    COALESCE(e.at_risk_positions, (0)::bigint) AS at_risk_positions,
    COALESCE(e.margin_at_risk_usd, (0)::numeric) AS margin_at_risk_usd,
    (((((ps.on_time_pos_90d)::numeric / (NULLIF(ps.pos_due_90d, 0))::numeric) < 0.80) OR ((ps.std_lead_time_days / NULLIF(ps.mean_lead_time_days, (0)::numeric)) > 0.35)) AND (COALESCE(e.at_risk_positions, (0)::bigint) >= 1)) AS review_flag,
    rank() OVER (ORDER BY ((ps.on_time_pos_90d)::numeric / (NULLIF(ps.pos_due_90d, 0))::numeric)) AS reliability_rank
   FROM ((((ops.suppliers s
     CROSS JOIN cr)
     JOIN ops.product_categories c ON ((c.category_id = s.primary_category_id)))
     LEFT JOIN po_stats ps ON ((ps.supplier_id = s.supplier_id)))
     LEFT JOIN exposure e ON ((e.supplier_id = s.supplier_id)));


--
-- Name: analytics_runs analytics_runs_as_of_date_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.analytics_runs
    ADD CONSTRAINT analytics_runs_as_of_date_fkey FOREIGN KEY (as_of_date) REFERENCES ops.calendar(calendar_date);


--
-- Name: demand_forecast_daily demand_forecast_daily_promotion_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.demand_forecast_daily
    ADD CONSTRAINT demand_forecast_daily_promotion_id_fkey FOREIGN KEY (promotion_id) REFERENCES ops.promotions(promotion_id);


--
-- Name: demand_forecast_daily demand_forecast_daily_run_id_store_id_product_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.demand_forecast_daily
    ADD CONSTRAINT demand_forecast_daily_run_id_store_id_product_id_fkey FOREIGN KEY (run_id, store_id, product_id) REFERENCES analytics.demand_forecasts(run_id, store_id, product_id) ON DELETE CASCADE;


--
-- Name: demand_forecast_daily demand_forecast_daily_target_date_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.demand_forecast_daily
    ADD CONSTRAINT demand_forecast_daily_target_date_fkey FOREIGN KEY (target_date) REFERENCES ops.calendar(calendar_date);


--
-- Name: demand_forecasts demand_forecasts_product_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.demand_forecasts
    ADD CONSTRAINT demand_forecasts_product_id_fkey FOREIGN KEY (product_id) REFERENCES ops.products(product_id);


--
-- Name: demand_forecasts demand_forecasts_run_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.demand_forecasts
    ADD CONSTRAINT demand_forecasts_run_id_fkey FOREIGN KEY (run_id) REFERENCES analytics.analytics_runs(run_id) ON DELETE CASCADE;


--
-- Name: demand_forecasts demand_forecasts_store_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.demand_forecasts
    ADD CONSTRAINT demand_forecasts_store_id_fkey FOREIGN KEY (store_id) REFERENCES ops.stores(store_id);


--
-- Name: forecast_evaluations forecast_evaluations_run_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.forecast_evaluations
    ADD CONSTRAINT forecast_evaluations_run_id_fkey FOREIGN KEY (run_id) REFERENCES analytics.analytics_runs(run_id) ON DELETE CASCADE;


--
-- Name: inventory_risk_snapshots inventory_risk_snapshots_next_receipt_po_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.inventory_risk_snapshots
    ADD CONSTRAINT inventory_risk_snapshots_next_receipt_po_id_fkey FOREIGN KEY (next_receipt_po_id) REFERENCES ops.purchase_orders(purchase_order_id);


--
-- Name: inventory_risk_snapshots inventory_risk_snapshots_run_id_store_id_product_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.inventory_risk_snapshots
    ADD CONSTRAINT inventory_risk_snapshots_run_id_store_id_product_id_fkey FOREIGN KEY (run_id, store_id, product_id) REFERENCES analytics.demand_forecasts(run_id, store_id, product_id) ON DELETE CASCADE;


--
-- Name: inventory_risk_snapshots inventory_risk_snapshots_run_id_supplier_id_store_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.inventory_risk_snapshots
    ADD CONSTRAINT inventory_risk_snapshots_run_id_supplier_id_store_id_fkey FOREIGN KEY (run_id, supplier_id, store_id) REFERENCES analytics.supplier_lane_estimates(run_id, supplier_id, store_id);


--
-- Name: inventory_risk_snapshots inventory_risk_snapshots_supplier_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.inventory_risk_snapshots
    ADD CONSTRAINT inventory_risk_snapshots_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES ops.suppliers(supplier_id);


--
-- Name: replenishment_recommendations replenishment_recommendations_related_purchase_order_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.replenishment_recommendations
    ADD CONSTRAINT replenishment_recommendations_related_purchase_order_id_fkey FOREIGN KEY (related_purchase_order_id) REFERENCES ops.purchase_orders(purchase_order_id);


--
-- Name: replenishment_recommendations replenishment_recommendations_run_id_store_id_product_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.replenishment_recommendations
    ADD CONSTRAINT replenishment_recommendations_run_id_store_id_product_id_fkey FOREIGN KEY (run_id, store_id, product_id) REFERENCES analytics.inventory_risk_snapshots(run_id, store_id, product_id) ON DELETE CASCADE;


--
-- Name: replenishment_recommendations replenishment_recommendations_supplier_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.replenishment_recommendations
    ADD CONSTRAINT replenishment_recommendations_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES ops.suppliers(supplier_id);


--
-- Name: risk_checkpoints risk_checkpoints_purchase_order_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.risk_checkpoints
    ADD CONSTRAINT risk_checkpoints_purchase_order_id_fkey FOREIGN KEY (purchase_order_id) REFERENCES ops.purchase_orders(purchase_order_id);


--
-- Name: risk_checkpoints risk_checkpoints_run_id_store_id_product_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.risk_checkpoints
    ADD CONSTRAINT risk_checkpoints_run_id_store_id_product_id_fkey FOREIGN KEY (run_id, store_id, product_id) REFERENCES analytics.inventory_risk_snapshots(run_id, store_id, product_id) ON DELETE CASCADE;


--
-- Name: supplier_lane_estimates supplier_lane_estimates_run_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.supplier_lane_estimates
    ADD CONSTRAINT supplier_lane_estimates_run_id_fkey FOREIGN KEY (run_id) REFERENCES analytics.analytics_runs(run_id) ON DELETE CASCADE;


--
-- Name: supplier_lane_estimates supplier_lane_estimates_supplier_id_store_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: -
--

ALTER TABLE ONLY analytics.supplier_lane_estimates
    ADD CONSTRAINT supplier_lane_estimates_supplier_id_store_id_fkey FOREIGN KEY (supplier_id, store_id) REFERENCES ops.supplier_store_lanes(supplier_id, store_id);


--
-- Name: daily_sales daily_sales_product_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.daily_sales
    ADD CONSTRAINT daily_sales_product_id_fkey FOREIGN KEY (product_id) REFERENCES ops.products(product_id);


--
-- Name: daily_sales daily_sales_sales_date_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.daily_sales
    ADD CONSTRAINT daily_sales_sales_date_fkey FOREIGN KEY (sales_date) REFERENCES ops.calendar(calendar_date);


--
-- Name: daily_sales daily_sales_store_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.daily_sales
    ADD CONSTRAINT daily_sales_store_id_fkey FOREIGN KEY (store_id) REFERENCES ops.stores(store_id);


--
-- Name: inventory_adjustments inventory_adjustments_adjustment_date_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.inventory_adjustments
    ADD CONSTRAINT inventory_adjustments_adjustment_date_fkey FOREIGN KEY (adjustment_date) REFERENCES ops.calendar(calendar_date);


--
-- Name: inventory_adjustments inventory_adjustments_product_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.inventory_adjustments
    ADD CONSTRAINT inventory_adjustments_product_id_fkey FOREIGN KEY (product_id) REFERENCES ops.products(product_id);


--
-- Name: inventory_adjustments inventory_adjustments_store_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.inventory_adjustments
    ADD CONSTRAINT inventory_adjustments_store_id_fkey FOREIGN KEY (store_id) REFERENCES ops.stores(store_id);


--
-- Name: inventory_receipts inventory_receipts_po_line_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.inventory_receipts
    ADD CONSTRAINT inventory_receipts_po_line_id_fkey FOREIGN KEY (po_line_id) REFERENCES ops.purchase_order_lines(po_line_id) ON DELETE CASCADE;


--
-- Name: inventory_receipts inventory_receipts_received_date_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.inventory_receipts
    ADD CONSTRAINT inventory_receipts_received_date_fkey FOREIGN KEY (received_date) REFERENCES ops.calendar(calendar_date);


--
-- Name: inventory_snapshots inventory_snapshots_product_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.inventory_snapshots
    ADD CONSTRAINT inventory_snapshots_product_id_fkey FOREIGN KEY (product_id) REFERENCES ops.products(product_id);


--
-- Name: inventory_snapshots inventory_snapshots_snapshot_date_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.inventory_snapshots
    ADD CONSTRAINT inventory_snapshots_snapshot_date_fkey FOREIGN KEY (snapshot_date) REFERENCES ops.calendar(calendar_date);


--
-- Name: inventory_snapshots inventory_snapshots_store_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.inventory_snapshots
    ADD CONSTRAINT inventory_snapshots_store_id_fkey FOREIGN KEY (store_id) REFERENCES ops.stores(store_id);


--
-- Name: product_suppliers product_suppliers_product_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.product_suppliers
    ADD CONSTRAINT product_suppliers_product_id_fkey FOREIGN KEY (product_id) REFERENCES ops.products(product_id);


--
-- Name: product_suppliers product_suppliers_supplier_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.product_suppliers
    ADD CONSTRAINT product_suppliers_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES ops.suppliers(supplier_id);


--
-- Name: products products_category_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.products
    ADD CONSTRAINT products_category_id_fkey FOREIGN KEY (category_id) REFERENCES ops.product_categories(category_id);


--
-- Name: promotion_products promotion_products_product_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.promotion_products
    ADD CONSTRAINT promotion_products_product_id_fkey FOREIGN KEY (product_id) REFERENCES ops.products(product_id);


--
-- Name: promotion_products promotion_products_promotion_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.promotion_products
    ADD CONSTRAINT promotion_products_promotion_id_fkey FOREIGN KEY (promotion_id) REFERENCES ops.promotions(promotion_id) ON DELETE CASCADE;


--
-- Name: promotions promotions_region_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.promotions
    ADD CONSTRAINT promotions_region_id_fkey FOREIGN KEY (region_id) REFERENCES ops.regions(region_id);


--
-- Name: purchase_order_lines purchase_order_lines_product_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.purchase_order_lines
    ADD CONSTRAINT purchase_order_lines_product_id_fkey FOREIGN KEY (product_id) REFERENCES ops.products(product_id);


--
-- Name: purchase_order_lines purchase_order_lines_purchase_order_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.purchase_order_lines
    ADD CONSTRAINT purchase_order_lines_purchase_order_id_fkey FOREIGN KEY (purchase_order_id) REFERENCES ops.purchase_orders(purchase_order_id) ON DELETE CASCADE;


--
-- Name: purchase_orders purchase_orders_order_date_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.purchase_orders
    ADD CONSTRAINT purchase_orders_order_date_fkey FOREIGN KEY (order_date) REFERENCES ops.calendar(calendar_date);


--
-- Name: purchase_orders purchase_orders_store_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.purchase_orders
    ADD CONSTRAINT purchase_orders_store_id_fkey FOREIGN KEY (store_id) REFERENCES ops.stores(store_id);


--
-- Name: purchase_orders purchase_orders_supplier_id_store_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.purchase_orders
    ADD CONSTRAINT purchase_orders_supplier_id_store_id_fkey FOREIGN KEY (supplier_id, store_id) REFERENCES ops.supplier_store_lanes(supplier_id, store_id);


--
-- Name: stores stores_region_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.stores
    ADD CONSTRAINT stores_region_id_fkey FOREIGN KEY (region_id) REFERENCES ops.regions(region_id);


--
-- Name: supplier_store_lanes supplier_store_lanes_store_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.supplier_store_lanes
    ADD CONSTRAINT supplier_store_lanes_store_id_fkey FOREIGN KEY (store_id) REFERENCES ops.stores(store_id);


--
-- Name: supplier_store_lanes supplier_store_lanes_supplier_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.supplier_store_lanes
    ADD CONSTRAINT supplier_store_lanes_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES ops.suppliers(supplier_id);


--
-- Name: suppliers suppliers_primary_category_id_fkey; Type: FK CONSTRAINT; Schema: ops; Owner: -
--

ALTER TABLE ONLY ops.suppliers
    ADD CONSTRAINT suppliers_primary_category_id_fkey FOREIGN KEY (primary_category_id) REFERENCES ops.product_categories(category_id);


--
-- Name: latent_demand latent_demand_demand_date_fkey; Type: FK CONSTRAINT; Schema: sim_truth; Owner: -
--

ALTER TABLE ONLY sim_truth.latent_demand
    ADD CONSTRAINT latent_demand_demand_date_fkey FOREIGN KEY (demand_date) REFERENCES ops.calendar(calendar_date);


--
-- Name: latent_demand latent_demand_product_id_fkey; Type: FK CONSTRAINT; Schema: sim_truth; Owner: -
--

ALTER TABLE ONLY sim_truth.latent_demand
    ADD CONSTRAINT latent_demand_product_id_fkey FOREIGN KEY (product_id) REFERENCES ops.products(product_id);


--
-- Name: latent_demand latent_demand_store_id_fkey; Type: FK CONSTRAINT; Schema: sim_truth; Owner: -
--

ALTER TABLE ONLY sim_truth.latent_demand
    ADD CONSTRAINT latent_demand_store_id_fkey FOREIGN KEY (store_id) REFERENCES ops.stores(store_id);


--
-- PostgreSQL database dump complete
--

\unrestrict stocgainSchemaDump42

