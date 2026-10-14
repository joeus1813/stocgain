"""Actual model outputs against the existing small PostgreSQL dataset."""

from datetime import date
from decimal import Decimal

import pytest
import sqlalchemy as sa

from stocgain.analytics.config import AnalyticsConfig
from stocgain.analytics.pipeline import compute, extract_inputs, persist
from stocgain.db.models import Base

pytestmark = pytest.mark.db


@pytest.fixture
def computed_outputs(db_tx):
    inputs = extract_inputs(db_tx, date(2026, 9, 30), AnalyticsConfig())
    return inputs, compute(inputs)


def test_pipeline_persistence_and_constraints(db_tx, computed_outputs):
    inputs, outputs = computed_outputs
    run = insert_outputs(db_tx, inputs, outputs)
    for name, count in [
        ("demand_forecasts", 180),
        ("demand_forecast_daily", 7560),
        ("inventory_risk_snapshots", 180),
        ("replenishment_recommendations", 180),
    ]:
        assert (
            db_tx.scalar(
                sa.text(f"SELECT count(*) FROM analytics.{name} WHERE run_id=:run"),
                {"run": run},
            )
            == count
        )
    ranks = db_tx.scalars(
        sa.text(
            "SELECT priority_rank FROM analytics.replenishment_recommendations WHERE run_id=:run AND priority_rank IS NOT NULL ORDER BY priority_rank"
        ),
        {"run": run},
    ).all()
    assert ranks == list(range(1, len(ranks) + 1))
    assert (
        db_tx.scalar(
            sa.text(
                "SELECT count(*) FROM analytics.risk_checkpoints WHERE run_id=:run AND is_binding"
            ),
            {"run": run},
        )
        == 180
    )
    rows = (
        db_tx.execute(
            sa.select(Base.metadata.tables["analytics.inventory_risk_snapshots"]).where(
                Base.metadata.tables["analytics.inventory_risk_snapshots"].c.run_id
                == run
            ),
        )
        .mappings()
        .all()
    )
    for row in rows:
        assert (
            row["inventory_position_units"]
            == row["on_hand_units"] + row["on_order_units"]
        )
        assert row["reorder_point_units"] <= row["order_up_to_units"]
        assert Decimal(0) <= row["stockout_probability"] <= Decimal(1)


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
        .values(
            status="succeeded",
            completed_at=sa.func.now(),
            positions_scored=len(outputs.risks),
        )
    )
    return run


def test_pipeline_repeatability(computed_outputs):
    inputs, outputs = computed_outputs
    assert compute(inputs) == outputs


def test_pipeline_explanation_numbers(computed_outputs):
    _, outputs = computed_outputs
    for row in outputs.risks[:100]:
        assert f"{row['stockout_probability'] * 100:.1f}%" in row["explanation"]
        assert (
            f"{row['margin_at_risk_usd']:,.0f}" in row["explanation"]
            or f"{row['margin_at_risk_usd']:,.2f}" in row["explanation"]
        )


def test_pipeline_neutral_scenario_matches_postgresql(db_tx, computed_outputs):
    from stocgain.analytics.scenario import ScenarioParameters, evaluate
    from stocgain.analytics.serialization import snapshot_precision

    inputs, outputs = computed_outputs
    run = insert_outputs(db_tx, inputs, outputs)
    stored = {
        (r["store_id"], r["product_id"]): dict(r)
        for r in db_tx.execute(
            sa.select(Base.metadata.tables["analytics.inventory_risk_snapshots"]).where(
                Base.metadata.tables["analytics.inventory_risk_snapshots"].c.run_id
                == run
            ),
        ).mappings()
    }
    result = evaluate(inputs, outputs)
    assert all(v == 0 for v in result["delta"]["absolute"].values())
    for row in result["position_results"]:
        actual = snapshot_precision(row["scenario"])
        expected = stored[row["store_id"], row["product_id"]]
        for key, value in actual.items():
            if isinstance(value, float):
                assert value == pytest.approx(float(expected[key]), abs=1e-6)
            else:
                assert value == expected[key]
    service = evaluate(inputs, outputs, ScenarioParameters(service_level=0.98))
    for key in ("margin_at_risk_usd", "at_risk_positions", "mean_stockout_probability"):
        assert service["delta"]["absolute"][key] == 0
    assert service["delta"]["absolute"]["safety_stock_value_usd"] > 0
    assert service["delta"]["absolute"]["annual_expected_shortfall_margin_usd"] < 0
