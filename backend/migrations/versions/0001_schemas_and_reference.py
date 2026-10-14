"""Create schemas, enumerations, and operational reference tables.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _enum(name: str, schema: str) -> postgresql.ENUM:
    return postgresql.ENUM(name=name, schema=schema, create_type=False)


def upgrade() -> None:
    for schema in ("ops", "analytics", "sim_truth"):
        op.execute(sa.text(f"CREATE SCHEMA {schema}"))

    enum_values = {
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
    for qualified_name, values in enum_values.items():
        schema, name = qualified_name.split(".")
        postgresql.ENUM(*values, name=name, schema=schema).create(
            op.get_bind(), checkfirst=False
        )

    op.create_table(
        "regions",
        sa.Column("region_id", sa.SmallInteger, primary_key=True),
        sa.Column("region_code", sa.String(4), nullable=False, unique=True),
        sa.Column("region_name", sa.String(40), nullable=False, unique=True),
        sa.CheckConstraint("region_code ~ '^[A-Z]{2}$'"),
        schema="ops",
    )
    op.create_table(
        "product_categories",
        sa.Column("category_id", sa.SmallInteger, primary_key=True),
        sa.Column("category_code", sa.String(4), nullable=False, unique=True),
        sa.Column("category_name", sa.String(40), nullable=False, unique=True),
        sa.CheckConstraint("category_code ~ '^[A-Z]{2}$'"),
        schema="ops",
    )
    op.create_table(
        "stores",
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
    op.create_index("ix_stores_region_id", "stores", ["region_id"], schema="ops")
    op.create_table(
        "suppliers",
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
    op.create_index(
        "ix_suppliers_primary_category_id",
        "suppliers",
        ["primary_category_id"],
        schema="ops",
    )
    op.create_table(
        "products",
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
    op.create_index(
        "ix_products_category_id", "products", ["category_id"], schema="ops"
    )
    op.create_table(
        "product_suppliers",
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
    op.create_index(
        "ix_product_suppliers_supplier_id",
        "product_suppliers",
        ["supplier_id"],
        schema="ops",
    )
    op.create_index(
        "ux_product_suppliers_one_primary",
        "product_suppliers",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
        schema="ops",
    )
    op.create_table(
        "supplier_store_lanes",
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
    op.create_index(
        "ix_lanes_store_id", "supplier_store_lanes", ["store_id"], schema="ops"
    )
    op.create_table(
        "calendar",
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
    op.create_index(
        "ix_calendar_week_start_date", "calendar", ["week_start_date"], schema="ops"
    )
    op.create_table(
        "promotions",
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
    op.create_index(
        "ix_promotions_dates", "promotions", ["start_date", "end_date"], schema="ops"
    )
    op.create_table(
        "promotion_products",
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
    op.create_index(
        "ix_promotion_products_product_id",
        "promotion_products",
        ["product_id"],
        schema="ops",
    )
    op.create_table(
        "dataset_manifest",
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


def downgrade() -> None:
    for table in (
        "dataset_manifest",
        "promotion_products",
        "promotions",
        "calendar",
        "supplier_store_lanes",
        "product_suppliers",
        "products",
        "suppliers",
        "stores",
        "product_categories",
        "regions",
    ):
        op.drop_table(table, schema="ops")
    for schema, name in (
        ("analytics", "risk_driver"),
        ("analytics", "lead_time_source"),
        ("analytics", "checkpoint_type"),
        ("analytics", "distribution_family"),
        ("analytics", "demand_pattern"),
        ("analytics", "forecast_method"),
        ("analytics", "action_type"),
        ("analytics", "risk_tier"),
        ("analytics", "run_status"),
        ("analytics", "run_type"),
        ("ops", "adjustment_reason"),
    ):
        _enum(name, schema).drop(op.get_bind(), checkfirst=False)
    for schema in ("sim_truth", "analytics", "ops"):
        op.execute(sa.text(f"DROP SCHEMA {schema}"))
