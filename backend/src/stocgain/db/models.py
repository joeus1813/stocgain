"""SQLAlchemy table and ORM mappings matching the four immutable schema revisions."""

from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared metadata for migrations and loader header validation."""


ENUM_VALUES = {
    "ops.adjustment_reason": (
        "shrink",
        "damage",
        "cycle_count_correction",
        "vendor_return",
    ),
    "analytics.run_type": ("current", "backfill"),
    "analytics.run_status": ("running", "succeeded", "failed"),
    "analytics.risk_tier": ("low", "moderate", "high", "critical"),
    "analytics.action_type": ("no_action", "monitor", "reorder", "expedite_po"),
    "analytics.forecast_method": (
        "store_sku",
        "blended",
        "chain_fallback",
        "insufficient_data",
    ),
    "analytics.demand_pattern": (
        "smooth",
        "erratic",
        "intermittent",
        "lumpy",
        "no_demand",
    ),
    "analytics.distribution_family": (
        "normal",
        "negative_binomial",
        "poisson",
        "degenerate",
    ),
    "analytics.checkpoint_type": ("receipt", "window_end"),
    "analytics.lead_time_source": ("lane", "supplier", "contract"),
    "analytics.risk_driver": (
        "currently_out_of_stock",
        "coverage_gap",
        "no_inbound_supply",
        "overdue_po",
        "supplier_unreliable",
        "lead_time_variability",
        "demand_acceleration",
        "high_demand_variability",
        "recent_stockouts",
        "upcoming_promotion",
        "limited_history",
    ),
}


def _enum(name: str, schema: str = "analytics") -> postgresql.ENUM:
    return postgresql.ENUM(
        *ENUM_VALUES[f"{schema}.{name}"], name=name, schema=schema, create_type=False
    )


def _position_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column("run_id", sa.BigInteger, primary_key=True),
        sa.Column("store_id", sa.SmallInteger, primary_key=True),
        sa.Column("product_id", sa.Integer, primary_key=True),
    ]


sa.Table(
    "regions",
    Base.metadata,
    sa.Column("region_id", sa.SmallInteger, primary_key=True),
    sa.Column("region_code", sa.String(4), nullable=False, unique=True),
    sa.Column("region_name", sa.String(40), nullable=False, unique=True),
    sa.CheckConstraint("region_code ~ '^[A-Z]{2}$'"),
    schema="ops",
)

sa.Table(
    "product_categories",
    Base.metadata,
    sa.Column("category_id", sa.SmallInteger, primary_key=True),
    sa.Column("category_code", sa.String(4), nullable=False, unique=True),
    sa.Column("category_name", sa.String(40), nullable=False, unique=True),
    sa.CheckConstraint("category_code ~ '^[A-Z]{2}$'"),
    schema="ops",
)

sa.Table(
    "stores",
    Base.metadata,
    sa.Column("store_id", sa.SmallInteger, primary_key=True),
    sa.Column("store_code", sa.String(4), nullable=False, unique=True),
    sa.Column("store_name", sa.String(60), nullable=False),
    sa.Column("city", sa.String(40), nullable=False),
    sa.Column("state_code", sa.CHAR(2), nullable=False),
    sa.Column(
        "region_id",
        sa.SmallInteger,
        sa.ForeignKey("ops.regions.region_id"),
        nullable=False,
    ),
    sa.Column("opened_date", sa.Date, nullable=False),
    sa.Column("sales_area_sqft", sa.Integer, nullable=False),
    sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    sa.CheckConstraint("store_code ~ '^S[0-9]{2}$'"),
    sa.CheckConstraint("state_code ~ '^[A-Z]{2}$'"),
    sa.CheckConstraint("sales_area_sqft > 0"),
    schema="ops",
)

sa.Index("ix_stores_region_id", Base.metadata.tables["ops.stores"].c["region_id"])

sa.Table(
    "suppliers",
    Base.metadata,
    sa.Column("supplier_id", sa.SmallInteger, primary_key=True),
    sa.Column("supplier_code", sa.String(8), nullable=False, unique=True),
    sa.Column("supplier_name", sa.String(80), nullable=False, unique=True),
    sa.Column(
        "primary_category_id",
        sa.SmallInteger,
        sa.ForeignKey("ops.product_categories.category_id"),
        nullable=False,
    ),
    sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    sa.CheckConstraint("supplier_code ~ '^SUP-[0-9]{3}$'"),
    schema="ops",
)

sa.Index(
    "ix_suppliers_primary_category_id",
    Base.metadata.tables["ops.suppliers"].c["primary_category_id"],
)

sa.Table(
    "products",
    Base.metadata,
    sa.Column("product_id", sa.Integer, primary_key=True),
    sa.Column("sku", sa.String(12), nullable=False, unique=True),
    sa.Column("product_name", sa.String(120), nullable=False),
    sa.Column(
        "category_id",
        sa.SmallInteger,
        sa.ForeignKey("ops.product_categories.category_id"),
        nullable=False,
    ),
    sa.Column("brand_name", sa.String(40), nullable=False),
    sa.Column("unit_of_measure", sa.String(8), nullable=False),
    sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
    sa.Column("unit_cost", sa.Numeric(10, 2), nullable=False),
    sa.Column("introduced_date", sa.Date, nullable=False),
    sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    sa.CheckConstraint("sku ~ '^[A-Z]{2}-[0-9]{5}$'"),
    sa.CheckConstraint(
        "unit_of_measure IN ('each','pack','bag','gallon','roll','box')"
    ),
    sa.CheckConstraint("unit_price > 0"),
    sa.CheckConstraint("unit_cost > 0"),
    sa.CheckConstraint("unit_price > unit_cost"),
    schema="ops",
)

sa.Index(
    "ix_products_category_id", Base.metadata.tables["ops.products"].c["category_id"]
)

sa.Table(
    "product_suppliers",
    Base.metadata,
    sa.Column(
        "product_id",
        sa.Integer,
        sa.ForeignKey("ops.products.product_id"),
        primary_key=True,
    ),
    sa.Column(
        "supplier_id",
        sa.SmallInteger,
        sa.ForeignKey("ops.suppliers.supplier_id"),
        primary_key=True,
    ),
    sa.Column("is_primary", sa.Boolean, nullable=False),
    sa.Column("case_pack_qty", sa.Integer, nullable=False),
    sa.Column("min_order_qty", sa.Integer, nullable=False),
    sa.CheckConstraint("case_pack_qty > 0"),
    sa.CheckConstraint("min_order_qty > 0"),
    sa.CheckConstraint("min_order_qty % case_pack_qty = 0"),
    schema="ops",
)

sa.Index(
    "ix_product_suppliers_supplier_id",
    Base.metadata.tables["ops.product_suppliers"].c["supplier_id"],
)

sa.Index(
    "ux_product_suppliers_one_primary",
    Base.metadata.tables["ops.product_suppliers"].c["product_id"],
    unique=True,
    postgresql_where=sa.text("is_primary"),
)

sa.Table(
    "supplier_store_lanes",
    Base.metadata,
    sa.Column(
        "supplier_id",
        sa.SmallInteger,
        sa.ForeignKey("ops.suppliers.supplier_id"),
        primary_key=True,
    ),
    sa.Column(
        "store_id",
        sa.SmallInteger,
        sa.ForeignKey("ops.stores.store_id"),
        primary_key=True,
    ),
    sa.Column("contract_lead_time_days", sa.SmallInteger, nullable=False),
    sa.Column("review_weekday", sa.SmallInteger, nullable=False),
    sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    sa.CheckConstraint("contract_lead_time_days BETWEEN 1 AND 60"),
    sa.CheckConstraint("review_weekday BETWEEN 1 AND 7"),
    schema="ops",
)

sa.Index(
    "ix_lanes_store_id", Base.metadata.tables["ops.supplier_store_lanes"].c["store_id"]
)

sa.Table(
    "calendar",
    Base.metadata,
    sa.Column("calendar_date", sa.Date, primary_key=True),
    sa.Column("iso_year", sa.SmallInteger, nullable=False),
    sa.Column("iso_week", sa.SmallInteger, nullable=False),
    sa.Column("iso_day_of_week", sa.SmallInteger, nullable=False),
    sa.Column("day_name", sa.String(9), nullable=False),
    sa.Column("month", sa.SmallInteger, nullable=False),
    sa.Column("month_name", sa.String(9), nullable=False),
    sa.Column("quarter", sa.SmallInteger, nullable=False),
    sa.Column("week_start_date", sa.Date, nullable=False),
    sa.Column("is_weekend", sa.Boolean, nullable=False),
    sa.Column("holiday_name", sa.String(40)),
    sa.CheckConstraint("iso_week BETWEEN 1 AND 53"),
    sa.CheckConstraint("iso_day_of_week BETWEEN 1 AND 7"),
    sa.CheckConstraint("month BETWEEN 1 AND 12"),
    sa.CheckConstraint("quarter BETWEEN 1 AND 4"),
    schema="ops",
)

sa.Index(
    "ix_calendar_week_start_date",
    Base.metadata.tables["ops.calendar"].c["week_start_date"],
)

sa.Table(
    "promotions",
    Base.metadata,
    sa.Column("promotion_id", sa.Integer, primary_key=True),
    sa.Column("promotion_code", sa.String(12), nullable=False, unique=True),
    sa.Column("promotion_name", sa.String(80), nullable=False),
    sa.Column("region_id", sa.SmallInteger, sa.ForeignKey("ops.regions.region_id")),
    sa.Column("start_date", sa.Date, nullable=False),
    sa.Column("end_date", sa.Date, nullable=False),
    sa.Column("discount_rate", sa.Numeric(4, 3), nullable=False),
    sa.Column("planned_lift", sa.Numeric(4, 2), nullable=False),
    sa.CheckConstraint("promotion_code ~ '^PRM-[0-9]{4}$'"),
    sa.CheckConstraint("end_date >= start_date"),
    sa.CheckConstraint("end_date - start_date <= 30"),
    sa.CheckConstraint("discount_rate > 0 AND discount_rate < 0.6"),
    sa.CheckConstraint("planned_lift BETWEEN 1.00 AND 3.00"),
    schema="ops",
)

sa.Index(
    "ix_promotions_dates",
    Base.metadata.tables["ops.promotions"].c["start_date"],
    Base.metadata.tables["ops.promotions"].c["end_date"],
)

sa.Table(
    "promotion_products",
    Base.metadata,
    sa.Column(
        "promotion_id",
        sa.Integer,
        sa.ForeignKey("ops.promotions.promotion_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.Column(
        "product_id",
        sa.Integer,
        sa.ForeignKey("ops.products.product_id"),
        primary_key=True,
    ),
    schema="ops",
)

sa.Index(
    "ix_promotion_products_product_id",
    Base.metadata.tables["ops.promotion_products"].c["product_id"],
)

sa.Table(
    "dataset_manifest",
    Base.metadata,
    sa.Column("dataset_id", sa.SmallInteger, primary_key=True),
    sa.Column("data_origin", sa.String(20), nullable=False),
    sa.Column("generator_version", sa.String(20), nullable=False),
    sa.Column("preset", sa.String(20), nullable=False),
    sa.Column("seed", sa.Integer, nullable=False),
    sa.Column("history_start_date", sa.Date, nullable=False),
    sa.Column("history_end_date", sa.Date, nullable=False),
    sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column(
        "loaded_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.Column("row_counts", postgresql.JSONB, nullable=False),
    sa.Column("content_checksum", sa.CHAR(64), nullable=False),
    sa.Column("notes", sa.Text, nullable=False),
    sa.CheckConstraint("dataset_id = 1"),
    sa.CheckConstraint("data_origin IN ('synthetic','public')"),
    sa.CheckConstraint("preset IN ('small','standard','large')"),
    sa.CheckConstraint("history_end_date > history_start_date"),
    schema="ops",
)

sa.Table(
    "daily_sales",
    Base.metadata,
    sa.Column(
        "store_id",
        sa.SmallInteger,
        sa.ForeignKey("ops.stores.store_id"),
        primary_key=True,
    ),
    sa.Column(
        "product_id",
        sa.Integer,
        sa.ForeignKey("ops.products.product_id"),
        primary_key=True,
    ),
    sa.Column(
        "sales_date",
        sa.Date,
        sa.ForeignKey("ops.calendar.calendar_date"),
        primary_key=True,
    ),
    sa.Column("units_sold", sa.Integer, nullable=False),
    sa.Column("net_sales_amount", sa.Numeric(12, 2), nullable=False),
    sa.Column("cogs_amount", sa.Numeric(12, 2), nullable=False),
    sa.CheckConstraint("units_sold >= 0"),
    sa.CheckConstraint("net_sales_amount >= 0"),
    sa.CheckConstraint("cogs_amount >= 0"),
    sa.CheckConstraint("units_sold > 0 OR (net_sales_amount = 0 AND cogs_amount = 0)"),
    schema="ops",
)

sa.Index(
    "brin_daily_sales_sales_date",
    Base.metadata.tables["ops.daily_sales"].c["sales_date"],
    postgresql_using="brin",
)

sa.Table(
    "inventory_snapshots",
    Base.metadata,
    sa.Column(
        "store_id",
        sa.SmallInteger,
        sa.ForeignKey("ops.stores.store_id"),
        primary_key=True,
    ),
    sa.Column(
        "product_id",
        sa.Integer,
        sa.ForeignKey("ops.products.product_id"),
        primary_key=True,
    ),
    sa.Column(
        "snapshot_date",
        sa.Date,
        sa.ForeignKey("ops.calendar.calendar_date"),
        primary_key=True,
    ),
    sa.Column("opening_on_hand", sa.Integer, nullable=False),
    sa.Column("closing_on_hand", sa.Integer, nullable=False),
    sa.CheckConstraint("opening_on_hand >= 0"),
    sa.CheckConstraint("closing_on_hand >= 0"),
    schema="ops",
)

sa.Index(
    "ix_inventory_snapshots_date",
    Base.metadata.tables["ops.inventory_snapshots"].c["snapshot_date"],
)

sa.Table(
    "purchase_orders",
    Base.metadata,
    sa.Column("purchase_order_id", sa.Integer, primary_key=True),
    sa.Column("po_number", sa.String(12), nullable=False, unique=True),
    sa.Column("supplier_id", sa.SmallInteger, nullable=False),
    sa.Column(
        "store_id",
        sa.SmallInteger,
        sa.ForeignKey("ops.stores.store_id"),
        nullable=False,
    ),
    sa.Column(
        "order_date",
        sa.Date,
        sa.ForeignKey("ops.calendar.calendar_date"),
        nullable=False,
    ),
    sa.Column("promised_delivery_date", sa.Date, nullable=False),
    sa.ForeignKeyConstraint(
        ["supplier_id", "store_id"],
        ["ops.supplier_store_lanes.supplier_id", "ops.supplier_store_lanes.store_id"],
    ),
    sa.CheckConstraint("po_number ~ '^PO-[0-9]{6}$'"),
    sa.CheckConstraint("promised_delivery_date > order_date"),
    schema="ops",
)

sa.Index(
    "ix_po_store_order_date",
    Base.metadata.tables["ops.purchase_orders"].c["store_id"],
    Base.metadata.tables["ops.purchase_orders"].c["order_date"],
)

sa.Index(
    "ix_po_supplier_promised",
    Base.metadata.tables["ops.purchase_orders"].c["supplier_id"],
    Base.metadata.tables["ops.purchase_orders"].c["promised_delivery_date"],
)

sa.Table(
    "purchase_order_lines",
    Base.metadata,
    sa.Column("po_line_id", sa.Integer, primary_key=True),
    sa.Column(
        "purchase_order_id",
        sa.Integer,
        sa.ForeignKey("ops.purchase_orders.purchase_order_id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("line_number", sa.SmallInteger, nullable=False),
    sa.Column(
        "product_id",
        sa.Integer,
        sa.ForeignKey("ops.products.product_id"),
        nullable=False,
    ),
    sa.Column("quantity_ordered", sa.Integer, nullable=False),
    sa.Column("quantity_cancelled", sa.Integer, nullable=False, server_default="0"),
    sa.Column("unit_cost", sa.Numeric(10, 2), nullable=False),
    sa.UniqueConstraint("purchase_order_id", "line_number"),
    sa.UniqueConstraint("purchase_order_id", "product_id"),
    sa.CheckConstraint("line_number >= 1"),
    sa.CheckConstraint("quantity_ordered > 0"),
    sa.CheckConstraint(
        "quantity_cancelled >= 0 AND quantity_cancelled <= quantity_ordered"
    ),
    sa.CheckConstraint("unit_cost > 0"),
    schema="ops",
)

sa.Index(
    "ix_po_lines_product_id",
    Base.metadata.tables["ops.purchase_order_lines"].c["product_id"],
)

sa.Table(
    "inventory_receipts",
    Base.metadata,
    sa.Column("receipt_id", sa.Integer, primary_key=True),
    sa.Column(
        "po_line_id",
        sa.Integer,
        sa.ForeignKey("ops.purchase_order_lines.po_line_id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column(
        "received_date",
        sa.Date,
        sa.ForeignKey("ops.calendar.calendar_date"),
        nullable=False,
    ),
    sa.Column("quantity_received", sa.Integer, nullable=False),
    sa.UniqueConstraint("po_line_id", "received_date"),
    sa.CheckConstraint("quantity_received > 0"),
    schema="ops",
)

sa.Index(
    "ix_receipts_received_date",
    Base.metadata.tables["ops.inventory_receipts"].c["received_date"],
)

sa.Table(
    "inventory_adjustments",
    Base.metadata,
    sa.Column("adjustment_id", sa.Integer, primary_key=True),
    sa.Column(
        "store_id",
        sa.SmallInteger,
        sa.ForeignKey("ops.stores.store_id"),
        nullable=False,
    ),
    sa.Column(
        "product_id",
        sa.Integer,
        sa.ForeignKey("ops.products.product_id"),
        nullable=False,
    ),
    sa.Column(
        "adjustment_date",
        sa.Date,
        sa.ForeignKey("ops.calendar.calendar_date"),
        nullable=False,
    ),
    sa.Column("quantity_delta", sa.Integer, nullable=False),
    sa.Column(
        "reason_code",
        postgresql.ENUM(name="adjustment_reason", schema="ops", create_type=False),
        nullable=False,
    ),
    sa.UniqueConstraint("store_id", "product_id", "adjustment_date", "reason_code"),
    sa.CheckConstraint("quantity_delta <> 0"),
    sa.CheckConstraint("reason_code = 'cycle_count_correction' OR quantity_delta < 0"),
    schema="ops",
)

sa.Table(
    "analytics_runs",
    Base.metadata,
    sa.Column("run_id", sa.BigInteger, sa.Identity(always=True), primary_key=True),
    sa.Column("run_type", _enum("run_type"), nullable=False),
    sa.Column(
        "as_of_date",
        sa.Date,
        sa.ForeignKey("ops.calendar.calendar_date"),
        nullable=False,
    ),
    sa.Column("status", _enum("run_status"), nullable=False, server_default="running"),
    sa.Column("model_version", sa.String(40), nullable=False),
    sa.Column("config", postgresql.JSONB, nullable=False),
    sa.Column("dataset_checksum", sa.CHAR(64), nullable=False),
    sa.Column(
        "started_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.Column("completed_at", sa.DateTime(timezone=True)),
    sa.Column("step_timings", postgresql.JSONB),
    sa.Column("positions_scored", sa.Integer),
    sa.Column("error_message", sa.Text),
    sa.CheckConstraint("status <> 'succeeded' OR completed_at IS NOT NULL"),
    sa.CheckConstraint("positions_scored >= 0"),
    sa.CheckConstraint("status <> 'failed' OR error_message IS NOT NULL"),
    schema="analytics",
)

sa.Index(
    "ix_runs_status_type_asof",
    Base.metadata.tables["analytics.analytics_runs"].c["status"],
    Base.metadata.tables["analytics.analytics_runs"].c["run_type"],
    sa.text("as_of_date DESC"),
    sa.text("completed_at DESC"),
)

sa.Table(
    "demand_forecasts",
    Base.metadata,
    sa.Column(
        "run_id",
        sa.BigInteger,
        sa.ForeignKey("analytics.analytics_runs.run_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.Column(
        "store_id",
        sa.SmallInteger,
        sa.ForeignKey("ops.stores.store_id"),
        primary_key=True,
    ),
    sa.Column(
        "product_id",
        sa.Integer,
        sa.ForeignKey("ops.products.product_id"),
        primary_key=True,
    ),
    sa.Column("method", _enum("forecast_method"), nullable=False),
    sa.Column("demand_pattern", _enum("demand_pattern"), nullable=False),
    sa.Column("lookback_days", sa.SmallInteger, nullable=False),
    sa.Column("clean_days", sa.SmallInteger, nullable=False),
    sa.Column("censored_days", sa.SmallInteger, nullable=False),
    sa.Column("promo_days", sa.SmallInteger, nullable=False),
    sa.Column("base_daily_demand", sa.Numeric(12, 4), nullable=False),
    sa.Column("daily_demand_std", sa.Numeric(12, 4), nullable=False),
    sa.Column("observed_demand_cv", sa.Numeric(8, 4)),
    sa.Column("demand_trend_ratio", sa.Numeric(8, 4)),
    sa.Column("adi", sa.Numeric(8, 3)),
    sa.Column("cv_squared", sa.Numeric(8, 4)),
    sa.Column("forecast_7d_units", sa.Numeric(12, 2), nullable=False),
    sa.Column("forecast_14d_units", sa.Numeric(12, 2), nullable=False),
    sa.Column("forecast_28d_units", sa.Numeric(12, 2), nullable=False),
    sa.Column("forecast_7d_std_units", sa.Numeric(12, 2), nullable=False),
    sa.Column("forecast_14d_std_units", sa.Numeric(12, 2), nullable=False),
    sa.Column("forecast_28d_std_units", sa.Numeric(12, 2), nullable=False),
    sa.CheckConstraint("lookback_days > 0"),
    sa.CheckConstraint("clean_days >= 0"),
    sa.CheckConstraint("censored_days >= 0"),
    sa.CheckConstraint("promo_days >= 0"),
    sa.CheckConstraint("base_daily_demand >= 0"),
    sa.CheckConstraint("daily_demand_std >= 0"),
    sa.CheckConstraint("forecast_7d_units >= 0"),
    sa.CheckConstraint("forecast_14d_units >= forecast_7d_units"),
    sa.CheckConstraint("forecast_28d_units >= forecast_14d_units"),
    schema="analytics",
)

sa.Table(
    "demand_forecast_daily",
    Base.metadata,
    *_position_columns(),
    sa.Column(
        "target_date",
        sa.Date,
        sa.ForeignKey("ops.calendar.calendar_date"),
        primary_key=True,
    ),
    sa.Column("horizon_day", sa.SmallInteger, nullable=False),
    sa.Column("forecast_units", sa.Numeric(12, 4), nullable=False),
    sa.Column("dow_index", sa.Numeric(6, 4), nullable=False),
    sa.Column("promo_multiplier", sa.Numeric(4, 2), nullable=False),
    sa.Column("promotion_id", sa.Integer, sa.ForeignKey("ops.promotions.promotion_id")),
    sa.ForeignKeyConstraint(
        ["run_id", "store_id", "product_id"],
        [
            "analytics.demand_forecasts.run_id",
            "analytics.demand_forecasts.store_id",
            "analytics.demand_forecasts.product_id",
        ],
        ondelete="CASCADE",
    ),
    sa.CheckConstraint("horizon_day BETWEEN 1 AND 42"),
    sa.CheckConstraint("forecast_units >= 0"),
    sa.CheckConstraint("dow_index > 0"),
    sa.CheckConstraint("promo_multiplier >= 1.00"),
    schema="analytics",
)

sa.Table(
    "forecast_evaluations",
    Base.metadata,
    sa.Column(
        "evaluation_id", sa.BigInteger, sa.Identity(always=True), primary_key=True
    ),
    sa.Column(
        "run_id",
        sa.BigInteger,
        sa.ForeignKey("analytics.analytics_runs.run_id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("model_name", sa.String(40), nullable=False),
    sa.Column("evaluation_basis", sa.String(20), nullable=False),
    sa.Column("segment_type", sa.String(20), nullable=False),
    sa.Column("segment_value", sa.String(20), nullable=False),
    sa.Column("n_origins", sa.SmallInteger, nullable=False),
    sa.Column("n_observations", sa.Integer, nullable=False),
    sa.Column("actual_units", sa.Numeric(14, 2), nullable=False),
    sa.Column("forecast_units", sa.Numeric(14, 2), nullable=False),
    sa.Column("abs_error_units", sa.Numeric(14, 2), nullable=False),
    sa.Column("mae", sa.Numeric(12, 4)),
    sa.Column("wape", sa.Numeric(8, 4)),
    sa.Column("bias_rate", sa.Numeric(8, 4)),
    sa.Column("first_origin_date", sa.Date, nullable=False),
    sa.Column("last_origin_date", sa.Date, nullable=False),
    sa.UniqueConstraint(
        "run_id", "model_name", "evaluation_basis", "segment_type", "segment_value"
    ),
    sa.CheckConstraint(
        "model_name IN ('stocgain_v1','naive_28d_mean','seasonal_naive_7d')"
    ),
    sa.CheckConstraint("evaluation_basis IN ('observed_in_stock','simulated_latent')"),
    sa.CheckConstraint(
        "segment_type IN ('overall','horizon_bucket','velocity_class','demand_pattern')"
    ),
    sa.CheckConstraint("n_origins > 0"),
    sa.CheckConstraint("n_observations >= 0"),
    schema="analytics",
)

sa.Table(
    "supplier_lane_estimates",
    Base.metadata,
    sa.Column(
        "run_id",
        sa.BigInteger,
        sa.ForeignKey("analytics.analytics_runs.run_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.Column("supplier_id", sa.SmallInteger, primary_key=True),
    sa.Column("store_id", sa.SmallInteger, primary_key=True),
    sa.Column("lead_time_source", _enum("lead_time_source"), nullable=False),
    sa.Column("n_received_pos", sa.Integer, nullable=False),
    sa.Column("mean_lead_time_days", sa.Numeric(6, 2), nullable=False),
    sa.Column("std_lead_time_days", sa.Numeric(6, 2), nullable=False),
    sa.Column("mean_delay_days", sa.Numeric(6, 2), nullable=False),
    sa.Column("std_delay_days", sa.Numeric(6, 2), nullable=False),
    sa.Column("mean_delay_when_late_days", sa.Numeric(6, 2), nullable=False),
    sa.Column("on_time_rate", sa.Numeric(5, 4)),
    sa.ForeignKeyConstraint(
        ["supplier_id", "store_id"],
        ["ops.supplier_store_lanes.supplier_id", "ops.supplier_store_lanes.store_id"],
    ),
    sa.CheckConstraint("n_received_pos >= 0"),
    sa.CheckConstraint("mean_lead_time_days > 0"),
    sa.CheckConstraint("std_lead_time_days >= 0"),
    sa.CheckConstraint("std_delay_days >= 0"),
    sa.CheckConstraint("mean_delay_when_late_days >= 0"),
    sa.CheckConstraint("on_time_rate BETWEEN 0 AND 1"),
    schema="analytics",
)

sa.Table(
    "inventory_risk_snapshots",
    Base.metadata,
    *_position_columns(),
    sa.Column(
        "supplier_id",
        sa.SmallInteger,
        sa.ForeignKey("ops.suppliers.supplier_id"),
        nullable=False,
    ),
    sa.Column("on_hand_units", sa.Integer, nullable=False),
    sa.Column("on_order_units", sa.Integer, nullable=False),
    sa.Column("inventory_position_units", sa.Integer, nullable=False),
    sa.Column("open_po_count", sa.SmallInteger, nullable=False),
    sa.Column("next_receipt_date", sa.Date),
    sa.Column("next_receipt_units", sa.Integer),
    sa.Column(
        "next_receipt_po_id",
        sa.Integer,
        sa.ForeignKey("ops.purchase_orders.purchase_order_id"),
    ),
    sa.Column(
        "next_receipt_overdue", sa.Boolean, nullable=False, server_default=sa.false()
    ),
    sa.Column("avg_daily_demand_units", sa.Numeric(12, 4), nullable=False),
    sa.Column("daily_demand_std_units", sa.Numeric(12, 4), nullable=False),
    sa.Column("days_of_cover", sa.Numeric(8, 1)),
    sa.Column("lead_time_mean_days", sa.Numeric(6, 2), nullable=False),
    sa.Column("lead_time_std_days", sa.Numeric(6, 2), nullable=False),
    sa.Column("protection_window_days", sa.Numeric(6, 2), nullable=False),
    sa.Column("lead_time_demand_mean_units", sa.Numeric(12, 2), nullable=False),
    sa.Column("lead_time_demand_std_units", sa.Numeric(12, 2), nullable=False),
    sa.Column("distribution_family", _enum("distribution_family"), nullable=False),
    sa.Column("service_level", sa.Numeric(5, 4), nullable=False),
    sa.Column("safety_stock_units", sa.Numeric(12, 2), nullable=False),
    sa.Column("reorder_point_units", sa.Integer, nullable=False),
    sa.Column("order_up_to_units", sa.Integer, nullable=False),
    sa.Column("below_reorder_point", sa.Boolean, nullable=False),
    sa.Column("binding_checkpoint_type", _enum("checkpoint_type"), nullable=False),
    sa.Column("binding_window_days", sa.Numeric(6, 2), nullable=False),
    sa.Column("binding_supply_units", sa.Integer, nullable=False),
    sa.Column("binding_demand_mean_units", sa.Numeric(12, 2), nullable=False),
    sa.Column("binding_demand_std_units", sa.Numeric(12, 2), nullable=False),
    sa.Column("stockout_probability", sa.Numeric(5, 4), nullable=False),
    sa.Column("expected_shortage_units", sa.Numeric(12, 2), nullable=False),
    sa.Column("lost_sale_rate", sa.Numeric(4, 3), nullable=False),
    sa.Column("expected_lost_units", sa.Numeric(12, 2), nullable=False),
    sa.Column("revenue_at_risk_usd", sa.Numeric(12, 2), nullable=False),
    sa.Column("margin_at_risk_usd", sa.Numeric(12, 2), nullable=False),
    sa.Column("projected_stockout_date", sa.Date),
    sa.Column("days_until_projected_stockout", sa.SmallInteger),
    sa.Column("currently_out_of_stock", sa.Boolean, nullable=False),
    sa.Column("recent_censored_days", sa.SmallInteger, nullable=False),
    sa.Column("risk_tier", _enum("risk_tier"), nullable=False),
    sa.Column(
        "risk_drivers",
        postgresql.ARRAY(_enum("risk_driver")),
        nullable=False,
        server_default="{}",
    ),
    sa.Column("explanation", sa.Text, nullable=False),
    sa.ForeignKeyConstraint(
        ["run_id", "store_id", "product_id"],
        [
            "analytics.demand_forecasts.run_id",
            "analytics.demand_forecasts.store_id",
            "analytics.demand_forecasts.product_id",
        ],
        ondelete="CASCADE",
    ),
    sa.ForeignKeyConstraint(
        ["run_id", "supplier_id", "store_id"],
        [
            "analytics.supplier_lane_estimates.run_id",
            "analytics.supplier_lane_estimates.supplier_id",
            "analytics.supplier_lane_estimates.store_id",
        ],
    ),
    sa.CheckConstraint("on_hand_units >= 0"),
    sa.CheckConstraint("on_order_units >= 0"),
    sa.CheckConstraint("inventory_position_units = on_hand_units + on_order_units"),
    sa.CheckConstraint("open_po_count >= 0"),
    sa.CheckConstraint("next_receipt_units > 0"),
    sa.CheckConstraint("service_level BETWEEN 0.5 AND 0.9999"),
    sa.CheckConstraint("safety_stock_units >= 0"),
    sa.CheckConstraint("reorder_point_units >= 0"),
    sa.CheckConstraint("order_up_to_units >= reorder_point_units"),
    sa.CheckConstraint("stockout_probability BETWEEN 0 AND 1"),
    sa.CheckConstraint("expected_shortage_units >= 0"),
    sa.CheckConstraint("expected_lost_units >= 0"),
    sa.CheckConstraint("revenue_at_risk_usd >= 0"),
    sa.CheckConstraint("margin_at_risk_usd >= 0"),
    sa.CheckConstraint("days_until_projected_stockout BETWEEN 1 AND 42"),
    schema="analytics",
)

sa.Index(
    "ix_risk_run_tier_margin",
    Base.metadata.tables["analytics.inventory_risk_snapshots"].c["run_id"],
    sa.text("risk_tier DESC"),
    sa.text("margin_at_risk_usd DESC"),
)

sa.Index(
    "ix_risk_run_store",
    Base.metadata.tables["analytics.inventory_risk_snapshots"].c["run_id"],
    Base.metadata.tables["analytics.inventory_risk_snapshots"].c["store_id"],
)

sa.Index(
    "ix_risk_run_supplier",
    Base.metadata.tables["analytics.inventory_risk_snapshots"].c["run_id"],
    Base.metadata.tables["analytics.inventory_risk_snapshots"].c["supplier_id"],
)

sa.Index(
    "ix_risk_run_product",
    Base.metadata.tables["analytics.inventory_risk_snapshots"].c["run_id"],
    Base.metadata.tables["analytics.inventory_risk_snapshots"].c["product_id"],
)

sa.Table(
    "risk_checkpoints",
    Base.metadata,
    *_position_columns(),
    sa.Column("checkpoint_seq", sa.SmallInteger, primary_key=True),
    sa.Column("checkpoint_type", _enum("checkpoint_type"), nullable=False),
    sa.Column(
        "purchase_order_id",
        sa.Integer,
        sa.ForeignKey("ops.purchase_orders.purchase_order_id"),
    ),
    sa.Column("arrival_date", sa.Date),
    sa.Column("window_days", sa.Numeric(6, 2), nullable=False),
    sa.Column("window_std_days", sa.Numeric(6, 2), nullable=False),
    sa.Column("supply_units", sa.Integer, nullable=False),
    sa.Column("demand_mean_units", sa.Numeric(12, 2), nullable=False),
    sa.Column("demand_std_units", sa.Numeric(12, 2), nullable=False),
    sa.Column("distribution_family", _enum("distribution_family"), nullable=False),
    sa.Column("stockout_probability", sa.Numeric(5, 4), nullable=False),
    sa.Column("expected_shortage_units", sa.Numeric(12, 2), nullable=False),
    sa.Column("is_binding", sa.Boolean, nullable=False),
    sa.ForeignKeyConstraint(
        ["run_id", "store_id", "product_id"],
        [
            "analytics.inventory_risk_snapshots.run_id",
            "analytics.inventory_risk_snapshots.store_id",
            "analytics.inventory_risk_snapshots.product_id",
        ],
        ondelete="CASCADE",
    ),
    sa.CheckConstraint("checkpoint_seq >= 1"),
    sa.CheckConstraint(
        "(checkpoint_type = 'receipt') = (purchase_order_id IS NOT NULL)"
    ),
    sa.CheckConstraint("window_days >= 0"),
    sa.CheckConstraint("window_std_days >= 0"),
    sa.CheckConstraint("supply_units >= 0"),
    sa.CheckConstraint("stockout_probability BETWEEN 0 AND 1"),
    sa.CheckConstraint("expected_shortage_units >= 0"),
    schema="analytics",
)

sa.Index(
    "ux_checkpoints_one_binding",
    Base.metadata.tables["analytics.risk_checkpoints"].c["run_id"],
    Base.metadata.tables["analytics.risk_checkpoints"].c["store_id"],
    Base.metadata.tables["analytics.risk_checkpoints"].c["product_id"],
    unique=True,
    postgresql_where=sa.text("is_binding"),
)

sa.Table(
    "replenishment_recommendations",
    Base.metadata,
    sa.Column(
        "recommendation_id", sa.BigInteger, sa.Identity(always=True), primary_key=True
    ),
    sa.Column("run_id", sa.BigInteger, nullable=False),
    sa.Column("store_id", sa.SmallInteger, nullable=False),
    sa.Column("product_id", sa.Integer, nullable=False),
    sa.Column(
        "supplier_id",
        sa.SmallInteger,
        sa.ForeignKey("ops.suppliers.supplier_id"),
        nullable=False,
    ),
    sa.Column("action_type", _enum("action_type"), nullable=False),
    sa.Column("urgency", sa.String(10)),
    sa.Column("priority_rank", sa.Integer),
    sa.Column("recommended_order_units", sa.Integer),
    sa.Column("recommended_order_cost_usd", sa.Numeric(12, 2)),
    sa.Column(
        "related_purchase_order_id",
        sa.Integer,
        sa.ForeignKey("ops.purchase_orders.purchase_order_id"),
    ),
    sa.Column("rationale", sa.Text, nullable=False),
    sa.ForeignKeyConstraint(
        ["run_id", "store_id", "product_id"],
        [
            "analytics.inventory_risk_snapshots.run_id",
            "analytics.inventory_risk_snapshots.store_id",
            "analytics.inventory_risk_snapshots.product_id",
        ],
        ondelete="CASCADE",
    ),
    sa.UniqueConstraint("run_id", "store_id", "product_id"),
    sa.CheckConstraint("urgency IN ('urgent','standard')"),
    sa.CheckConstraint("(action_type = 'no_action') = (urgency IS NULL)"),
    sa.CheckConstraint("priority_rank >= 1"),
    sa.CheckConstraint("(action_type = 'no_action') = (priority_rank IS NULL)"),
    sa.CheckConstraint("recommended_order_units >= 0"),
    sa.CheckConstraint(
        "action_type <> 'expedite_po' OR related_purchase_order_id IS NOT NULL"
    ),
    sa.CheckConstraint("action_type <> 'reorder' OR recommended_order_units > 0"),
    schema="analytics",
)

sa.Index(
    "ux_recommendations_run_priority",
    Base.metadata.tables["analytics.replenishment_recommendations"].c["run_id"],
    Base.metadata.tables["analytics.replenishment_recommendations"].c["priority_rank"],
    unique=True,
    postgresql_where=sa.text("priority_rank IS NOT NULL"),
)

sa.Table(
    "latent_demand",
    Base.metadata,
    sa.Column(
        "store_id",
        sa.SmallInteger,
        sa.ForeignKey("ops.stores.store_id"),
        primary_key=True,
    ),
    sa.Column(
        "product_id",
        sa.Integer,
        sa.ForeignKey("ops.products.product_id"),
        primary_key=True,
    ),
    sa.Column(
        "demand_date",
        sa.Date,
        sa.ForeignKey("ops.calendar.calendar_date"),
        primary_key=True,
    ),
    sa.Column("latent_units", sa.Integer, nullable=False),
    sa.CheckConstraint("latent_units >= 0"),
    schema="sim_truth",
)


class Regions(Base):
    """Mapped ops.regions record; see docs/03."""

    __table__ = Base.metadata.tables["ops.regions"]


class ProductCategories(Base):
    """Mapped ops.product_categories record; see docs/03."""

    __table__ = Base.metadata.tables["ops.product_categories"]


class Stores(Base):
    """Mapped ops.stores record; see docs/03."""

    __table__ = Base.metadata.tables["ops.stores"]


class Suppliers(Base):
    """Mapped ops.suppliers record; see docs/03."""

    __table__ = Base.metadata.tables["ops.suppliers"]


class Products(Base):
    """Mapped ops.products record; see docs/03."""

    __table__ = Base.metadata.tables["ops.products"]


class ProductSuppliers(Base):
    """Mapped ops.product_suppliers record; see docs/03."""

    __table__ = Base.metadata.tables["ops.product_suppliers"]


class SupplierStoreLanes(Base):
    """Mapped ops.supplier_store_lanes record; see docs/03."""

    __table__ = Base.metadata.tables["ops.supplier_store_lanes"]


class Calendar(Base):
    """Mapped ops.calendar record; see docs/03."""

    __table__ = Base.metadata.tables["ops.calendar"]


class Promotions(Base):
    """Mapped ops.promotions record; see docs/03."""

    __table__ = Base.metadata.tables["ops.promotions"]


class PromotionProducts(Base):
    """Mapped ops.promotion_products record; see docs/03."""

    __table__ = Base.metadata.tables["ops.promotion_products"]


class DatasetManifest(Base):
    """Mapped ops.dataset_manifest record; see docs/03."""

    __table__ = Base.metadata.tables["ops.dataset_manifest"]


class DailySales(Base):
    """Mapped ops.daily_sales record; see docs/03."""

    __table__ = Base.metadata.tables["ops.daily_sales"]


class InventorySnapshots(Base):
    """Mapped ops.inventory_snapshots record; see docs/03."""

    __table__ = Base.metadata.tables["ops.inventory_snapshots"]


class PurchaseOrders(Base):
    """Mapped ops.purchase_orders record; see docs/03."""

    __table__ = Base.metadata.tables["ops.purchase_orders"]


class PurchaseOrderLines(Base):
    """Mapped ops.purchase_order_lines record; see docs/03."""

    __table__ = Base.metadata.tables["ops.purchase_order_lines"]


class InventoryReceipts(Base):
    """Mapped ops.inventory_receipts record; see docs/03."""

    __table__ = Base.metadata.tables["ops.inventory_receipts"]


class InventoryAdjustments(Base):
    """Mapped ops.inventory_adjustments record; see docs/03."""

    __table__ = Base.metadata.tables["ops.inventory_adjustments"]


class AnalyticsRuns(Base):
    """Mapped analytics.analytics_runs record; see docs/03."""

    __table__ = Base.metadata.tables["analytics.analytics_runs"]


class DemandForecasts(Base):
    """Mapped analytics.demand_forecasts record; see docs/03."""

    __table__ = Base.metadata.tables["analytics.demand_forecasts"]


class DemandForecastDaily(Base):
    """Mapped analytics.demand_forecast_daily record; see docs/03."""

    __table__ = Base.metadata.tables["analytics.demand_forecast_daily"]


class ForecastEvaluations(Base):
    """Mapped analytics.forecast_evaluations record; see docs/03."""

    __table__ = Base.metadata.tables["analytics.forecast_evaluations"]


class SupplierLaneEstimates(Base):
    """Mapped analytics.supplier_lane_estimates record; see docs/03."""

    __table__ = Base.metadata.tables["analytics.supplier_lane_estimates"]


class InventoryRiskSnapshots(Base):
    """Mapped analytics.inventory_risk_snapshots record; see docs/03."""

    __table__ = Base.metadata.tables["analytics.inventory_risk_snapshots"]


class RiskCheckpoints(Base):
    """Mapped analytics.risk_checkpoints record; see docs/03."""

    __table__ = Base.metadata.tables["analytics.risk_checkpoints"]


class ReplenishmentRecommendations(Base):
    """Mapped analytics.replenishment_recommendations record; see docs/03."""

    __table__ = Base.metadata.tables["analytics.replenishment_recommendations"]


class LatentDemand(Base):
    """Mapped sim_truth.latent_demand record; see docs/03."""

    __table__ = Base.metadata.tables["sim_truth.latent_demand"]
