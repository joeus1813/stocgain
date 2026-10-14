"""Position endpoint assembly from persisted model evidence, docs/08 §3.13–16."""

import re
from datetime import timedelta
from typing import Any

from stocgain.analytics.explanations import describe_driver
from stocgain.analytics.formatting import format_number
from stocgain.analytics.leadtime import expected_arrival
from stocgain.analytics.risk import prepare_pos, project_inventory
from stocgain.api.dependencies import Context
from stocgain.api.errors import ApiError
from stocgain.api.schemas import positions as schema
from stocgain.api.schemas.common import StrictModel
from stocgain.services.model_cache import get_baseline


def require_position(ctx: Context, store_id: int, product_id: int) -> dict[str, Any]:
    """Validate identities in store/product/position order and return SQL parameters."""
    params = {"store_id": store_id, "product_id": product_id}
    exists = ctx.rows("position_identity", params)[0]
    for key, code, message in [
        ("store_exists", "STORE_NOT_FOUND", "Store not found."),
        ("product_exists", "PRODUCT_NOT_FOUND", "Product not found."),
        (
            "position_exists",
            "POSITION_NOT_FOUND",
            "Position not found in this analytics run.",
        ),
    ]:
        if not exists[key]:
            raise ApiError(404, code, message)
    return params


def _fields(model: type[StrictModel], values: dict[str, Any]) -> dict[str, Any]:
    return {key: values[key] for key in model.model_fields}


def detail(ctx: Context, store_id: int, product_id: int) -> dict[str, Any]:
    """Return stored calculations and display descriptions without recomputation."""
    params = require_position(ctx, store_id, product_id)
    row = ctx.rows("position_detail", params)[0]
    risk = row["risk"]
    demand = row["demand"]
    supply = row["supply"]
    action = row["recommendation"]
    row.update(
        store_id=store_id, product_id=product_id, supplier_id=risk["supplier_id"]
    )
    risk_info = {
        **risk,
        "drivers": [
            describe_driver(code, risk, demand, supply, ctx.run["as_of_date"])
            for code in risk["risk_drivers"]
        ],
    }
    # Older persisted explanations predate the shared UI formatting boundary.
    # Normalize only this display token; preserve stored prose and all model values.
    risk_info["explanation"] = re.sub(
        r"(Estimated stockout probability before replenishment: )[^ ]+",
        lambda match: (
            match[1]
            + format_number(
                "probability", round(float(risk["stockout_probability"]), 4)
            )
        ),
        str(risk["explanation"]),
    )
    receipt = None
    if risk["next_receipt_date"] is not None:
        receipt = {
            "date": risk["next_receipt_date"],
            "units": risk["next_receipt_units"],
            "purchase_order_id": risk["next_receipt_po_id"],
            "po_number": row["next_po_number"],
            "overdue": risk["next_receipt_overdue"],
        }
    inventory = {**risk, "next_receipt": receipt}
    demand_info = {
        **demand,
        "forecast_method": demand["method"],
        "base_daily_demand_units": demand["base_daily_demand"],
        "avg_daily_demand_units": risk["avg_daily_demand_units"],
        "daily_demand_std_units": demand["daily_demand_std"],
        "recent_censored_days": risk["recent_censored_days"],
    }
    supply_info = {**supply, **risk}
    policy = {**risk, "review_period_days": ctx.run["config"]["review_period_days"]}
    related = (
        {
            "purchase_order_id": action["related_purchase_order_id"],
            "po_number": row["related_po_number"],
        }
        if action["related_purchase_order_id"]
        else None
    )
    recommendation = {
        **action,
        "recommended_order_cases": action["recommended_order_units"]
        // row["case_pack_qty"]
        if action["recommended_order_units"] is not None
        else None,
        "related_purchase_order": related,
    }
    return {
        "run": _fields(schema.RunInfo, ctx.run),
        "store": _fields(schema.StoreInfo, row),
        "product": _fields(schema.ProductInfo, row),
        "supplier": _fields(schema.SupplierInfo, row),
        "risk": _fields(schema.RiskInfo, risk_info),
        "inventory": _fields(schema.InventoryInfo, inventory),
        "demand": _fields(schema.DemandInfo, demand_info),
        "supply": _fields(schema.SupplyInfo, supply_info),
        "policy": _fields(schema.PolicyInfo, policy),
        "exposure": _fields(schema.ExposureInfo, risk),
        "checkpoints": ctx.rows("position_checkpoints", params),
        "recommendation": _fields(schema.RecommendationInfo, recommendation),
    }


def history(ctx: Context, store_id: int, product_id: int, days: int) -> dict[str, Any]:
    """Return cutoff-bounded observed history and current-run daily forecasts."""
    params = require_position(ctx, store_id, product_id)
    return {
        "days": ctx.rows("position_history", {**params, "days": days}),
        "forecast": ctx.rows("position_forecast", params),
    }


