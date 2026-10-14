"""Rolling-origin evaluation; simulation truth is isolated to this module (§3.12)."""

from collections.abc import Callable, Mapping, Sequence
from datetime import date, timedelta
from typing import Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.engine import Connection

from stocgain.analytics.config import AnalyticsConfig
from stocgain.db.sql_loader import read_sql

ForecastAt = Callable[[date], tuple[list[dict[str, Any]], list[dict[str, Any]]]]


def read_latent(
    connection: Connection, as_of: date, history_days: int
) -> list[Mapping[str, Any]]:
    """Read simulation-only target units, never passed to a forecast estimator."""
    return [
        dict(row)
        for row in connection.execute(
            text(read_sql("pipeline/extract_latent_demand.sql")),
            {"as_of": as_of, "history_days": history_days},
        ).mappings()
    ]


def rolling_origins(
    as_of: date, history_start: date, config: AnalyticsConfig
) -> list[date]:
    """Return ascending weekly origins with a complete lookback and 28-day target."""
    return sorted(
        origin
        for j in range(config.backtest_origins)
        if (origin := as_of - timedelta(days=28 + 7 * j))
        - timedelta(days=config.lookback_days - 1)
        >= history_start
    )


def evaluate(
    history: Sequence[Mapping[str, Any]],
    truth: Sequence[Mapping[str, Any]],
    positions: Sequence[Mapping[str, Any]],
    as_of: date,
    history_start: date,
    config: AnalyticsConfig,
    forecast_at: ForecastAt,
) -> list[dict[str, Any]]:
    """Aggregate errors in units across origins/models/bases/segments, §3.12.

    ``forecast_at`` must recompute every observable feature at its argument;
    it receives no simulation truth. Revenue ABC uses cumulative share before
    each product, with product ID as the revenue-tie breaker (SQL view 080).
    """
    origins = rolling_origins(as_of, history_start, config)
    if not origins or not positions:
        return []
    keys = [(int(p["store_id"]), int(p["product_id"])) for p in positions]
    index = {key: i for i, key in enumerate(keys)}
    shape = (len(keys), (as_of - history_start).days + 1)
    sales = np.full(shape, np.nan)
    revenue = np.zeros(shape, dtype=np.int64)
    available = np.zeros(shape, dtype=bool)
    latent = np.full(shape, np.nan)
    for row in history:
        i = index.get((row["store_id"], row["product_id"]))
        day = (row["position_date"] - history_start).days
        if i is not None and 0 <= day < shape[1]:
            sales[i, day] = float(row["units_sold"])
            revenue[i, day] = round(float(row["net_sales_amount"]) * 100)
            available[i, day] = row["availability_status"] == "in_stock"
    for row in truth:
        i = index.get((row["store_id"], row["product_id"]))
        day = (row["demand_date"] - history_start).days
        if i is not None and 0 <= day < shape[1]:
            latent[i, day] = float(row["latent_units"])
    # Each value holds count, actual sum, forecast sum, absolute error sum.
    sums: dict[tuple[str, str, str, str], np.ndarray[Any, np.dtype[np.float64]]] = {}
    seen_origins: dict[tuple[str, str, str, str], list[date]] = {}
    product_ids = np.array([key[1] for key in keys])
    products = sorted(set(product_ids.tolist()))
    for origin in origins:
        summaries, daily = forecast_at(origin)
        end = (origin - history_start).days + 1
        observed = sales[:, end : end + 28]
        simulated = latent[:, end : end + 28]
        history_28 = sales[:, end - 28 : end]
        last_week = sales[:, end - 7 : end]
        if (
            np.isnan(history_28).any()
            or np.isnan(observed).any()
            or np.isnan(simulated).any()
        ):
            raise ValueError(
                "Backtest requires complete observed and latent target grids"
            )
        forecasts = np.full((len(keys), 28), np.nan)
        patterns = np.full(len(keys), "", dtype=object)
        for row in summaries:
            i = index.get((row["store_id"], row["product_id"]))
            if i is not None:
                patterns[i] = row["demand_pattern"]
        for row in daily:
            i = index.get((row["store_id"], row["product_id"]))
            day = (row["target_date"] - origin).days - 1
            if i is not None and 0 <= day < 28:
                forecasts[i, day] = float(row["forecast_units"])
        if np.isnan(forecasts).any() or (patterns == "").any():
            raise ValueError(
                "Origin forecast must cover every evaluated position and target"
            )
        trailing_revenue = revenue[:, max(0, end - config.lookback_days) : end].sum(
            axis=1
        )
        product_revenue = {
            p: int(trailing_revenue[product_ids == p].sum()) for p in products
        }
        total = sum(product_revenue.values())
        before = 0
        classes: dict[int, str] = {}
        for product in sorted(products, key=lambda p: (-product_revenue[p], p)):
            classes[product] = (
                "A"
                if total and before * 100 < total * 80
                else "B"
                if total and before * 100 < total * 95
                else "C"
            )
            before += product_revenue[product]
        velocity = np.array([classes[p] for p in product_ids])
        segments: list[tuple[str, str, np.ndarray[Any, np.dtype[np.bool_]]]] = [
            ("overall", "all", np.ones_like(observed, dtype=bool))
        ]
        for label, start, stop in (("1-7", 0, 7), ("8-14", 7, 14), ("15-28", 14, 28)):
            mask = np.zeros_like(observed, dtype=bool)
            mask[:, start:stop] = True
            segments.append(("horizon_bucket", label, mask))
        for kind, labels in (
            ("velocity_class", velocity),
            ("demand_pattern", patterns),
        ):
            for label in sorted(set(labels.tolist())):
                segments.append(
                    (
                        kind,
                        label,
                        np.broadcast_to((labels == label)[:, None], observed.shape),
                    )
                )
        models = {
            "stocgain_v1": forecasts,
            "naive_28d_mean": np.broadcast_to(
                history_28.mean(axis=1)[:, None], observed.shape
            ),
            "seasonal_naive_7d": np.tile(last_week, (1, 4)),
        }
        for basis, actual, valid in (
            ("observed_in_stock", observed, available[:, end : end + 28]),
            ("simulated_latent", simulated, np.ones_like(observed, dtype=bool)),
        ):
            for model, predicted in models.items():
                errors = np.abs(predicted - actual)
                for kind, label, segment in segments:
                    mask = segment & valid
                    key = (model, basis, kind, label)
                    values = np.array(
                        [
                            mask.sum(),
                            actual[mask].sum(),
                            predicted[mask].sum(),
                            errors[mask].sum(),
                        ],
                        dtype=float,
                    )
                    sums.setdefault(key, np.zeros(4))[:] += values
                    seen_origins.setdefault(key, []).append(origin)
    results: list[dict[str, Any]] = []
    for (model, basis, kind, label), values in sorted(sums.items()):
        n, actual, predicted, error = values.tolist()
        dates = seen_origins[(model, basis, kind, label)]
        results.append(
            {
                "model_name": model,
                "evaluation_basis": basis,
                "segment_type": kind,
                "segment_value": label,
                "n_origins": len(dates),
                "n_observations": int(n),
                "actual_units": actual,
                "forecast_units": predicted,
                "abs_error_units": error,
                "mae": error / n if n else None,
                "wape": error / actual if actual else None,
                "bias_rate": (predicted - actual) / actual if actual else None,
                "first_origin_date": min(dates),
                "last_origin_date": max(dates),
            }
        )
    return results
