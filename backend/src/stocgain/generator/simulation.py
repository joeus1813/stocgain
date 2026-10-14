"""Causal inventory simulation with vectorized position state (docs/06 §6)."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np

from stocgain.generator.catalog import Rows, build_catalog
from stocgain.generator.config import GeneratorConfig
from stocgain.generator.demand import expected_demand, seasonality
from stocgain.generator.promotions import build_promotions
from stocgain.generator.rng import stream


@dataclass
class Dataset:
    """Deterministic rows plus in-memory validation diagnostics."""

    config: GeneratorConfig
    seed: int
    tables: Rows
    diagnostics: dict[str, Any]


def simulate(config: GeneratorConfig, seed: int) -> Dataset:
    """Simulate burn-in and dense history; physical quantities are integer units."""
    catalog = build_catalog(config, seed)
    promos = build_promotions(config, catalog, seed)
    tables = catalog.tables
    ps = catalog.products
    stores = catalog.stores
    for name in (
        "purchase_orders",
        "purchase_order_lines",
        "inventory_receipts",
        "inventory_adjustments",
        "daily_sales",
        "inventory_snapshots",
        "latent_demand",
    ):
        tables[name] = []
    n = len(ps)
    positions = n * len(stores)
    params = config.raw["simulation"]
    start = config.history_start - timedelta(days=config.burn_in_days)
    total = (config.history_end - start).days + 1
    history_days = (config.history_end - config.history_start).days + 1
    drng, frng, arng, erng = (
        stream(seed, k) for k in ("demand", "fulfillment", "adjustments", "events")
    )
    pack = np.tile([p["pack"] for p in ps], len(stores))
    moq = np.tile([p["moq"] for p in ps], len(stores))
    primary = np.tile([p["primary"] for p in ps], len(stores))
    store_ids = np.repeat([s["store_id"] for s in stores], n)
    product_ids = np.tile([p["id"] for p in ps], len(stores))
    lead = np.asarray(
        [
            catalog.lanes[(int(sup), int(st))][0]
            for sup, st in zip(primary, store_ids, strict=True)
        ]
    )
    review = np.asarray(
        [
            catalog.lanes[(int(sup), int(st))][1]
            for sup, st in zip(primary, store_ids, strict=True)
        ]
    )
    price = np.tile([p["price"] for p in ps], len(stores))
    cost = np.tile([p["cost"] for p in ps], len(stores))
    presentation = np.where(price > 100, 2, pack)
    regions = np.repeat([s["region_id"] for s in stores], n)
    categories = np.tile([p["category"] for p in ps], len(stores))
    initial = (
        np.tile([p["base"] for p in ps], len(stores))
        * np.repeat([s["volume"] for s in stores], n)
        * catalog.affinity[regions - 1, categories]
        * seasonality(config, catalog, start)
    )
    on_hand = (
        np.ceil(
            initial * (lead + params["review_period_days"]) * params["initial_buffer"]
        ).astype(np.int64)
        + presentation
    )
    on_order = np.zeros(positions, dtype=np.int64)
    sales_buffer = np.zeros((params["sales_lookback_days"], positions), dtype=np.int64)
    scheduled: dict[date, list[tuple[int, int, int]]] = defaultdict(list)
    diagnostics = {
        key: np.zeros((history_days, positions), dtype=np.int64)
        for key in ("opening", "closing", "received", "sold", "adjusted", "latent")
    }
    means_history = np.zeros((history_days, positions))
    dispersion = np.tile([p["dispersion"] for p in ps], len(stores))
    buffer = np.tile([p["buffer"] for p in ps], len(stores))
    po_id = 100001
    line_id = 300001
    receipt_id = 500001
    adjustment_id = 70001
    demo_received = []
    for di in range(total):
        day = start + timedelta(days=di)
        hi = di - config.burn_in_days
        opening = on_hand.copy()
        received = np.zeros(positions, dtype=np.int64)
        for lid, pos, qty in scheduled.pop(day, []):
            received[pos] += qty
            on_order[pos] -= qty
            tables["inventory_receipts"].append((receipt_id, lid, day, qty))
            receipt_id += 1
        available = opening + received
        means, discount = expected_demand(config, catalog, promos, day, di, total)
        latent = drng.negative_binomial(dispersion, dispersion / (dispersion + means))
        latent = np.where(means < 1e-6, 0, latent)
        sold = np.minimum(latent, available)
        on_hand = available - sold
        adjusted = np.zeros(positions, dtype=np.int64)
        for ri, reason in enumerate(
            ("shrink", "damage", "cycle_count_correction", "vendor_return")
        ):
            selected = arng.random(positions) < params["adjustment_probabilities"][ri]
            delta = -arng.integers(
                1, params["adjustment_max_units"][ri] + 1, size=positions
            )
            if ri == 2:
                delta *= arng.choice([-1, 1], size=positions)
            delta = np.where(selected, np.maximum(delta, -on_hand), 0)
            on_hand += delta
            adjusted += delta
            if hi >= 0:
                for raw_pos in np.flatnonzero(delta):
                    pos = int(raw_pos)
                    tables["inventory_adjustments"].append(
                        (
                            adjustment_id,
                            int(store_ids[pos]),
                            int(product_ids[pos]),
                            day,
                            int(delta[pos]),
                            reason,
                        )
                    )
                    adjustment_id += 1
        sales_buffer[di % len(sales_buffer)] = sold
        avg = sales_buffer.sum(axis=0) / min(di + 1, len(sales_buffer))
        ip = on_hand + on_order
        reorder = np.ceil(avg * lead * buffer).astype(np.int64) + presentation
        target = (
            np.ceil(avg * (lead + params["review_period_days"]) * buffer).astype(
                np.int64
            )
            + presentation
        )
        selected = np.flatnonzero((review == day.isoweekday()) & (ip <= reorder))
        groups: dict[tuple[int, int], list[int]] = defaultdict(list)
        for raw_pos in selected:
            pos = int(raw_pos)
            groups[(int(primary[pos]), int(store_ids[pos]))].append(int(pos))
        for (sid, stid), members in sorted(groups.items()):
            lt = catalog.lanes[(sid, stid)][0]
            promised = day + timedelta(days=lt)
            supplier = catalog.suppliers[sid]
            u = frng.random()
            delay = (
                -1
                if u < params["early_probability"]
                else 0
                if u < params["early_probability"] + supplier["p"]
                else 1 + int(frng.poisson(supplier["late_lambda"]))
            )
            event = config.raw["events"]["electrical_delay"]
            if (
                config.raw["events"]["enabled"]
                and sid == catalog.demo_el
                and day >= date.fromisoformat(event["start"])
                and erng.random() < event["probability"]
            ):
                delay += event["days"]
            arrival = max(day + timedelta(days=1), promised + timedelta(days=delay))
            if sid == catalog.demo_pl and arrival <= config.history_end:
                demo_received.append(arrival <= promised)
            tables["purchase_orders"].append(
                (po_id, f"PO-{po_id}", sid, stid, day, promised)
            )
            for number, pos in enumerate(members, 1):
                qty = max(
                    int(moq[pos]),
                    int(np.ceil((target[pos] - ip[pos]) / pack[pos])) * int(pack[pos]),
                )
                behavior = int(frng.choice(3, p=params["fill_probabilities"]))
                cancelled = 0
                if behavior == 0:
                    shipments = [(arrival, qty)]
                else:
                    lo, hi_fraction = params[
                        "split_fraction_range"
                        if behavior == 1
                        else "short_fraction_range"
                    ]
                    first = (
                        max(
                            1,
                            min(
                                qty - 1,
                                int(np.floor(qty * frng.uniform(lo, hi_fraction))),
                            ),
                        )
                        if qty > 1
                        else qty
                    )
                    shipments = [(arrival, first)]
                    if behavior == 1 and qty > first:
                        gap = int(
                            frng.integers(
                                params["split_delay_range"][0],
                                params["split_delay_range"][1] + 1,
                            )
                        )
                        shipments.append((arrival + timedelta(days=gap), qty - first))
                    elif behavior == 2:
                        cancelled = qty - first
                tables["purchase_order_lines"].append(
                    (
                        line_id,
                        po_id,
                        number,
                        int(product_ids[pos]),
                        qty,
                        cancelled,
                        float(cost[pos]),
                    )
                )
                on_order[pos] += qty - cancelled
                for arrival_day, ship_qty in shipments:
                    scheduled[arrival_day].append((line_id, pos, ship_qty))
                line_id += 1
            po_id += 1
        if hi >= 0:
            for key, array in [
                ("opening", opening),
                ("closing", on_hand),
                ("received", received),
                ("sold", sold),
                ("adjusted", adjusted),
                ("latent", latent),
            ]:
                diagnostics[key][hi] = array
            means_history[hi] = means
            tables["daily_sales"].extend(
                (
                    int(store_ids[i]),
                    int(product_ids[i]),
                    day,
                    int(sold[i]),
                    round(float(sold[i] * price[i] * (1 - discount[i])), 2),
                    round(float(sold[i] * cost[i]), 2),
                )
                for i in range(positions)
            )
            tables["inventory_snapshots"].extend(
                (
                    int(store_ids[i]),
                    int(product_ids[i]),
                    day,
                    int(opening[i]),
                    int(on_hand[i]),
                )
                for i in range(positions)
            )
            tables["latent_demand"].extend(
                (int(store_ids[i]), int(product_ids[i]), day, int(latent[i]))
                for i in range(positions)
            )
    storm = (regions == 1) & np.tile([p["storm"] for p in ps], len(stores))
    extra: dict[str, Any] = dict(diagnostics)
    extra["storm_expected_ratio"] = float(
        means_history[-7:, storm].mean() / means_history[-35:-7, storm].mean()
    )
    extra["demo_pl_on_time"] = float(np.mean(demo_received))
    return Dataset(config, seed, tables, extra)
