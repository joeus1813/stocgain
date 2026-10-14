"""Create dense sales and inventory facts plus procurement events.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_sales",
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
        sa.CheckConstraint(
            "units_sold > 0 OR (net_sales_amount = 0 AND cogs_amount = 0)"
        ),
        schema="ops",
    )
    op.create_index(
        "brin_daily_sales_sales_date",
        "daily_sales",
        ["sales_date"],
        schema="ops",
        postgresql_using="brin",
    )
    op.create_table(
        "inventory_snapshots",
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
    op.create_index(
        "ix_inventory_snapshots_date",
        "inventory_snapshots",
        ["snapshot_date"],
        schema="ops",
    )
    op.create_table(
        "purchase_orders",
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
            [
                "ops.supplier_store_lanes.supplier_id",
                "ops.supplier_store_lanes.store_id",
            ],
        ),
        sa.CheckConstraint("po_number ~ '^PO-[0-9]{6}$'"),
        sa.CheckConstraint("promised_delivery_date > order_date"),
        schema="ops",
    )
    op.create_index(
        "ix_po_store_order_date",
        "purchase_orders",
        ["store_id", "order_date"],
        schema="ops",
    )
    op.create_index(
        "ix_po_supplier_promised",
        "purchase_orders",
        ["supplier_id", "promised_delivery_date"],
        schema="ops",
    )
    op.create_table(
        "purchase_order_lines",
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
    op.create_index(
        "ix_po_lines_product_id", "purchase_order_lines", ["product_id"], schema="ops"
    )
    op.create_table(
        "inventory_receipts",
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
    op.create_index(
        "ix_receipts_received_date",
        "inventory_receipts",
        ["received_date"],
        schema="ops",
    )
    op.create_table(
        "inventory_adjustments",
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
        sa.CheckConstraint(
            "reason_code = 'cycle_count_correction' OR quantity_delta < 0"
        ),
        schema="ops",
    )


def downgrade() -> None:
    for table in (
        "inventory_adjustments",
        "inventory_receipts",
        "purchase_order_lines",
        "purchase_orders",
        "inventory_snapshots",
        "daily_sales",
    ):
        op.drop_table(table, schema="ops")
