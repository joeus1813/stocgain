"""Transactional point-in-time model orchestration (docs/09 Phase 3)."""

import math
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from time import perf_counter

import sqlalchemy as sa
from sqlalchemy import Connection, Engine

from stocgain.analytics.config import AnalyticsConfig, load_config
from stocgain.analytics.forecasting import forecast
from stocgain.analytics.leadtime import select_lane_estimate
from stocgain.analytics.replenishment import rank
from stocgain.analytics.risk import score_position
from stocgain.analytics.types import ModelInputs, ModelOutputs, Record
from stocgain.db.models import Base
from stocgain.db.sql_loader import read_sql


def extract(
    connection: Connection, name: str, as_of: date, history_days: int = 56
) -> list[Record]:
    """Execute a repository-owned cutoff-bounded extraction."""
    return [
        dict(row)
        for row in connection.execute(
            sa.text(read_sql(f"pipeline/extract_{name}.sql")),
            {"as_of": as_of, "history_days": history_days},
        ).mappings()
    ]


def extract_inputs(
    connection: Connection, as_of: date, config: AnalyticsConfig
) -> ModelInputs:
    """Read only operational inputs knowable by end of the requested date."""
    positions = extract(connection, "positions", as_of)
    on_hand = {
        (r["store_id"], r["product_id"]): r
        for r in extract(connection, "on_hand", as_of)
    }
    for p in positions:
        key = p["store_id"], p["product_id"]
        if key not in on_hand:
            raise ValueError(f"Missing closing inventory at {as_of} for {key}")
        p.update(on_hand[key])
        p["on_hand_units"] = p["closing_on_hand"]
    return ModelInputs(
        as_of,
        config,
        positions,
        extract(connection, "daily_history", as_of, config.lookback_days),
        extract(connection, "category_dow_profile", as_of),
        extract(connection, "product_chain_rate", as_of),
        extract(connection, "store_scale", as_of),
        extract(connection, "planned_promotions", as_of),
        extract(connection, "lane_lead_times", as_of),
        extract(connection, "supplier_lead_times", as_of),
        extract(connection, "open_po_lines", as_of),
    )


def forecast_inputs(inputs: ModelInputs) -> tuple[list[Record], list[Record]]:
    """Run the same censoring-aware forecast in current and historical runs."""
    return forecast(
        inputs.history,
        inputs.positions,
        inputs.dow,
        inputs.chain,
        inputs.scales,
        inputs.promotions,
        inputs.as_of,
        inputs.config,
    )


def compute(inputs: ModelInputs) -> ModelOutputs:
    """Compute full precision model outputs without database access."""
    forecasts, daily = forecast_inputs(inputs)
    suppliers = {r["supplier_id"]: r for r in inputs.suppliers}
    lanes = [
        select_lane_estimate(r, suppliers.get(r["supplier_id"], {}), inputs.config)
        for r in inputs.lanes
    ]
    lane_map = {(r["supplier_id"], r["store_id"]): r for r in lanes}
    daily_map: dict[tuple[int, int], list[float]] = defaultdict(list)
    for row in sorted(daily, key=lambda r: r["horizon_day"]):
        daily_map[row["store_id"], row["product_id"]].append(
            float(row["forecast_units"])
        )
    po_map: dict[tuple[int, int], list[Record]] = defaultdict(list)
    for po in inputs.open_pos:
        po_map[po["store_id"], po["product_id"]].append(po)
    forecast_map = {(r["store_id"], r["product_id"]): r for r in forecasts}
    risks, checkpoints, recommendations = [], [], []
    for source in inputs.positions:
        position = dict(source)
        lead = lane_map[position["supplier_id"], position["store_id"]][
            "mean_lead_time_days"
        ]
        future = [
            p
            for p in inputs.promotions
            if p["store_id"] == position["store_id"]
            and p["product_id"] == position["product_id"]
            and p["target_date"] <= inputs.as_of + timedelta(days=math.ceil(lead))
        ]
        if future:
            position["upcoming_promotion"] = min(future, key=lambda p: p["target_date"])
        key = position["store_id"], position["product_id"]
        risk, points, recommendation = score_position(
            position,
            forecast_map[key],
            daily_map[key],
            lane_map[position["supplier_id"], position["store_id"]],
            po_map[key],
            inputs.as_of,
            inputs.config,
        )
        risks.append(risk)
        checkpoints.extend(points)
        recommendations.append(recommendation)
    return ModelOutputs(
        forecasts, daily, lanes, risks, checkpoints, rank(recommendations, risks)
    )


