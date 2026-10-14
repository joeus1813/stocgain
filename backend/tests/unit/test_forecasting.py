"""Independent numerical and boundary checks for docs/05 §3."""

from dataclasses import replace
from datetime import date, timedelta
from typing import Any

import pytest

from stocgain.analytics.config import AnalyticsConfig
from stocgain.analytics.demand_patterns import classify
from stocgain.analytics.forecasting import forecast

T = date(2026, 9, 30)
POSITIONS = [{"store_id": 1, "product_id": 1, "category_id": 1}]


def history(
    values: list[float], statuses: list[str] | None = None
) -> list[dict[str, Any]]:
    return [
        {
            "store_id": 1,
            "product_id": 1,
            "category_id": 1,
            "position_date": T - timedelta(days=i),
            "units_sold": v,
            "availability_status": statuses[i] if statuses else "in_stock",
            "is_promo_day": False,
        }
        for i, v in enumerate(values)
    ]


def run(
    rows: list[dict[str, Any]], **kwargs: Any
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return forecast(
        rows,
        POSITIONS,
        kwargs.pop("dow", []),
        kwargs.pop("chain", []),
        kwargs.pop("scales", []),
        kwargs.pop("promotions", []),
        T,
        kwargs.pop("config", AnalyticsConfig()),
    )


def test_g4_independent_golden() -> None:
    values = [6, 0, 0, 3, 7, 6, 5, 0, 0, 0, 6, 7, 5, 6]
    statuses = ["out_all_day" if v == 0 else "in_stock" for v in values]
    statuses[3] = "sold_out"
    summary, _ = run(
        history(values, statuses),
        config=replace(AnalyticsConfig(), lookback_days=14, min_clean_days_full=7),
    )
    row = summary[0]
    assert row["base_daily_demand"] == pytest.approx(6.019, abs=0.002)
    assert row["daily_demand_std"] == pytest.approx(2.453, abs=0.002)
    assert row["censored_days"] == 6
    assert row["clean_days"] == 8
    assert sum(values) / 14 == pytest.approx(3.643, abs=0.001)


def test_constant_and_zero() -> None:
    for value in (0, 5):
        summary, daily = run(history([value] * 56))
        row = summary[0]
        assert row["base_daily_demand"] == pytest.approx(value)
        assert row["daily_demand_std"] == pytest.approx(value**0.5)
        assert row["observed_demand_cv"] == (0 if value else None)
        for horizon in (7, 14, 28):
            assert row[f"forecast_{horizon}d_units"] == pytest.approx(
                sum(r["forecast_units"] for r in daily[:horizon])
            )
            assert row[f"forecast_{horizon}d_std_units"] == pytest.approx(
                (value * horizon) ** 0.5
            )
        if not value:
            assert row["demand_pattern"] == "no_demand"


@pytest.mark.parametrize(
    "n,method,expected",
    [
        (14, "store_sku", 5),
        (10, "blended", 45 / 7),
        (3, "chain_fallback", 10),
        (0, "chain_fallback", 10),
    ],
)
def test_fallback(n: int, method: str, expected: float) -> None:
    rows = history([5] * 56, ["in_stock"] * n + ["out_all_day"] * (56 - n))
    summary, _ = run(
        rows, chain=[{"product_id": 1, "chain_rate": 10, "n_clean_chain": 20}]
    )
    assert summary[0]["method"] == method
    assert summary[0]["base_daily_demand"] == pytest.approx(expected)
    if n < 7:
        assert summary[0]["daily_demand_std"] == expected


def test_full_history_then_insufficient() -> None:
    rows = history([0] * 56, ["out_all_day"] * 56)
    summary, _ = run(
        rows,
        chain=[
            {
                "product_id": 1,
                "chain_rate": None,
                "n_clean_chain": 0,
                "chain_rate_full_history": 8,
                "n_clean_chain_full_history": 7,
            }
        ],
        scales=[{"store_id": 1, "category_id": 1, "store_scale": 1.5}],
    )
    assert summary[0]["base_daily_demand"] == 12
    summary, _ = run(rows)
    assert summary[0]["method"] == "insufficient_data"
    assert summary[0]["base_daily_demand"] == 0


def test_weekday_and_promo() -> None:
    indices = [0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3]
    rows = history([10 * indices[(T - timedelta(days=i)).weekday()] for i in range(56)])
    rows[0].update(units_sold=1000, is_promo_day=True)
    dow = [
        {"category_id": 1, "iso_day_of_week": k + 1, "n_obs": 30, "dow_index": v}
        for k, v in enumerate(indices)
    ]
    summary, daily = run(
        rows,
        dow=dow,
        promotions=[
            {
                "store_id": 1,
                "product_id": 1,
                "target_date": T + timedelta(days=1),
                "promotion_id": 2,
                "planned_lift": 1.35,
            }
        ],
    )
    assert summary[0]["base_daily_demand"] == pytest.approx(10)
    assert daily[0]["forecast_units"] == pytest.approx(
        13.5 * indices[(T + timedelta(days=1)).weekday()]
    )
    assert summary[0]["promo_days"] == 1
    dow[0]["n_obs"] = 29
    _, flat = run(history([5] * 56), dow=dow)
    assert all(r["forecast_units"] == pytest.approx(5) for r in flat)


def test_cutoff_and_missing(caplog: pytest.LogCaptureFixture) -> None:
    rows = history([5] * 56)
    baseline = run(rows)
    future = dict(rows[0], position_date=T + timedelta(days=1), units_sold=10000)
    ancient = dict(rows[0], position_date=T - timedelta(days=56), units_sold=10000)
    assert run([*rows, future, ancient]) == baseline
    summary, _ = run(rows[1:])
    assert summary[0]["base_daily_demand"] == pytest.approx(5)
    assert summary[0]["censored_days"] == 1
    assert "missing position-days" in caplog.text


def test_trend_requires_four_and_does_not_multiply_forecast() -> None:
    rows = history([10] * 14 + [5] * 42)
    summary, daily = run(rows)
    assert summary[0]["demand_trend_ratio"] == 2
    assert daily[0]["forecast_units"] == summary[0]["base_daily_demand"]
    for row in rows[3:14]:
        row["availability_status"] = "sold_out"
    assert run(rows)[0][0]["demand_trend_ratio"] is None


@pytest.mark.parametrize(
    "adi,cv2,expected",
    [
        (None, 0, "no_demand"),
        (1.32, 0.489999, "smooth"),
        (1.32, 0.49, "erratic"),
        (1.320001, 0.489999, "intermittent"),
        (1.320001, 0.49, "lumpy"),
    ],
)
def test_pattern_boundaries(adi: float | None, cv2: float, expected: str) -> None:
    assert classify(adi, cv2) == expected


def test_intermittent_and_chain_pattern() -> None:
    rows = history([1 if i in (0, 20, 40) else 0 for i in range(56)])
    row = run(rows)[0][0]
    assert row["demand_pattern"] == "intermittent"
    assert row["adi"] == pytest.approx(56 / 3)
    assert row["cv_squared"] == 0
    other = [dict(r, store_id=2) for r in rows]
    censored = history([0] * 56, ["out_all_day"] * 56)
    summaries, _ = forecast(
        [*censored, *other],
        [*POSITIONS, dict(POSITIONS[0], store_id=2)],
        [],
        [],
        [],
        [],
        T,
        AnalyticsConfig(),
    )
    assert summaries[0]["demand_pattern"] == "intermittent"


def test_pattern_uses_nonzero_sample_variance_and_raw_units() -> None:
    rows = history([1, 3] + [0] * 54)
    row = run(rows)[0][0]
    assert row["adi"] == 28
    assert row["cv_squared"] == pytest.approx(0.5)
    assert row["demand_pattern"] == "lumpy"


def test_randomized_nonnegative_horizons_and_poisson_floor() -> None:
    import numpy as np

    rng = np.random.default_rng(8721)
    for _ in range(15):
        values = rng.poisson(rng.uniform(0, 20), 56).astype(float).tolist()
        rows = history(values)
        for row, is_clean in zip(rows, rng.random(56) > 0.2, strict=True):
            if not is_clean:
                row["availability_status"] = "sold_out"
        row, daily = run(rows)
        result = row[0]
        assert result["base_daily_demand"] >= 0
        assert result["daily_demand_std"] ** 2 >= result["base_daily_demand"] - 1e-10
        assert (
            0
            <= result["forecast_7d_units"]
            <= result["forecast_14d_units"]
            <= result["forecast_28d_units"]
        )
        assert all(d["forecast_units"] >= 0 for d in daily)


def test_empty_positions() -> None:
    assert forecast([], [], [], [], [], [], T, AnalyticsConfig()) == ([], [])
