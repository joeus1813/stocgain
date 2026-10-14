"""PostgreSQL constraints introduced by the first schema revision."""

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from stocgain.settings import Settings

pytestmark = pytest.mark.db


def test_all_26_specified_tables_exist() -> None:
    """The four revisions cover every Stage 1 physical table and no P2 tables."""
    expected = {
        "ops": {
            "regions",
            "stores",
            "product_categories",
            "suppliers",
            "products",
            "product_suppliers",
            "supplier_store_lanes",
            "calendar",
            "promotions",
            "promotion_products",
            "dataset_manifest",
            "daily_sales",
            "inventory_snapshots",
            "purchase_orders",
            "purchase_order_lines",
            "inventory_receipts",
            "inventory_adjustments",
        },
        "analytics": {
            "analytics_runs",
            "demand_forecasts",
            "demand_forecast_daily",
            "forecast_evaluations",
            "supplier_lane_estimates",
            "inventory_risk_snapshots",
            "risk_checkpoints",
            "replenishment_recommendations",
        },
        "sim_truth": {"latent_demand"},
    }
    engine = create_engine(Settings().test_database_url)
    try:
        inspector = inspect(engine)
        for schema, tables in expected.items():
            assert set(inspector.get_table_names(schema=schema)) == tables
    finally:
        engine.dispose()


def test_reference_tables_and_constraints(db_tx) -> None:
    """Existing small-preset rows reject invalid price and primary sourcing."""
    with pytest.raises(IntegrityError), db_tx.begin_nested():
        db_tx.execute(
            text("UPDATE ops.products SET unit_price=unit_cost WHERE product_id=1")
        )
    with pytest.raises(IntegrityError), db_tx.begin_nested():
        db_tx.execute(
            text(
                "INSERT INTO ops.product_suppliers SELECT product_id, (SELECT max(supplier_id) FROM ops.suppliers), true, 6, 12 FROM ops.products WHERE product_id=1"
            )
        )


def test_operational_fact_tables_and_constraints(db_tx) -> None:
    """Dense facts reject negative stock and sales on real loaded records."""
    with pytest.raises(IntegrityError), db_tx.begin_nested():
        db_tx.execute(
            text(
                "UPDATE ops.inventory_snapshots SET closing_on_hand=-1 WHERE store_id=1 AND product_id=1"
            )
        )
    with pytest.raises(IntegrityError), db_tx.begin_nested():
        db_tx.execute(
            text(
                "UPDATE ops.daily_sales SET units_sold=-1 WHERE store_id=1 AND product_id=1"
            )
        )
