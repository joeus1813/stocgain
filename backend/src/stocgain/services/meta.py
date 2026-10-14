"""Provenance and documented parameters from actual dataset/run state."""

import tomllib
from typing import Any

from sqlalchemy import Connection, text

from stocgain.analytics.config import AnalyticsConfig
from stocgain.db.sql_loader import read_sql
from stocgain.settings import REPOSITORY_ROOT


def metadata(connection: Connection) -> dict[str, Any]:
    """Return dataset provenance even when no analytics run exists."""
    dataset = connection.execute(text(read_sql("api/meta.sql"))).mappings().first()
    run = connection.execute(text(read_sql("api/current_run.sql"))).mappings().first()
    config = AnalyticsConfig(**run["config"]) if run else AnalyticsConfig()
    dimensions = connection.execute(text(read_sql("api/filters.sql"))).mappings().one()
    events_config = tomllib.loads(
        (REPOSITORY_ROOT / "backend/config/generator.toml").read_text()
    )["events"]
    labels = {
        "storm": ("E1", "Southeast storm-prep surge"),
        "electrical_delay": ("E2", "Electrical supplier delay"),
        "plumbing": ("E3", "Plumbing supplier uncertainty"),
        "fall_promotions": ("E4", "Planned fall promotions"),
    }
    events = [
        {
            "id": labels[key][0],
            "name": labels[key][1],
            "description": ", ".join(f"{k}: {v}" for k, v in value.items()),
        }
        for key, value in events_config.items()
        if key in labels and events_config.get("enabled", False)
    ]
    data = None
    if dataset:
        data = {
            key: dataset[key]
            for key in (
                "data_origin",
                "generator_version",
                "preset",
                "seed",
                "history_start_date",
                "history_end_date",
                "row_counts",
                "counts",
            )
        }
        data.update(
            label="Simulated Retail Dataset",
            provenance_statement=dataset["notes"],
            events=events,
        )
    run_data = None
    if run:
        run_data = {
            key: run[key]
            for key in (
                "run_id",
                "run_type",
                "as_of_date",
                "model_version",
                "completed_at",
            )
        }
        run_data["backfill_runs_available"] = (
            dataset["backfill_runs_available"] if dataset else 0
        )
    params = {
        key: getattr(config, key)
        for key in (
            "service_level",
            "review_period_days",
            "lookback_days",
            "half_life_days",
            "min_clean_days_full",
            "min_clean_days_blend",
            "normal_min_mean_units",
            "exposure_escalation_usd",
            "carrying_cost_rate_annual",
        )
    }
    params.update(
        tier_thresholds={
            tier: getattr(config, f"tier_{tier}_probability")
            for tier in ("critical", "high", "moderate")
        },
        lost_sale_rates={
            r["category_name"]: config.lost_sale_rates[r["category_code"]]
            for r in dimensions["categories"]
        },
        scenario_limits={
            "lead_time_change_days": [-7, 14],
            "demand_change_rate": [-0.5, 1.0],
            "service_level": [0.8, 0.995],
            "safety_stock_buffer_rate": [-0.5, 1.0],
        },
    )
    return {"dataset": data, "run": run_data, "parameters": params}
