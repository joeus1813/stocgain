"""Real PostgreSQL fixtures; production database is never used for mutations."""

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from stocgain.db.views import apply_views
from stocgain.generator.config import load_config
from stocgain.generator.simulation import simulate
from stocgain.generator.writer import write_dataset
from stocgain.loader.copy_loader import load_dataset
from stocgain.settings import REPOSITORY_ROOT, Settings


@pytest.fixture(scope="session")
def loaded_small_db(tmp_path_factory):
    settings = Settings()
    assert settings.test_database_url != settings.database_url
    engine = create_engine(settings.test_database_url)
    cfg = Config(str(REPOSITORY_ROOT / "backend/alembic.ini"))
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")
    path = tmp_path_factory.mktemp("small") / "dataset"
    write_dataset(simulate(load_config("small"), 42), path)
    load_dataset(engine, path)
    apply_views(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_tx(loaded_small_db):
    with loaded_small_db.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


@pytest.fixture
def risk_position(db_tx):
    from stocgain.db.models import Base

    t = Base.metadata.tables
    run = db_tx.execute(
        t["analytics.analytics_runs"]
        .insert()
        .values(
            run_type="current",
            as_of_date="2026-09-30",
            model_version="test",
            config={},
            dataset_checksum="0" * 64,
        )
        .returning(t["analytics.analytics_runs"].c.run_id)
    ).scalar_one()
    db_tx.execute(
        t["analytics.demand_forecasts"]
        .insert()
        .values(
            run_id=run,
            store_id=1,
            product_id=1,
            method="store_sku",
            demand_pattern="smooth",
            lookback_days=56,
            clean_days=49,
            censored_days=4,
            promo_days=3,
            base_daily_demand=12,
            daily_demand_std=5,
            forecast_7d_units=84,
            forecast_14d_units=168,
            forecast_28d_units=336,
            forecast_7d_std_units=13.23,
            forecast_14d_std_units=18.71,
            forecast_28d_std_units=26.46,
        )
    )
    db_tx.execute(
        t["analytics.supplier_lane_estimates"]
        .insert()
        .values(
            run_id=run,
            supplier_id=1,
            store_id=1,
            lead_time_source="lane",
            n_received_pos=27,
            mean_lead_time_days=10,
            std_lead_time_days=2,
            mean_delay_days=0.92,
            std_delay_days=1.88,
            mean_delay_when_late_days=3.10,
            on_time_rate=0.7037,
        )
    )
    db_tx.execute(
        t["analytics.inventory_risk_snapshots"]
        .insert()
        .values(
            run_id=run,
            store_id=1,
            product_id=1,
            supplier_id=1,
            on_hand_units=100,
            on_order_units=0,
            inventory_position_units=100,
            open_po_count=0,
            next_receipt_overdue=False,
            avg_daily_demand_units=12,
            daily_demand_std_units=5,
            days_of_cover=8.3,
            lead_time_mean_days=10,
            lead_time_std_days=2,
            protection_window_days=10,
            lead_time_demand_mean_units=120,
            lead_time_demand_std_units=28.74,
            distribution_family="normal",
            service_level=0.95,
            safety_stock_units=47.27,
            reorder_point_units=168,
            order_up_to_units=257,
            below_reorder_point=True,
            binding_checkpoint_type="window_end",
            binding_window_days=10,
            binding_supply_units=100,
            binding_demand_mean_units=120,
            binding_demand_std_units=28.74,
            stockout_probability=0.7568,
            expected_shortage_units=24.14,
            lost_sale_rate=0.65,
            expected_lost_units=15.69,
            revenue_at_risk_usd=391.88,
            margin_at_risk_usd=148.88,
            currently_out_of_stock=False,
            recent_censored_days=2,
            risk_tier="critical",
            explanation="Illustrative test fixture.",
        )
    )
    db_tx.execute(
        t["analytics.replenishment_recommendations"]
        .insert()
        .values(
            run_id=run,
            store_id=1,
            product_id=1,
            supplier_id=1,
            action_type="no_action",
            rationale="Constraint fixture",
        )
    )
    return run


@pytest.fixture
def sql_run(db_tx, risk_position):
    from sqlalchemy import text

    db_tx.execute(
        text(
            "UPDATE analytics.analytics_runs SET status='succeeded', completed_at='2026-10-01 00:00:00+00' WHERE run_id=:run"
        ),
        {"run": risk_position},
    )
    db_tx.execute(
        text(
            "UPDATE analytics.replenishment_recommendations SET action_type='reorder',urgency='urgent', priority_rank=1, recommended_order_units=168,recommended_order_cost_usd=1680 WHERE run_id=:run"
        ),
        {"run": risk_position},
    )
    return risk_position


@pytest.fixture
def actual_model_run(db_tx):
    """Actual calculations and PostgreSQL persistence, rolled back after each test."""
    from datetime import date

    from sqlalchemy import func

    from stocgain.analytics.config import AnalyticsConfig
    from stocgain.analytics.pipeline import compute, extract_inputs, persist
    from stocgain.db.models import Base

    def insert_outputs(connection, inputs, outputs):
        runs = Base.metadata.tables["analytics.analytics_runs"]
        run = connection.execute(
            runs.insert()
            .values(
                run_type="current",
                as_of_date=inputs.as_of,
                model_version=inputs.config.model_version,
                config=inputs.config.to_dict(),
                dataset_checksum="0" * 64,
            )
            .returning(runs.c.run_id)
        ).scalar_one()
        persist(connection, run, outputs, True)
        connection.execute(
            runs.update()
            .where(runs.c.run_id == run)
            .values(status="succeeded", completed_at=func.now())
        )
        return run

    inputs = extract_inputs(db_tx, date(2026, 9, 30), AnalyticsConfig())
    return insert_outputs(db_tx, inputs, compute(inputs))


@pytest.fixture
def api_client(db_tx, actual_model_run):
    """HTTP contracts against actual computed data in a rolled-back transaction."""
    from fastapi.testclient import TestClient

    from stocgain.api.app import create_app
    from stocgain.api.dependencies import get_connection

    app = create_app()
    app.dependency_overrides[get_connection] = lambda: db_tx
    with TestClient(app) as client:
        yield client
