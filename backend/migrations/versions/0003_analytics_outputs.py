"""Create versioned analytics output tables.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(name=name, schema="analytics", create_type=False)


def _position_columns() -> list[sa.Column]:
    return [
        sa.Column("run_id", sa.BigInteger, primary_key=True),
        sa.Column("store_id", sa.SmallInteger, primary_key=True),
        sa.Column("product_id", sa.Integer, primary_key=True),
    ]


def upgrade() -> None:
    op.create_table(
        "analytics_runs",
        sa.Column("run_id", sa.BigInteger, sa.Identity(always=True), primary_key=True),
        sa.Column("run_type", _enum("run_type"), nullable=False),
        sa.Column(
            "as_of_date",
            sa.Date,
            sa.ForeignKey("ops.calendar.calendar_date"),
            nullable=False,
        ),
        sa.Column(
            "status", _enum("run_status"), nullable=False, server_default="running"
        ),
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
    op.create_index(
        "ix_runs_status_type_asof",
        "analytics_runs",
        [
            "status",
            "run_type",
            sa.text("as_of_date DESC"),
            sa.text("completed_at DESC"),
        ],
        schema="analytics",
    )
    op.create_table(
        "demand_forecasts",
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
    op.create_table(
        "demand_forecast_daily",
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
        sa.Column(
            "promotion_id", sa.Integer, sa.ForeignKey("ops.promotions.promotion_id")
        ),
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
    op.create_table(
        "forecast_evaluations",
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
        sa.CheckConstraint(
            "evaluation_basis IN ('observed_in_stock','simulated_latent')"
        ),
        sa.CheckConstraint(
            "segment_type IN ('overall','horizon_bucket','velocity_class','demand_pattern')"
        ),
        sa.CheckConstraint("n_origins > 0"),
        sa.CheckConstraint("n_observations >= 0"),
        schema="analytics",
    )
    op.create_table(
        "supplier_lane_estimates",
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
            [
                "ops.supplier_store_lanes.supplier_id",
                "ops.supplier_store_lanes.store_id",
            ],
        ),
        sa.CheckConstraint("n_received_pos >= 0"),
        sa.CheckConstraint("mean_lead_time_days > 0"),
        sa.CheckConstraint("std_lead_time_days >= 0"),
        sa.CheckConstraint("std_delay_days >= 0"),
        sa.CheckConstraint("mean_delay_when_late_days >= 0"),
        sa.CheckConstraint("on_time_rate BETWEEN 0 AND 1"),
        schema="analytics",
    )
    op.create_table(
        "inventory_risk_snapshots",
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
            "next_receipt_overdue",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
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
    op.create_index(
        "ix_risk_run_tier_margin",
        "inventory_risk_snapshots",
        ["run_id", sa.text("risk_tier DESC"), sa.text("margin_at_risk_usd DESC")],
        schema="analytics",
    )
    op.create_index(
        "ix_risk_run_store",
        "inventory_risk_snapshots",
        ["run_id", "store_id"],
        schema="analytics",
    )
    op.create_index(
        "ix_risk_run_supplier",
        "inventory_risk_snapshots",
        ["run_id", "supplier_id"],
        schema="analytics",
    )
    op.create_index(
        "ix_risk_run_product",
        "inventory_risk_snapshots",
        ["run_id", "product_id"],
        schema="analytics",
    )
    op.create_table(
        "risk_checkpoints",
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
    op.create_index(
        "ux_checkpoints_one_binding",
        "risk_checkpoints",
        ["run_id", "store_id", "product_id"],
        unique=True,
        postgresql_where=sa.text("is_binding"),
        schema="analytics",
    )
    op.create_table(
        "replenishment_recommendations",
        sa.Column(
            "recommendation_id",
            sa.BigInteger,
            sa.Identity(always=True),
            primary_key=True,
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
    op.create_index(
        "ux_recommendations_run_priority",
        "replenishment_recommendations",
        ["run_id", "priority_rank"],
        unique=True,
        postgresql_where=sa.text("priority_rank IS NOT NULL"),
        schema="analytics",
    )


def downgrade() -> None:
    for table in (
        "replenishment_recommendations",
        "risk_checkpoints",
        "inventory_risk_snapshots",
        "supplier_lane_estimates",
        "forecast_evaluations",
        "demand_forecast_daily",
        "demand_forecasts",
        "analytics_runs",
    ):
        op.drop_table(table, schema="analytics")
