"""Independent rolling-origin, baseline, basis and error metric fixtures."""

from dataclasses import replace
from datetime import date, timedelta
from typing import Any

import pytest

from stocgain.analytics.backtest import evaluate, rolling_origins
from stocgain.analytics.config import AnalyticsConfig

T = date(2026, 9, 30)
POSITIONS = [{"store_id": 1, "product_id": 1, "category_id": 1}]


def fixture(value: float = 0) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    history = [
        {
            "store_id": 1,
            "product_id": 1,
            "position_date": T - timedelta(days=i),
            "units_sold": value,
            "net_sales_amount": 2 * value,
            "availability_status": "in_stock",
        }
        for i in range(84)
    ]
    truth = [
        {
            "store_id": 1,
            "product_id": 1,
            "demand_date": row["position_date"],
            "latent_units": value,
        }
        for row in history
    ]
    return history, truth


def prediction(origin: date) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return [{"store_id": 1, "product_id": 1, "demand_pattern": "smooth"}], [
        {
            "store_id": 1,
            "product_id": 1,
            "target_date": origin + timedelta(days=i),
            "forecast_units": 2.0,
        }
        for i in range(1, 29)
    ]


def overall(
    rows: list[dict[str, Any]],
    model: str = "stocgain_v1",
    basis: str = "observed_in_stock",
) -> dict[str, Any]:
    return next(
        r
        for r in rows
        if r["model_name"] == model
        and r["evaluation_basis"] == basis
        and r["segment_type"] == "overall"
    )


def test_origins() -> None:
    config = AnalyticsConfig()
    origins = rolling_origins(T, T - timedelta(days=179), config)
    assert origins == [T - timedelta(days=i) for i in range(77, 27, -7)]
    assert rolling_origins(T, T - timedelta(days=83), config) == [
        T - timedelta(days=28)
    ]
    assert rolling_origins(T, T - timedelta(days=82), config) == []


def test_zero_actual_metrics_defined() -> None:
    history, truth = fixture()
    rows = evaluate(
        history,
        truth,
        POSITIONS,
        T,
        T - timedelta(days=83),
        AnalyticsConfig(),
        prediction,
    )
    row = overall(rows)
    assert row["mae"] == 2
    assert row["wape"] is None
    assert row["bias_rate"] is None
    assert row["n_observations"] == 28
    assert row["n_origins"] == 1
    assert row["forecast_units"] == 56
    assert row["abs_error_units"] == 56
    assert {
        r["segment_value"] for r in rows if r["segment_type"] == "velocity_class"
    } == {"C"}


def test_observed_basis_excludes_censored_but_not_promos() -> None:
    history, truth = fixture(1)
    history[0]["availability_status"] = "sold_out"
    history[1]["availability_status"] = "out_all_day"
    history[2]["is_promo_day"] = True
    rows = evaluate(
        history,
        truth,
        POSITIONS,
        T,
        T - timedelta(days=83),
        AnalyticsConfig(),
        prediction,
    )
    assert overall(rows)["n_observations"] == 26
    assert overall(rows)["actual_units"] == 26
    assert overall(rows)["wape"] == 1
    assert overall(rows)["bias_rate"] == 1
    assert overall(rows, basis="simulated_latent")["n_observations"] == 28
    buckets = [
        r
        for r in rows
        if r["model_name"] == "stocgain_v1"
        and r["evaluation_basis"] == "observed_in_stock"
        and r["segment_type"] == "horizon_bucket"
    ]
    assert sum(r["n_observations"] for r in buckets) == 26
    assert sum(r["abs_error_units"] for r in buckets) == 26


def test_baselines_independent_numerical_fixture() -> None:
    history, truth = fixture(0)
    origin = T - timedelta(days=28)
    for row in history:
        age = (origin - row["position_date"]).days
        if 0 <= age < 28:
            row["units_sold"] = 10
        if 0 <= age < 7:
            row["units_sold"] = 7 - age
        row["availability_status"] = "in_stock" if age < 0 else "sold_out"
    rows = evaluate(
        history,
        truth,
        POSITIONS,
        T,
        T - timedelta(days=83),
        AnalyticsConfig(),
        prediction,
    )
    naive = overall(rows, model="naive_28d_mean")
    assert naive["forecast_units"] == 238  # 21*10 + (1+...+7)
    assert naive["mae"] == 8.5
    seasonal = overall(rows, model="seasonal_naive_7d")
    assert seasonal["forecast_units"] == 112  # four repeats of sum(1..7)
    assert seasonal["mae"] == 4


def test_origin_callback_and_cutoff() -> None:
    history, truth = fixture(1)
    calls: list[date] = []

    def callback(origin: date) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        calls.append(origin)
        return prediction(origin)

    config = replace(AnalyticsConfig(), backtest_origins=1)
    first = evaluate(
        history, truth, POSITIONS, T, T - timedelta(days=83), config, callback
    )
    history.append(
        dict(history[0], position_date=T + timedelta(days=1), units_sold=1000)
    )
    truth.append(dict(truth[0], demand_date=T + timedelta(days=1), latent_units=1000))
    assert (
        evaluate(history, truth, POSITIONS, T, T - timedelta(days=83), config, callback)
        == first
    )
    assert calls == [T - timedelta(days=28)] * 2


def test_missing_target_rejected() -> None:
    history, truth = fixture()
    with pytest.raises(ValueError, match="complete observed and latent"):
        evaluate(
            history,
            truth[1:],
            POSITIONS,
            T,
            T - timedelta(days=83),
            AnalyticsConfig(),
            prediction,
        )


def test_abc_exact_boundaries_and_product_tie_break() -> None:
    # Revenues 80, 15, 5 have cumulative-before shares 0, .80, .95.
    history, truth = fixture(1)
    histories: list[dict[str, Any]] = []
    truths: list[dict[str, Any]] = []
    positions = [dict(POSITIONS[0], product_id=p) for p in (1, 2, 3)]
    for p, revenue in ((1, 80), (2, 15), (3, 5)):
        histories.extend(
            dict(r, product_id=p, net_sales_amount=revenue) for r in history
        )
        truths.extend(dict(r, product_id=p) for r in truth)

    def callback(origin: date) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        summaries, daily = prediction(origin)
        return (
            [dict(s, product_id=p) for p in (1, 2, 3) for s in summaries],
            [dict(d, product_id=p, forecast_units=p) for p in (1, 2, 3) for d in daily],
        )

    rows = evaluate(
        histories,
        truths,
        positions,
        T,
        T - timedelta(days=83),
        AnalyticsConfig(),
        callback,
    )
    segmented = {
        r["segment_value"]: r
        for r in rows
        if r["model_name"] == "stocgain_v1"
        and r["evaluation_basis"] == "simulated_latent"
        and r["segment_type"] == "velocity_class"
    }
    assert segmented["A"]["forecast_units"] == 28
    assert segmented["B"]["forecast_units"] == 56
    assert segmented["C"]["forecast_units"] == 84
