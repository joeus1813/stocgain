"""Deterministic fictional catalog and supplier lanes (docs/06 §3)."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np

from stocgain.generator.config import GeneratorConfig
from stocgain.generator.rng import stream

Rows = dict[str, list[tuple[Any, ...]]]


@dataclass
class Catalog:
    """Operational rows and private simulator parameters, never model features."""

    tables: Rows
    products: list[dict[str, Any]]
    stores: list[dict[str, Any]]
    suppliers: dict[int, dict[str, Any]]
    lanes: dict[tuple[int, int], tuple[int, int]]
    affinity: Any
    demo_el: int
    demo_pl: int


def build_catalog(config: GeneratorConfig, seed: int) -> Catalog:
    """Build stable IDs, supplier relationships, prices and calendar rows."""
    raw, sel = config.raw, config.selection
    rng, srng, lrng = (stream(seed, n) for n in ("catalog", "suppliers", "lanes"))
    params = raw["simulation"]
    tables: Rows = {
        n: []
        for n in (
            "regions",
            "product_categories",
            "stores",
            "suppliers",
            "products",
            "product_suppliers",
            "supplier_store_lanes",
            "calendar",
        )
    }
    regions = {r["code"]: i + 1 for i, r in enumerate(raw["regions"])}
    tables["regions"] = [
        (i + 1, r["code"], r["name"]) for i, r in enumerate(raw["regions"])
    ]
    stores = [
        dict(s)
        for s in raw["stores"]
        if sel["stores"] == "all" or s["code"] in sel["stores"]
    ]
    if sel["stores"] == "all_plus_generated":
        raise ValueError(
            "The optional large preset is not implemented; use small or standard."
        )
    for s in stores:
        s["region_id"] = regions[s["region"]]
        tables["stores"].append(
            (
                s["store_id"],
                s["code"],
                s["name"],
                s["city"],
                s["state"],
                s["region_id"],
                date.fromisoformat(s["opened"]),
                s["sqft"],
                True,
            )
        )
    products: list[dict[str, Any]] = []
    suppliers: dict[int, dict[str, Any]] = {}
    demo_el = demo_pl = 0
    prefixes = [
        "Ashford",
        "Bluewater",
        "Cedarline",
        "Copperfield",
        "Eastbrook",
        "Gulfmark",
        "Granite Peak",
        "Harborview",
        "Ironbridge",
        "Juniper",
        "Kingsway",
        "Lakeshore",
        "Meridian",
        "Northbay",
        "Oakhaven",
        "Pinecrest",
        "Quarry Hill",
        "Redstone",
        "Silverline",
        "Summit Ridge",
        "Tidewater",
        "Valleyfield",
        "Westmont",
        "Yellowpine",
    ]
    words = [
        "Tool",
        "Tool & Hardware",
        "Electric",
        "Plumbing",
        "Building Products",
        "Garden & Outdoor",
        "Coatings",
        "Fastener",
    ]
    suffixes = [
        "Supply Co.",
        "Distributors",
        "Industries",
        "Products Inc.",
        "Wholesale",
        "Manufacturing",
    ]
    used: set[str] = {"Lakeshore Electric Distributors", "Gulfmark Plumbing Supply Co."}
    for ci, c in enumerate(raw["categories"]):
        code = c["code"]
        count = sel["skus_per_category"][code]
        tables["product_categories"].append((ci + 1, code, c["name"]))
        ids = []
        for j in range(sel["suppliers_per_category"][code]):
            sid = len(suppliers) + 1
            ids.append(sid)
            while True:
                name = f"{srng.choice(prefixes)} {words[ci]} {srng.choice(suffixes)}"
                if name not in used:
                    break
            if code == "EL" and j == (2 if config.preset == "standard" else 0):
                demo_el = sid
                name = "Lakeshore Electric Distributors"
            if code == "PL" and j == (2 if config.preset == "standard" else 0):
                demo_pl = sid
                name = "Gulfmark Plumbing Supply Co."
            used.add(name)
            low, high = c["lead_time_range"]
            supplier = {
                "base_lt": int(srng.integers(low, high + 1)),
                "p": float(
                    np.clip(
                        srng.beta(*params["supplier_ontime_beta"]),
                        *params["supplier_ontime_clip"],
                    )
                ),
                "late_lambda": float(
                    srng.uniform(*params["supplier_late_lambda_range"])
                ),
            }
            if sid == demo_pl and raw["events"]["enabled"]:
                supplier.update(
                    p=raw["events"]["plumbing"]["on_time_probability"],
                    late_lambda=raw["events"]["plumbing"]["late_lambda"],
                )
            suppliers[sid] = supplier
            tables["suppliers"].append((sid, f"SUP-{sid:03}", name, ci + 1, True))
        # Balanced shuffled assignment guarantees >=3 products/supplier on standard.
        assignments = np.resize(np.asarray(ids), count)
        rng.shuffle(assignments)
        for j in range(count):
            pid = len(products) + 1
            item = j % len(c["items"])
            base = c["items"][item]
            price = float(
                np.exp(rng.uniform(np.log(c["price"][0]), np.log(c["price"][1])))
            )
            if "Generator" in base or "Mower" in base or "Water Heater" in base:
                price = c["price"][1]
            ending = float(rng.choice([0.01, 0.02, 0.03]))
            price = round(price) - ending
            if price < c["price"][0]:
                price = float(np.ceil(c["price"][0] + ending)) - ending
            price = round(price, 2)
            cost = round(price * (1 - rng.uniform(*c["margin"])), 2)
            weights = np.asarray(c["velocity_mix"], dtype=float)
            if price > 200:
                weights[:2] = 0
            elif price >= 50:
                weights[0] = 0
            tier = int(rng.choice(4, p=weights / weights.sum()))
            rate = float(np.exp(rng.uniform(*np.log(params["velocity_ranges"][tier]))))
            pack = (
                int(rng.choice([10, 20, 40]))
                if code == "BM"
                else (
                    1
                    if price > 100
                    else int(rng.choice([2, 4, 6] if price >= 20 else [6, 10, 12, 24]))
                )
            )
            moq = pack * (int(rng.integers(1, 3)) if price > 100 else 2)
            primary = int(assignments[j])
            brand = c["brands"][j % 2]
            unit = (
                "gallon"
                if code == "PA" and item < 3
                else "bag"
                if code == "LG" and item in (1, 2, 3, 4)
                else "pack"
                if "Kit" in base or "Pack" in base
                else "each"
            )
            introduced = date(2019, 1, 1) + timedelta(
                days=int(
                    rng.integers(
                        0,
                        (
                            config.history_start
                            - timedelta(days=120)
                            - date(2019, 1, 1)
                        ).days
                        + 1,
                    )
                )
            )
            tables["products"].append(
                (
                    pid,
                    f"{code}-{10000 + pid}",
                    f"{brand} {base} - Variant {j // len(c['items']) + 1}",
                    ci + 1,
                    brand,
                    unit,
                    price,
                    cost,
                    introduced,
                    True,
                )
            )
            tables["product_suppliers"].append((pid, primary, True, pack, moq))
            if len(ids) > 1 and rng.random() < params["secondary_supplier_probability"]:
                secondary = int(rng.choice([i for i in ids if i != primary]))
                tables["product_suppliers"].append((pid, secondary, False, pack, moq))
            products.append(
                {
                    "id": pid,
                    "category": ci,
                    "primary": primary,
                    "price": price,
                    "cost": cost,
                    "pack": pack,
                    "moq": moq,
                    "tier": tier,
                    "base": rate,
                    "dispersion": float(
                        rng.choice(
                            params["dispersion_values"],
                            p=np.asarray(c["dispersion_mix"]) / 100,
                        )
                    ),
                    "trend": float(rng.uniform(*params["trend_range"])),
                    "buffer": float(rng.uniform(*params["policy_buffer_range"])),
                    "storm": (code == "EL" and item < 5) or (code == "BM" and item < 2),
                }
            )
    tables["product_suppliers"].sort()
    lanes = {}
    for sid, supplier in suppliers.items():
        for s in stores:
            lt = (
                supplier["base_lt"]
                + raw["regions"][s["region_id"] - 1]["lead_time_offset"]
                + int(lrng.random() < params["lane_extra_day_probability"])
            )
            weekday = int(lrng.integers(1, 6))
            lanes[(sid, s["store_id"])] = (lt, weekday)
            tables["supplier_store_lanes"].append(
                (sid, s["store_id"], lt, weekday, True)
            )
    holidays = {
        "2026-05-25": "Memorial Day",
        "2026-07-04": "Independence Day",
        "2026-09-07": "Labor Day",
        "2025-09-01": "Labor Day",
        "2025-11-27": "Thanksgiving",
        "2025-12-25": "Christmas",
        "2026-01-01": "New Year's Day",
    }
    start = config.history_start - timedelta(days=config.burn_in_days)
    for i in range((config.history_end + timedelta(days=90) - start).days + 1):
        d = start + timedelta(days=i)
        iso = d.isocalendar()
        tables["calendar"].append(
            (
                d,
                iso.year,
                iso.week,
                iso.weekday,
                d.strftime("%A"),
                d.month,
                d.strftime("%B"),
                (d.month - 1) // 3 + 1,
                d - timedelta(days=d.weekday()),
                d.weekday() >= 5,
                holidays.get(d.isoformat()),
            )
        )
    return Catalog(
        tables,
        products,
        stores,
        suppliers,
        lanes,
        rng.lognormal(0, params["region_affinity_sigma"], (4, 8)),
        demo_el,
        demo_pl,
    )
