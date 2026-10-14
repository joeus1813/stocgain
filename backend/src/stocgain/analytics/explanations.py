"""Deterministic descriptive drivers and prose, docs/05 §8."""

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any


def date_label(value: date) -> str:
    """Month/day display used in model explanations."""
    return f"{value:%b} {value.day}"


def detect_drivers(
    risk: Mapping[str, Any],
    forecast: Mapping[str, Any],
    lane: Mapping[str, Any],
    open_pos: Sequence[Mapping[str, Any]],
    next_window: float,
    upcoming_promotion: bool = False,
) -> list[str]:
    """Evaluate every descriptive rule in canonical order; docs/05 §8.2."""
    doc = risk["days_of_cover"]
    level = float(
        forecast.get("base_daily_demand", forecast.get("deseasonalized_level_units", 0))
    )
    checks = [
        ("currently_out_of_stock", risk["currently_out_of_stock"]),
        ("coverage_gap", doc is not None and doc < next_window),
        ("no_inbound_supply", not open_pos and risk["below_reorder_point"]),
        ("overdue_po", any(p["overdue"] for p in open_pos)),
        (
            "supplier_unreliable",
            lane.get("on_time_rate") is not None and lane["on_time_rate"] < 0.8,
        ),
        (
            "lead_time_variability",
            risk["lead_time_std_days"] / risk["lead_time_mean_days"] >= 0.3,
        ),
        (
            "demand_acceleration",
            forecast.get("demand_trend_ratio") is not None
            and forecast["demand_trend_ratio"] >= 1.25,
        ),
        (
            "high_demand_variability",
            forecast.get("observed_demand_cv") is not None
            and forecast["observed_demand_cv"] >= 0.75
            and level >= 1,
        ),
        ("recent_stockouts", risk["recent_censored_days"] >= 3),
        ("upcoming_promotion", upcoming_promotion),
        ("limited_history", forecast["method"] != "store_sku"),
    ]
    return [name for name, present in checks if present]


def build_explanation(
    risk: Mapping[str, Any],
    forecast: Mapping[str, Any],
    lane: Mapping[str, Any],
    open_pos: Sequence[Mapping[str, Any]],
    supplier_name: str,
    promotion: Mapping[str, Any] | None = None,
) -> str:
    """Assemble coverage, delivery, at most two drivers and risk text (§8.3)."""
    oh = risk["on_hand_units"]
    avg = risk["avg_daily_demand_units"]
    if oh == 0 and avg > 0:
        s1 = f"This item is out of stock now while forecast demand is {avg:.1f} units/day."
    elif avg == 0:
        s1 = f"On-hand inventory is {oh:,} units and there has been no recent in-stock demand."
    else:
        s1 = f"On-hand inventory of {oh:,} units covers about {float(risk['days_of_cover'] or 0):.1f} days of forecast demand ({avg:.1f} units/day)."
    if open_pos:
        po = open_pos[0]
        name = po.get("po_number", f"PO-{po['purchase_order_id']}")
        if po["overdue"]:
            s2 = f"{name} ({po['open_quantity_as_of']:,} units) was due on {date_label(po['promised_delivery_date'])} and has not arrived; based on this supplier's history it is now expected on {date_label(po['expected_arrival_date'])}."
        else:
            s2 = f"The next delivery ({po['open_quantity_as_of']:,} units on {name}) is expected on {date_label(po['expected_arrival_date'])}, after {po['window_days']:.1f} days of selling."
    else:
        s2 = f"No replenishment is on order; a new order from {supplier_name} typically arrives in {risk['lead_time_mean_days']:.1f} days (±{risk['lead_time_std_days']:.1f})."
    phrases: dict[str, str] = {
        "recent_stockouts": f"It was out of stock on {risk['recent_censored_days']} of the last 28 days; those days were excluded from the demand estimate.",
        "lead_time_variability": f"Lead times on this lane vary by about ±{risk['lead_time_std_days']:.1f} days.",
        "limited_history": f"There are only {forecast.get('clean_days', 0)} clean in-stock days of history, so the estimate leans on chain-wide demand for this item.",
    }
    if forecast.get("demand_trend_ratio") is not None:
        phrases["demand_acceleration"] = (
            f"Recent demand is running {round((forecast['demand_trend_ratio'] - 1) * 100)}% above its prior six-week rate."
        )
    if lane.get("on_time_rate") is not None:
        phrases["supplier_unreliable"] = (
            f"This supplier delivered {round(lane['on_time_rate'] * 100)}% of orders to this store on time over the last 90 days."
        )
    if forecast.get("observed_demand_cv") is not None:
        phrases["high_demand_variability"] = (
            f"Daily demand is highly variable (coefficient of variation {forecast['observed_demand_cv']:.2f})."
        )
    if promotion:
        phrases["upcoming_promotion"] = (
            f"A planned promotion ({promotion['promotion_name']}) starting {date_label(promotion['start_date'])} is expected to lift demand by {round((float(promotion['planned_lift']) - 1) * 100)}%."
        )
    order = (
        "recent_stockouts",
        "demand_acceleration",
        "supplier_unreliable",
        "lead_time_variability",
        "high_demand_variability",
        "upcoming_promotion",
        "limited_history",
    )
    drivers = (
        []
        if risk["risk_tier"] == "low"
        else [phrases[d] for d in order if d in risk["risk_drivers"] and d in phrases][
            :2
        ]
    )
    s4 = f"Estimated stockout probability before replenishment: {risk['stockout_probability'] * 100:.1f}% ({risk['risk_tier'].title()})."
    if risk["margin_at_risk_usd"] >= 1:
        s4 += f" Estimated gross margin at risk: ${risk['margin_at_risk_usd']:,.0f} (model estimate)."
    return " ".join([s1, s2, *drivers, s4])