def projection(
    ctx: Context, store_id: int, product_id: int, history_days: int, horizon_days: int
) -> dict[str, Any]:
    """Replay the full-precision model inputs so stockout dates match the pipeline."""
    params = require_position(ctx, store_id, product_id)
    inputs, outputs = get_baseline(ctx)
    risk = next(
        r
        for r in outputs.risks
        if (r["store_id"], r["product_id"]) == (store_id, product_id)
    )
    stored = ctx.rows("position_detail", params)[0]["risk"]
    forecast = next(
        r
        for r in outputs.forecasts
        if (r["store_id"], r["product_id"]) == (store_id, product_id)
    )
    lane = next(
        r
        for r in outputs.lanes
        if (r["supplier_id"], r["store_id"]) == (risk["supplier_id"], store_id)
    )
    daily = [
        float(r["forecast_units"])
        for r in sorted(outputs.daily, key=lambda r: r["horizon_day"])
        if (r["store_id"], r["product_id"]) == (store_id, product_id)
    ]
    orders = prepare_pos(
        [
            p
            for p in inputs.open_pos
            if (p["store_id"], p["product_id"]) == (store_id, product_id)
        ],
        inputs.as_of,
        lane,
    )
    values, first = project_inventory(
        daily,
        float(forecast["daily_demand_std"]),
        risk["on_hand_units"],
        orders,
        inputs.as_of,
    )
    stockout = inputs.as_of + timedelta(days=first) if first is not None else None
    stored_date = (
        str(stored["projected_stockout_date"])
        if stored["projected_stockout_date"]
        else None
    )
    if (str(stockout) if stockout else None) != stored_date:
        raise ApiError(
            500,
            "MODEL_INCONSISTENCY",
            "Projection differs from the selected analytics run.",
        )
    actual = ctx.rows("position_history", {**params, "days": history_days})
    points = [
        {
            "date": r["date"],
            "kind": "actual",
            "on_hand_units": r["closing_on_hand_units"],
        }
        for r in actual
    ]
    points.extend(
        {
            "date": r["date"],
            "kind": "projected",
            "expected_on_hand_units": r["projected_on_hand_units"],
            "band_low_units": r["low_units"],
            "band_high_units": r["high_units"],
            "forecast_units": r["forecast_units"],
            "receipts_units": r["receipt_units"],
        }
        for r in values[:horizon_days]
    )
    receipts = [
        {
            "date": p["expected_arrival_date"],
            "purchase_order_id": p["purchase_order_id"],
            "po_number": p["po_number"],
            "units": p["open_quantity_as_of"],
            "overdue": p["overdue"],
        }
        for p in orders
        if p["expected_arrival_date"] <= inputs.as_of + timedelta(days=horizon_days)
    ]
    return {
        "as_of_date": inputs.as_of,
        "reorder_point_units": stored["reorder_point_units"],
        "safety_stock_units": stored["safety_stock_units"],
        "projected_stockout_date": stockout,
        "points": points,
        "receipts": receipts,
        "notes": "Expected inventory assumes forecast demand and expected PO arrival dates; the band is an approximate 80% range from demand uncertainty only.",
    }


def purchase_orders(
    ctx: Context, store_id: int, product_id: int, recent_received_limit: int
) -> dict[str, Any]:
    """Derive line status and expected dates using only facts known by cutoff."""
    params = require_position(ctx, store_id, product_id)
    lane = ctx.rows("position_detail", params)[0]["supply"]
    rows = ctx.rows("position_purchase_orders", params)
    opened = []
    received = []
    for row in rows:
        if row["open_quantity"] > 0:
            row.update(
                expected_arrival_date=expected_arrival(
                    ctx.run["as_of_date"], row["promised_delivery_date"], lane
                ),
                overdue=row["promised_delivery_date"] <= ctx.run["as_of_date"],
            )
            opened.append(_fields(schema.OpenOrder, row))
        elif row["first_receipt_date"] is not None:
            received.append(_fields(schema.ReceivedOrder, row))
    opened.sort(key=lambda r: (r["expected_arrival_date"], r["purchase_order_id"]))
    return {"open": opened, "recent_received": received[:recent_received_limit]}


def sensitivity_detail(ctx: Context, store_id: int, product_id: int) -> dict[str, Any]:
    """Replay the existing pure sensitivity function without changing model assumptions."""
    from stocgain.analytics.risk import sensitivity

    require_position(ctx, store_id, product_id)
    inputs, outputs = get_baseline(ctx)

    def matches(record: dict[str, Any]) -> bool:
        return (record["store_id"], record["product_id"]) == (store_id, product_id)

    position = next(p for p in inputs.positions if matches(p))
    forecast = next(p for p in outputs.forecasts if matches(p))
    lane = next(
        p
        for p in outputs.lanes
        if p["store_id"] == store_id and p["supplier_id"] == position["supplier_id"]
    )
    daily = sorted(
        (p for p in outputs.daily if matches(p)), key=lambda p: p["horizon_day"]
    )
    probabilities = sensitivity(
        position,
        forecast,
        [float(p["forecast_units"]) for p in daily],
        lane,
        [p for p in inputs.open_pos if matches(p)],
        inputs.as_of,
        inputs.config,
        [float(p["promo_multiplier"]) for p in daily],
    )
    labels = [
        ("reliable_lead_times", "reliable_lead_times", "Perfectly reliable lead times"),
        (
            "pos_on_promised_date",
            "promised_arrival",
            "Open POs arrive on promised date",
        ),
        (
            "poisson_variability",
            "poisson_variability",
            "Demand variability at Poisson floor",
        ),
        ("no_promotion", "no_promotion", "No planned promotion"),
    ]
    return dict(
        baseline_probability=probabilities["baseline"],
        scenarios=[
            dict(key=key, label=label, stockout_probability=probabilities[source])
            for key, source, label in labels
        ],
        note="One-at-a-time sensitivities; effects are not additive. Lower uncertainty can increase probability when expected demand exceeds supply.",
    )
