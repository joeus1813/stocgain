"""Read-only standard model acceptance and independently persisted scenario checks."""

import json
from time import perf_counter

import sqlalchemy as sa

from stocgain.analytics.config import AnalyticsConfig
from stocgain.analytics.pipeline import compute, extract_inputs
from stocgain.analytics.scenario import evaluate
from stocgain.analytics.serialization import snapshot_precision
from stocgain.db.engine import create_db_engine
from stocgain.db.models import Base
from stocgain.settings import get_settings


def main() -> None:
    """Print only actually measured metrics from the populated database."""
    engine = create_db_engine(get_settings())
    tables = Base.metadata.tables
    with engine.connect() as connection:
        runs = [
            dict(r)
            for r in connection.execute(
                sa.select(tables["analytics.analytics_runs"]).where(
                    tables["analytics.analytics_runs"].c.status == "succeeded"
                )
            ).mappings()
        ]
        current = max(
            (r for r in runs if r["run_type"] == "current"), key=lambda r: r["run_id"]
        )
        run = current["run_id"]
        inputs = extract_inputs(
            connection, current["as_of_date"], AnalyticsConfig(**current["config"])
        )
        outputs = compute(inputs)
        stored = {
            (r["store_id"], r["product_id"]): dict(r)
            for r in connection.execute(
                sa.select(tables["analytics.inventory_risk_snapshots"]).where(
                    tables["analytics.inventory_risk_snapshots"].c.run_id == run
                )
            ).mappings()
        }
        start = perf_counter()
        neutral = evaluate(inputs, outputs)
        scenario_seconds = perf_counter() - start
        assert all(v == 0 for v in neutral["delta"]["absolute"].values())
        for row in neutral["position_results"]:
            result = snapshot_precision(row["scenario"])
            expected = stored[row["store_id"], row["product_id"]]
            for key, value in result.items():
                if isinstance(value, float):
                    assert abs(value - float(expected[key])) <= 1e-6, (
                        row["store_id"],
                        row["product_id"],
                        key,
                        value,
                        expected[key],
                    )
                else:
                    assert value == expected[key], (key, value, expected[key])
        counts = {}
        for name in (
            "demand_forecasts",
            "demand_forecast_daily",
            "inventory_risk_snapshots",
            "risk_checkpoints",
            "replenishment_recommendations",
            "forecast_evaluations",
        ):
            table = tables[f"analytics.{name}"]
            counts[name] = connection.scalar(
                sa.select(sa.func.count())
                .select_from(table)
                .where(table.c.run_id == run)
            )
        evaluations = [
            dict(r)
            for r in connection.execute(
                sa.select(tables["analytics.forecast_evaluations"]).where(
                    tables["analytics.forecast_evaluations"].c.run_id == run,
                    tables["analytics.forecast_evaluations"].c.segment_type
                    == "overall",
                )
            ).mappings()
        ]
        print(
            json.dumps(
                {
                    "run_id": run,
                    "succeeded_runs": len(runs),
                    "counts": counts,
                    "tier_counts": neutral["baseline"]["positions_by_tier"],
                    "neutral_positions_verified": len(stored),
                    "scenario_seconds": scenario_seconds,
                    "pipeline_seconds": sum(r["step_timings"]["total"] for r in runs),
                    "evaluations": evaluations,
                },
                default=str,
                indent=2,
            )
        )
    engine.dispose()


if __name__ == "__main__":
    main()
