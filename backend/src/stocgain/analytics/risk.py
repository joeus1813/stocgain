"""Pure checkpoint risk, projections and inventory decisions, docs/05 §5–9."""

import math
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any

from stocgain.analytics.config import AnalyticsConfig
from stocgain.analytics.distributions import (
    cumulative_forecast,
    expected_shortage,
    prob_exceeds,
    select_family,
    window_demand,
)
from stocgain.analytics.explanations import build_explanation, detect_drivers
from stocgain.analytics.exposure import compute_exposure
from stocgain.analytics.leadtime import expected_arrival
from stocgain.analytics.policy import compute_policy, order_quantity
from stocgain.analytics.replenishment import recommend


def prepare_pos(
    open_pos: Sequence[Mapping[str, Any]], as_of: date, lane: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Copy open orders with expected dates, preserving scenario overrides (§4.3)."""
    result = []
    for po in open_pos:
        eta = po.get("expected_arrival_date") or expected_arrival(
            as_of, po["promised_delivery_date"], lane
        )
        result.append(
            {
                **po,
                "expected_arrival_date": eta,
                "arrival_std_days": float(
                    po.get("arrival_std_days", lane["std_delay_days"])
                ),
                "window_days": (eta - as_of).days - 1,
                "overdue": po["promised_delivery_date"] <= as_of,
            }
        )
    return sorted(
        result, key=lambda p: (p["expected_arrival_date"], p["purchase_order_id"])
    )


def score_positions(
    daily: Sequence[float],
    daily_std: float,
    on_hand: int,
    lead_mean: float,
    lead_std: float,
    open_pos: Sequence[Mapping[str, Any]],
    config: AnalyticsConfig,
) -> list[dict[str, Any]]:
    """Evaluate receipts before the protection boundary then its end (§5.5)."""
    grouped: dict[date, list[Mapping[str, Any]]] = {}
    for po in open_pos:
        if po["window_days"] < lead_mean:
            grouped.setdefault(po["expected_arrival_date"], []).append(po)
    checkpoints = []
    supply = on_hand
    for eta, group in sorted(grouped.items()):
        first = min(group, key=lambda p: p["purchase_order_id"])
        checkpoints.append(
            {
                "checkpoint_type": "receipt",
                "purchase_order_id": first["purchase_order_id"],
                "arrival_date": eta,
                "window_days": first["window_days"],
                "window_std_days": max(float(p["arrival_std_days"]) for p in group),
                "supply_units": supply,
            }
        )
        supply += sum(int(p["open_quantity_as_of"]) for p in group)
    checkpoints.append(
        {
            "checkpoint_type": "window_end",
            "purchase_order_id": None,
            "arrival_date": None,
            "window_days": lead_mean,
            "window_std_days": lead_std,
            "supply_units": supply,
        }
    )
    for i, c in enumerate(checkpoints, 1):
        mean, std = window_demand(
            daily, float(c["window_days"]), float(c["window_std_days"]), daily_std
        )
        c.update(
            checkpoint_seq=i,
            demand_mean_units=mean,
            demand_std_units=std,
            distribution_family=select_family(mean, std, config.normal_min_mean_units),
            stockout_probability=prob_exceeds(
                mean, std, int(c["supply_units"]), config.normal_min_mean_units
            ),
            expected_shortage_units=expected_shortage(
                mean, std, int(c["supply_units"]), config.normal_min_mean_units
            ),
            is_binding=False,
        )
    binding = max(
        checkpoints,
        key=lambda c: (
            c["stockout_probability"],
            c["expected_shortage_units"],
            -c["checkpoint_seq"],
        ),
    )
    binding["is_binding"] = True
    return checkpoints


def assign_tier(
    probability: float,
    margin: float,
    on_hand: int,
    next_mean: float,
    method: str,
    config: AnalyticsConfig,
) -> str:
    """Apply probability thresholds, financial escalation and data guard (§8.1)."""
    if method == "insufficient_data":
        return "moderate"
    if (
        on_hand == 0 and next_mean >= 1
    ) or probability >= config.tier_critical_probability:
        return "critical"
    if probability >= config.tier_high_probability:
        return "high"
    if probability >= config.tier_moderate_probability:
        return "high" if margin >= config.exposure_escalation_usd else "moderate"
    return "low"


def project_inventory(
    daily: Sequence[float],
    daily_std: float,
    on_hand: int,
    open_pos: Sequence[Mapping[str, Any]],
    as_of: date,
) -> tuple[list[dict[str, Any]], int | None]:
    """Expected on-hand and approximate 80% band with start-day receipts (§5.8)."""
    balance = float(on_hand)
    first = None
    cumulative_receipts = 0
    cumulative_demand = 0.0
    points = []
    receipts: dict[date, int] = {}
    for po in open_pos:
        eta = po["expected_arrival_date"]
        receipts[eta] = receipts.get(eta, 0) + int(po["open_quantity_as_of"])
    for t, forecast in enumerate(daily, 1):
        day = as_of + timedelta(days=t)
        received = receipts.get(day, 0)
        available = balance + received
        if first is None and forecast > 0 and available <= forecast:
            first = t
        balance = max(0.0, available - forecast)
        cumulative_receipts += received
        cumulative_demand += forecast
        spread = 1.2816 * daily_std * math.sqrt(t)
        points.append(
            {
                "date": day,
                "horizon_day": t,
                "forecast_units": forecast,
                "receipt_units": received,
                "projected_on_hand_units": balance,
                "low_units": max(
                    0.0, on_hand + cumulative_receipts - cumulative_demand - spread
                ),
                "high_units": max(
                    0.0, on_hand + cumulative_receipts - cumulative_demand + spread
                ),
            }
        )
    return points, first


def score_position(
    position: Mapping[str, Any],
    forecast: Mapping[str, Any],
    daily: list[float],
    lane: Mapping[str, Any],
    open_pos: Sequence[Mapping[str, Any]],
    as_of: date,
    config: AnalyticsConfig,
    service_level: float | None = None,
    buffer_rate: float = 0.0,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """Produce full-precision snapshot, checkpoints and recommendation rows (§5–9)."""
    pos = prepare_pos(open_pos, as_of, lane)
    oh = int(position["on_hand_units"])
    oo = sum(int(p["open_quantity_as_of"]) for p in pos)
    lead = float(lane["mean_lead_time_days"])
    lead_std = float(lane["std_lead_time_days"])
    std = float(
        forecast.get("daily_demand_std", forecast.get("daily_demand_std_units", 0))
    )
    checkpoints = score_positions(daily, std, oh, lead, lead_std, pos, config)
    binding = next(c for c in checkpoints if c["is_binding"])
    pol = compute_policy(daily, std, lead, lead_std, config, service_level, buffer_rate)
    order = order_quantity(
        oh + oo,
        pol["reorder_point_units"],
        pol["order_up_to_units"],
        int(position["case_pack_qty"]),
        int(position["min_order_qty"]),
        float(position["unit_cost"]),
    )
    avg = cumulative_forecast(daily, 28) / 28
    next_window = float(pos[0]["window_days"]) if pos else lead
    loss = (
        float(position["lost_sale_rate"])
        if "lost_sale_rate" in position
        else config.lost_sale_rates[position["category_code"]]
    )
    exposure = compute_exposure(
        binding["expected_shortage_units"],
        loss,
        float(position["unit_price"]),
        float(position["unit_cost"]),
    )
    _, stockout = project_inventory(daily, std, oh, pos, as_of)
    result: dict[str, Any] = {
        **{k: position[k] for k in ("store_id", "product_id", "supplier_id")},
        "on_hand_units": oh,
        "on_order_units": oo,
        "inventory_position_units": oh + oo,
        "open_po_count": len({p["purchase_order_id"] for p in pos}),
        "next_receipt_date": pos[0]["expected_arrival_date"] if pos else None,
        "next_receipt_units": sum(
            int(p["open_quantity_as_of"])
            for p in pos
            if p["expected_arrival_date"] == pos[0]["expected_arrival_date"]
        )
        if pos
        else None,
        "next_receipt_po_id": pos[0]["purchase_order_id"] if pos else None,
        "next_receipt_overdue": bool(pos and pos[0]["overdue"]),
        "avg_daily_demand_units": avg,
        "daily_demand_std_units": std,
        "days_of_cover": round(min(365.0, oh / avg), 1) if avg > 0 else None,
        "lead_time_mean_days": lead,
        "lead_time_std_days": lead_std,
        "protection_window_days": lead,
        **pol,
        "below_reorder_point": order["below_reorder_point"],
        "distribution_family": binding["distribution_family"],
        "binding_checkpoint_type": binding["checkpoint_type"],
        "binding_window_days": binding["window_days"],
        "binding_supply_units": binding["supply_units"],
        "binding_demand_mean_units": binding["demand_mean_units"],
        "binding_demand_std_units": binding["demand_std_units"],
        "stockout_probability": binding["stockout_probability"],
        "expected_shortage_units": binding["expected_shortage_units"],
        **exposure,
        "projected_stockout_date": as_of + timedelta(days=stockout)
        if stockout
        else None,
        "days_until_projected_stockout": stockout,
        "currently_out_of_stock": oh == 0 and avg > 0,
        "recent_censored_days": int(
            forecast.get(
                "recent_censored_days", position.get("recent_censored_days", 0)
            )
        ),
    }
    result["risk_tier"] = assign_tier(
        result["stockout_probability"],
        result["margin_at_risk_usd"],
        oh,
        cumulative_forecast(daily, next_window),
        forecast["method"],
        config,
    )
    promotion = position.get("upcoming_promotion")
    result["risk_drivers"] = detect_drivers(
        result, forecast, lane, pos, next_window, bool(promotion)
    )
    result["explanation"] = build_explanation(
        result,
        forecast,
        lane,
        pos,
        position.get("supplier_name", f"supplier {position['supplier_id']}"),
        promotion,
    )
    for c in checkpoints:
        c.update(store_id=position["store_id"], product_id=position["product_id"])
    return (
        result,
        checkpoints,
        recommend(result, forecast, pos, binding, order, position, config),
    )


def sensitivity(
    position: Mapping[str, Any],
    forecast: Mapping[str, Any],
    daily: list[float],
    lane: Mapping[str, Any],
    open_pos: Sequence[Mapping[str, Any]],
    as_of: date,
    config: AnalyticsConfig,
    promo_multipliers: Sequence[float],
) -> dict[str, float]:
    """Four one-at-a-time probability counterfactuals, not additive (§8.4)."""
    if len(promo_multipliers) != len(daily) or any(m <= 0 for m in promo_multipliers):
        raise ValueError("A positive promotion multiplier is required for each day")
    prepared = prepare_pos(open_pos, as_of, lane)

    def probability(
        f: Mapping[str, Any],
        days: list[float],
        estimates: Mapping[str, Any],
        orders: Sequence[Mapping[str, Any]],
    ) -> float:
        result, _, _ = score_position(
            position, f, days, estimates, orders, as_of, config
        )
        return float(result["stockout_probability"])

    reliable_lane = {**lane, "std_lead_time_days": 0.0, "std_delay_days": 0.0}
    reliable_orders: Sequence[Mapping[str, Any]] = [
        {**p, "arrival_std_days": 0.0} for p in prepared
    ]
    promised_orders: Sequence[Mapping[str, Any]] = [
        {
            **p,
            "expected_arrival_date": max(
                as_of + timedelta(days=1), p["promised_delivery_date"]
            ),
        }
        for p in prepared
    ]
    level = float(
        forecast.get("base_daily_demand", forecast.get("deseasonalized_level_units", 0))
    )
    floor_forecast = {**forecast, "daily_demand_std": math.sqrt(level)}
    no_promo = [d / m for d, m in zip(daily, promo_multipliers, strict=True)]
    return {
        "baseline": probability(forecast, daily, lane, open_pos),
        "reliable_lead_times": probability(
            forecast, daily, reliable_lane, reliable_orders
        ),
        "promised_arrival": probability(forecast, daily, lane, promised_orders),
        "poisson_variability": probability(floor_forecast, daily, lane, open_pos),
        "no_promotion": probability(forecast, no_promo, lane, open_pos),
    }
