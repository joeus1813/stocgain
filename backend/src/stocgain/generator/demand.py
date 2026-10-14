"""Expected demand multipliers and Negative Binomial draws (docs/06 §5)."""

from datetime import date
from typing import Any

import numpy as np

from stocgain.generator.catalog import Catalog
from stocgain.generator.config import GeneratorConfig


def seasonality(config: GeneratorConfig, catalog: Catalog, day: date) -> Any:
    """Return per-position seasonal multipliers, sorted store then product."""
    values = []
    for s in catalog.stores:
        shift = config.raw["regions"][s["region_id"] - 1]["season_shift"]
        for p in catalog.products:
            base, amp, peak, width = config.raw["categories"][p["category"]]["season"]
            values.append(
                base
                + amp
                * np.exp(
                    -0.5 * ((day.timetuple().tm_yday - (peak + shift)) / width) ** 2
                )
            )
    return np.asarray(values)


def expected_demand(
    config: GeneratorConfig,
    catalog: Catalog,
    promotions: list[dict[str, Any]],
    day: date,
    day_index: int,
    total_days: int,
) -> tuple[Any, Any]:
    """Return latent NB means (units/day) and applicable price discounts."""
    ps = catalog.products
    n = len(ps)
    s_count = len(catalog.stores)
    category = np.tile([p["category"] for p in ps], s_count)
    regions = np.repeat([s["region_id"] for s in catalog.stores], n)
    ids = np.tile([p["id"] for p in ps], s_count)
    base = np.tile([p["base"] for p in ps], s_count)
    volume = np.repeat([s["volume"] for s in catalog.stores], n)
    affinity = catalog.affinity[regions - 1, category]
    dow = np.asarray([c["dow"] for c in config.raw["categories"]], dtype=float)
    dow = dow / dow.mean(axis=1)[:, None]
    means = (
        base
        * volume
        * affinity
        * seasonality(config, catalog, day)
        * dow[category, day.weekday()]
    )
    means *= 1 + np.tile([p["trend"] for p in ps], s_count) * day_index / total_days
    codes = [c["code"] for c in config.raw["categories"]]
    for holiday in config.raw["holiday_windows"]:
        if (
            date.fromisoformat(holiday["start"])
            <= day
            <= date.fromisoformat(holiday["end"])
        ):
            members = [codes.index(code) for code in holiday["categories"]]
            means *= np.where(np.isin(category, members), holiday["factor"], 1)
    discount = np.zeros_like(means)
    for promo in promotions:
        if promo["start"] <= day <= promo["end"]:
            mask = np.isin(ids, promo["products"]) & (
                (regions == promo["region"]) if promo["region"] is not None else True
            )
            means[mask] *= promo["realized"]
            discount[mask] = promo["discount"]
    event = config.raw["events"]["storm"]
    start = date.fromisoformat(event["start"])
    end = date.fromisoformat(event["end"])
    if config.raw["events"]["enabled"] and start <= day <= end:
        factor = (
            event["start_multiplier"]
            + (event["end_multiplier"] - event["start_multiplier"])
            * (day - start).days
            / (end - start).days
        )
        mask = (regions == 1) & np.tile([p["storm"] for p in ps], s_count)
        means[mask] *= factor
    return means, discount
