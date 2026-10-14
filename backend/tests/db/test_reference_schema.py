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


def test_reference_tables_and_constraints() -> None:
    """The reference schema rejects malformed codes, prices, and duplicate primary sourcing."""
    engine = create_engine(Settings().test_database_url)
    try:
        with engine.begin() as connection:
            assert connection.scalar(
                text("SELECT to_regclass('ops.product_suppliers') IS NOT NULL")
            )

        with engine.connect() as connection, connection.begin() as transaction:
            connection.execute(
                text("INSERT INTO ops.regions VALUES (1, 'SE', 'Southeast')")
            )
            connection.execute(
                text(
                    "INSERT INTO ops.product_categories VALUES (1, 'PT', 'Power Tools')"
                )
            )
            connection.execute(
                text("""
                    INSERT INTO ops.suppliers VALUES
                    (1, 'SUP-001', 'Fictional Supply One', 1, true),
                    (2, 'SUP-002', 'Fictional Supply Two', 1, true)
                """)
            )
            connection.execute(
                text("""
                    INSERT INTO ops.products VALUES
                    (1, 'PT-10001', 'Fictional Drill', 1, 'Torvane', 'each',
                     20.00, 10.00, DATE '2023-01-01', true)
                """)
            )
            connection.execute(
                text("INSERT INTO ops.product_suppliers VALUES (1, 1, true, 6, 12)")
            )
            with pytest.raises(IntegrityError):
                with connection.begin_nested():
                    connection.execute(
                        text(
                            "INSERT INTO ops.product_suppliers VALUES (1, 2, true, 6, 12)"
                        )
                    )
            with pytest.raises(IntegrityError):
                with connection.begin_nested():
                    connection.execute(
                        text("""
                            INSERT INTO ops.products VALUES
                            (2, 'PT-10002', 'Bad Price', 1, 'Torvane', 'each',
                             10.00, 10.00, DATE '2023-01-01', true)
                        """)
                    )
            transaction.rollback()
    finally:
        engine.dispose()


def test_operational_fact_tables_and_constraints() -> None:
    """Dense facts and procurement events enforce core row-level invariants."""
    engine = create_engine(Settings().test_database_url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            connection.execute(
                text("INSERT INTO ops.regions VALUES (1, 'SE', 'Southeast')")
            )
            connection.execute(
                text(
                    "INSERT INTO ops.product_categories VALUES (1, 'PT', 'Power Tools')"
                )
            )
            connection.execute(
                text("""
                INSERT INTO ops.stores
                (store_id, store_code, store_name, city, state_code, region_id,
                 opened_date, sales_area_sqft)
                VALUES (1, 'S01', 'Fictional Store', 'Atlanta', 'GA', 1,
                        DATE '2020-01-01', 100000)
            """)
            )
            connection.execute(
                text("""
                INSERT INTO ops.products
                (product_id, sku, product_name, category_id, brand_name,
                 unit_of_measure, unit_price, unit_cost, introduced_date)
                VALUES (1, 'PT-10001', 'Fictional Drill', 1, 'Torvane',
                        'each', 20.00, 10.00, DATE '2023-01-01')
            """)
            )
            connection.execute(
                text("""
                INSERT INTO ops.calendar
                (calendar_date, iso_year, iso_week, iso_day_of_week, day_name,
                 month, month_name, quarter, week_start_date, is_weekend)
                VALUES (DATE '2026-09-30', 2026, 40, 3, 'Wednesday',
                        9, 'September', 3, DATE '2026-09-28', false)
            """)
            )
            with pytest.raises(IntegrityError):
                with connection.begin_nested():
                    connection.execute(
                        text("""
                        INSERT INTO ops.inventory_snapshots VALUES
                        (1, 1, DATE '2026-09-30', 0, -1)
                    """)
                    )
            with pytest.raises(IntegrityError):
                with connection.begin_nested():
                    connection.execute(
                        text("""
                        INSERT INTO ops.daily_sales VALUES
                        (1, 1, DATE '2026-09-30', -1, 0, 0)
                    """)
                    )
            transaction.rollback()
    finally:
        engine.dispose()
