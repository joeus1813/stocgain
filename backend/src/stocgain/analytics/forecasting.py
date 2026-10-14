"""Pure censoring-aware daily demand forecasting, docs/05 §3."""

import logging
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any

import numpy as np

from stocgain.analytics.config import AnalyticsConfig
from stocgain.analytics.demand_patterns import classify, pattern_statistics

logger = logging.getLogger(__name__)


def forecast(
    history: Sequence[Mapping[str, Any]],
    positions: Sequence[Mapping[str, Any]],
    dow: Sequence[Mapping[str, Any]],
    chain: Sequence[Mapping[str, Any]],
    scales: Sequence[Mapping[str, Any]],
    promotions: Sequence[Mapping[str, Any]],
    as_of: date,
    config: AnalyticsConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return summary and daily rows in units, without run IDs; docs/05 §3.3–10.

    Aggregated DOW, chain and scale inputs must be extracted at ``as_of``.
    History is defensively cutoff-filtered and missing grid cells are censored.
    """
    if not positions:
        return [], []
    size, days = len(positions), config.lookback_days
    keys = [(int(p["store_id"]), int(p["product_id"])) for p in positions]
    index = {key: i for i, key in enumerate(keys)}
    units = np.zeros((size, days))
    clean = np.zeros((size, days), dtype=bool)
    promo = np.zeros((size, days), dtype=bool)
    seen = np.zeros((size, days), dtype=bool)
    censored = np.zeros((size, days), dtype=bool)
    for row in history:
        age = (as_of - row["position_date"]).days
        i = index.get((row["store_id"], row["product_id"]))
        if i is None or not 0 <= age < days:
            continue
        if seen[i, age]:
            raise ValueError("Duplicate position-day in forecast history")
        seen[i, age] = True
        units[i, age] = float(row["units_sold"])
        promo[i, age] = bool(row["is_promo_day"])
        clean[i, age] = row["availability_status"] == "in_stock" and not promo[i, age]
        censored[i, age] = row["availability_status"] in ("sold_out", "out_all_day")
    if not seen.all():
        logger.warning("Forecast history has %d missing position-days", (~seen).sum())
    censored |= ~seen
    profiles: dict[int, dict[int, Mapping[str, Any]]] = {}
    for row in dow:
        profiles.setdefault(int(row["category_id"]), {})[
            int(row["iso_day_of_week"])
        ] = row
    weekday = np.ones((size, 7))
    for i, position in enumerate(positions):
        profile = profiles.get(int(position["category_id"]), {})
        if len(profile) == 7 and all(
            int(r["n_obs"]) >= config.dow_min_observations
            and r["dow_index"] is not None
            and float(r["dow_index"]) > 0
            for r in profile.values()
        ):
            weekday[i] = [float(profile[k]["dow_index"]) for k in range(1, 8)]
    historical_dow = [(as_of - timedelta(days=a)).weekday() for a in range(days)]
    z = units / weekday[:, historical_dow]
    weights = clean * np.power(0.5, np.arange(days) / config.half_life_days)
    weight_sum = weights.sum(axis=1)
    level = np.divide(
        (weights * z).sum(axis=1),
        weight_sum,
        out=np.zeros(size),
        where=weight_sum > 0,
    )
    variance = np.divide(
        (weights * (z - level[:, None]) ** 2).sum(axis=1),
        weight_sum,
        out=np.zeros(size),
        where=weight_sum > 0,
    )
    observed_std = np.sqrt(variance)
    count = clean.sum(axis=1)
    chain_by_product = {int(r["product_id"]): r for r in chain}
    scale_by_key = {
        (r["store_id"], r["category_id"]): float(r["store_scale"])
        for r in scales
        if r["store_scale"] is not None
    }
    methods: list[str] = []
    for i, position in enumerate(positions):
        row = chain_by_product.get(int(position["product_id"]), {})
        scale = scale_by_key.get((position["store_id"], position["category_id"]), 1.0)
        chain_level = float(row.get("chain_rate") or 0) * scale
        if count[i] >= config.min_clean_days_full:
            methods.append("store_sku")
        elif count[i] >= config.min_clean_days_blend:
            fraction = count[i] / config.min_clean_days_full
            level[i] = fraction * level[i] + (1 - fraction) * chain_level
            methods.append("blended")
        elif int(row.get("n_clean_chain", 0)) >= config.min_clean_days_blend:
            level[i] = observed_std[i] = chain_level
            methods.append("chain_fallback")
        elif (
            int(row.get("n_clean_chain_full_history", 0)) >= config.min_clean_days_blend
        ):
            level[i] = observed_std[i] = float(row["chain_rate_full_history"]) * scale
            methods.append("chain_fallback")
        else:
            level[i] = observed_std[i] = 0
            methods.append("insufficient_data")
    std = np.where(level > 0, np.maximum(observed_std, np.sqrt(level)), 0)
    adi, cv2 = pattern_statistics(units, clean)
    for product in sorted({key[1] for key in keys}):
        members = np.array([i for i, key in enumerate(keys) if key[1] == product])
        sparse = members[count[members] < config.min_clean_days_blend]
        if sparse.size:
            pooled_adi, pooled_cv2 = pattern_statistics(
                units[members].reshape(1, -1), clean[members].reshape(1, -1)
            )
            adi[sparse], cv2[sparse] = pooled_adi[0], pooled_cv2[0]
    recent = clean.copy()
    recent[:, 14:] = False
    older = clean.copy()
    older[:, :14] = False
    n_recent, n_older = recent.sum(axis=1), older.sum(axis=1)
    mean_recent = np.divide(
        (z * recent).sum(axis=1), n_recent, out=np.zeros(size), where=n_recent > 0
    )
    mean_older = np.divide(
        (z * older).sum(axis=1), n_older, out=np.zeros(size), where=n_older > 0
    )
    trend = np.divide(
        mean_recent,
        mean_older,
        out=np.full(size, np.nan),
        where=(n_recent >= 4) & (n_older >= 4) & (mean_older > 0),
    )
    dates = [
        as_of + timedelta(days=t) for t in range(1, config.forecast_horizon_days + 1)
    ]
    future_dow = weekday[:, [d.weekday() for d in dates]]
    multipliers = np.ones_like(future_dow)
    promotion_ids: dict[tuple[int, int], int] = {}
    for row in promotions:
        i = index.get((row["store_id"], row["product_id"]))
        t = (row["target_date"] - as_of).days - 1
        if i is not None and 0 <= t < len(dates):
            if (i, t) in promotion_ids:
                raise ValueError("Overlapping planned promotions for position-day")
            multipliers[i, t] = float(row["planned_lift"])
            promotion_ids[i, t] = int(row["promotion_id"])
    daily = level[:, None] * future_dow * multipliers
    summaries: list[dict[str, Any]] = []
    daily_rows: list[dict[str, Any]] = []
    for i, (store_id, product_id) in enumerate(keys):
        pattern_adi = None if np.isnan(adi[i]) else float(adi[i])
        summary: dict[str, Any] = {
            "store_id": store_id,
            "product_id": product_id,
            "method": methods[i],
            "demand_pattern": classify(pattern_adi, float(cv2[i])),
            "lookback_days": days,
            "clean_days": int(count[i]),
            "censored_days": int(censored[i].sum()),
            "promo_days": int(promo[i].sum()),
            "base_daily_demand": float(level[i]),
            "daily_demand_std": float(std[i]),
            "observed_demand_cv": float(observed_std[i] / level[i])
            if level[i]
            else None,
            "demand_trend_ratio": None if np.isnan(trend[i]) else float(trend[i]),
            "adi": pattern_adi,
            "cv_squared": float(cv2[i]),
        }
        for horizon in (7, 14, 28):
            summary[f"forecast_{horizon}d_units"] = float(daily[i, :horizon].sum())
            summary[f"forecast_{horizon}d_std_units"] = float(std[i] * np.sqrt(horizon))
        summaries.append(summary)
        for t, target_date in enumerate(dates):
            daily_rows.append(
                {
                    "store_id": store_id,
                    "product_id": product_id,
                    "target_date": target_date,
                    "horizon_day": t + 1,
                    "forecast_units": float(daily[i, t]),
                    "dow_index": float(future_dow[i, t]),
                    "promo_multiplier": float(multipliers[i, t]),
                    "promotion_id": promotion_ids.get((i, t)),
                }
            )
    return summaries, daily_rows
