"""Keep unobservable simulated demand isolated from operational facts.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "latent_demand",
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


def downgrade() -> None:
    op.drop_table("latent_demand", schema="sim_truth")