def describe_driver(
    code: str,
    risk: Mapping[str, Any],
    forecast: Mapping[str, Any],
    lane: Mapping[str, Any],
    as_of: date | None = None,
) -> dict[str, str]:
    """Describe one stored driver without causal claims; docs/08 §3.13."""
    labels = {
        "currently_out_of_stock": "Currently out of stock",
        "coverage_gap": "Coverage gap",
        "no_inbound_supply": "No inbound supply",
        "overdue_po": "Overdue purchase order",
        "supplier_unreliable": "Supplier on-time below 80%",
        "lead_time_variability": "Lead-time variability",
        "demand_acceleration": "Demand acceleration",
        "high_demand_variability": "High demand variability",
        "recent_stockouts": "Recent stockouts",
        "upcoming_promotion": "Upcoming promotion",
        "limited_history": "Limited history",
    }
    next_window = float(risk["lead_time_mean_days"])
    if risk.get("next_receipt_date") is not None and as_of is not None:
        arrival = risk["next_receipt_date"]
        if isinstance(arrival, str):
            arrival = date.fromisoformat(arrival)
        next_window = float((arrival - as_of).days - 1)
    descriptions = {
        "currently_out_of_stock": f"No units are on hand while forecast demand averages {risk['avg_daily_demand_units']:.1f} units/day.",
        "coverage_gap": f"Days of cover ({float(risk['days_of_cover'] or 0):.1f}) are shorter than the time until replenishment ({next_window:.1f} days).",
        "no_inbound_supply": "Nothing is on order and inventory position is at or below the reorder point.",
        "overdue_po": "At least one open purchase order is past its promised delivery date.",
        "lead_time_variability": f"Lead-time standard deviation is {risk['lead_time_std_days']:.1f} days relative to a mean of {risk['lead_time_mean_days']:.1f} days.",
        "recent_stockouts": f"Stockouts censored demand on {risk['recent_censored_days']} of the last 28 days.",
        "upcoming_promotion": "A planned promotion falls within the replenishment protection window.",
        "limited_history": f"The forecast uses {forecast['method']} with {forecast['clean_days']} clean in-stock days.",
    }
    if lane.get("on_time_rate") is not None:
        descriptions["supplier_unreliable"] = (
            f"This lane's 90-day on-time rate is {float(lane['on_time_rate']) * 100:.1f}%."
        )
    if forecast.get("demand_trend_ratio") is not None:
        descriptions["demand_acceleration"] = (
            f"Recent clean demand is {float(forecast['demand_trend_ratio']):.2f} times its preceding six-week rate."
        )
    if forecast.get("observed_demand_cv") is not None:
        descriptions["high_demand_variability"] = (
            f"Observed daily demand has a coefficient of variation of {float(forecast['observed_demand_cv']):.2f}."
        )
    return {"code": code, "label": labels[code], "description": descriptions[code]}
