"""Nonoverlapping planned promotions and private realized lifts (docs/06 §5.4)."""

from datetime import date, timedelta
from typing import Any

from stocgain.generator.catalog import Catalog
from stocgain.generator.config import GeneratorConfig
from stocgain.generator.rng import stream


def build_promotions(
    config: GeneratorConfig, catalog: Catalog, seed: int
) -> list[dict[str, Any]]:
    """Generate plans through history end + 42 days; never overlap product scopes."""
    rng = stream(seed, "promotions")
    params = config.raw["promotion_model"]
    promotions: list[dict[str, Any]] = []
    elasticity = rng.uniform(*params["elasticity_range"], size=8)

    def add(ci: int, start: date, region: int | None) -> None:
        end = start + timedelta(
            days=int(
                rng.integers(params["duration_days"][0], params["duration_days"][1] + 1)
            )
            - 1
        )
        candidates = [
            p["id"]
            for p in catalog.products
            if p["category"] == ci
            and p["tier"] != 3
            and not any(
                p["id"] in old["products"]
                and start <= old["end"]
                and end >= old["start"]
                and (region is None or old["region"] is None or region == old["region"])
                for old in promotions
            )
        ]
        low, high = params[
            "products_small" if config.preset == "small" else "products_standard"
        ]
        if not candidates:
            return
        members = sorted(
            int(x)
            for x in rng.choice(
                candidates,
                size=min(len(candidates), int(rng.integers(low, high + 1))),
                replace=False,
            )
        )
        discount = (
            round(
                float(rng.uniform(*params["discount_range"])) / params["discount_step"]
            )
            * params["discount_step"]
        )
        discount = round(discount, 3)
        planned = round(min(2.5, max(1.05, 1 + elasticity[ci] * discount)), 2)
        promotions.append(
            {
                "id": len(promotions) + 1,
                "category": ci,
                "region": region,
                "start": start,
                "end": end,
                "discount": discount,
                "planned": planned,
                "realized": planned
                * float(rng.uniform(*params["realized_multiplier_range"])),
                "products": members,
            }
        )

    if config.raw["events"]["enabled"]:
        event = config.raw["events"]["fall_promotions"]
        codes = [category["code"] for category in config.raw["categories"]]
        for code in event["categories"]:
            add(codes.index(code), date.fromisoformat(event["start"]), None)
    for ci in range(8):
        current = config.history_start - timedelta(days=config.burn_in_days)
        while current <= config.history_end + timedelta(days=params["future_days"]):
            region = (
                None
                if rng.random() < params["chain_probability"]
                else int(rng.integers(1, 5))
            )
            add(ci, current, region)
            current += timedelta(
                days=int(
                    rng.integers(
                        params["cadence_days"][0], params["cadence_days"][1] + 1
                    )
                )
            )
    catalog.tables["promotions"] = []
    catalog.tables["promotion_products"] = []
    for promo in promotions:
        ci = promo["category"]
        season = (
            "Fall"
            if promo["start"].month >= 9
            else "Summer"
            if promo["start"].month >= 6
            else "Spring"
        )
        catalog.tables["promotions"].append(
            (
                promo["id"],
                f"PRM-{promo['id']:04}",
                f"{season} {config.raw['categories'][ci]['name']} Event",
                promo["region"],
                promo["start"],
                promo["end"],
                promo["discount"],
                promo["planned"],
            )
        )
        catalog.tables["promotion_products"].extend(
            (promo["id"], p) for p in promo["products"]
        )
    return promotions