def persist(
    connection: Connection, run_id: int, outputs: ModelOutputs, current: bool
) -> None:
    """Insert all dependent model rows atomically; let PostgreSQL enforce constraints."""
    groups = [
        ("demand_forecasts", outputs.forecasts),
        ("demand_forecast_daily", outputs.daily if current else []),
        ("supplier_lane_estimates", outputs.lanes),
        ("inventory_risk_snapshots", outputs.risks),
        ("risk_checkpoints", outputs.checkpoints),
        ("replenishment_recommendations", outputs.recommendations),
        ("forecast_evaluations", outputs.evaluations),
    ]
    for name, rows in groups:
        table = Base.metadata.tables[f"analytics.{name}"]
        for start in range(0, len(rows), 2000):
            connection.execute(
                table.insert(),
                [{"run_id": run_id, **row} for row in rows[start : start + 2000]],
            )


def run(
    engine: Engine,
    as_of: date | None = None,
    *,
    run_type: str = "current",
    evaluate: bool = False,
    config: AnalyticsConfig | None = None,
) -> Record:
    """Persist a complete run, marking failures without publishing partial outputs."""
    config = config or load_config()
    tables = Base.metadata.tables
    runs = tables["analytics.analytics_runs"]
    started = perf_counter()
    timings: dict[str, float] = {}
    with engine.begin() as connection:
        manifest = (
            connection.execute(sa.select(tables["ops.dataset_manifest"]))
            .mappings()
            .one()
        )
        cutoff = as_of or manifest["history_end_date"]
        if not manifest["history_start_date"] <= cutoff <= manifest["history_end_date"]:
            raise ValueError("as_of must be within the loaded history")
        run_id = int(
            connection.execute(
                runs.insert()
                .values(
                    run_type=run_type,
                    as_of_date=cutoff,
                    model_version=config.model_version,
                    config=config.to_dict(),
                    dataset_checksum=manifest["content_checksum"],
                )
                .returning(runs.c.run_id)
            ).scalar_one()
        )
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            )
            connection.execute(sa.text("SET LOCAL max_parallel_workers_per_gather = 0"))
            step = perf_counter()
            inputs = extract_inputs(connection, cutoff, config)
            timings["extract"] = perf_counter() - step
            step = perf_counter()
            outputs = compute(inputs)
            timings["compute"] = perf_counter() - step
            if evaluate:
                from stocgain.analytics.backtest import evaluate as evaluate_forecasts
                from stocgain.analytics.backtest import read_latent

                step = perf_counter()
                days = (cutoff - manifest["history_start_date"]).days + 1
                history = extract(connection, "daily_history", cutoff, days)
                truth = read_latent(connection, cutoff, days)
                outputs.evaluations = evaluate_forecasts(
                    history,
                    truth,
                    inputs.positions,
                    cutoff,
                    manifest["history_start_date"],
                    config,
                    lambda origin: forecast_inputs(
                        extract_inputs(connection, origin, config)
                    ),
                )
                timings["backtest"] = perf_counter() - step
            step = perf_counter()
            persist(connection, run_id, outputs, run_type == "current")
            timings["persist"] = perf_counter() - step
            timings["total"] = perf_counter() - started
            connection.execute(
                runs.update()
                .where(runs.c.run_id == run_id)
                .values(
                    status="succeeded",
                    completed_at=datetime.now(UTC),
                    positions_scored=len(outputs.risks),
                    step_timings=timings,
                )
            )
            connection.execute(
                runs.delete().where(
                    runs.c.run_type == run_type,
                    runs.c.as_of_date == cutoff,
                    runs.c.run_id < run_id,
                    runs.c.status == "succeeded",
                )
            )
        return {
            "run_id": run_id,
            "as_of_date": cutoff,
            "positions_scored": len(outputs.risks),
            "step_timings": timings,
        }
    except Exception as error:
        with engine.begin() as connection:
            connection.execute(
                runs.update()
                .where(runs.c.run_id == run_id)
                .values(
                    status="failed",
                    completed_at=datetime.now(UTC),
                    error_message=str(error)[:4000],
                    step_timings=timings,
                )
            )
        raise


def backfill(engine: Engine, weeks: int | None = None) -> list[Record]:
    """Compute weekly historical runs, oldest first, without daily rows/evaluation."""
    config = load_config()
    weeks = config.backfill_weeks if weeks is None else weeks
    if weeks < 1:
        raise ValueError("weeks must be positive")
    with engine.connect() as connection:
        end = connection.scalar(
            sa.select(Base.metadata.tables["ops.dataset_manifest"].c.history_end_date)
        )
    if end is None:
        raise ValueError("No loaded dataset")
    return [
        run(engine, end - timedelta(weeks=w), run_type="backfill", config=config)
        for w in range(weeks, 0, -1)
    ]
