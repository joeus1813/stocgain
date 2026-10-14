"""Decision-support actions and deterministic priority; docs/05 §9."""

from collections.abc import Mapping, Sequence
from typing import Any

from stocgain.analytics.config import AnalyticsConfig
from stocgain.analytics.explanations import date_label


def recommend(
    risk: Mapping[str, Any],
    forecast: Mapping[str, Any],
    open_pos: Sequence[Mapping[str, Any]],
    binding: Mapping[str, Any],
    order: Mapping[str, Any],
    position: Mapping[str, Any],
    config: AnalyticsConfig,
) -> dict[str, Any]:
    """Select first matching primary action and retain secondary order (§9.1)."""
    elevated = risk["risk_tier"] != "low"
    receipt = (
        binding["checkpoint_type"] == "receipt"
        and risk["stockout_probability"] >= config.expedite_probability
    )
    late = (
        bool(open_pos)
        and open_pos[0]["window_days"] >= risk["protection_window_days"]
        and risk["stockout_probability"] >= config.expedite_probability
    )
    overdue = risk["next_receipt_overdue"] and elevated
    related = None
    supplier = position.get("supplier_name", f"supplier {position['supplier_id']}")
    if forecast["method"] == "insufficient_data":
        action = "monitor"
        rationale = "The demand estimate relies on chain-wide data; verify shelf availability and on-hand accuracy."
    elif open_pos and (receipt or late or overdue):
        action = "expedite_po"
        selected = (
            next(
                (
                    p
                    for p in open_pos
                    if p["purchase_order_id"] == binding["purchase_order_id"]
                ),
                None,
            )
            if receipt
            else None
        )
        selected = selected or next((p for p in open_pos if p["overdue"]), open_pos[0])
        related = selected["purchase_order_id"]
        name = selected.get("po_number", f"PO-{related}")
        if receipt:
            rationale = f"Shortage is likely before {name} arrives on {date_label(selected['expected_arrival_date'])}; request an expedite or a partial early shipment from {supplier}."
        elif late:
            rationale = f"Open order {name} is not expected until {date_label(selected['expected_arrival_date'])}, later than a new order would typically arrive; request an expedite."
        else:
            rationale = f"{name} is past its promised date ({date_label(selected['promised_delivery_date'])}); confirm the delivery date with {supplier} or request an expedite."
    elif order["below_reorder_point"]:
        action = "reorder"
        qty = order["recommended_order_units"]
        pack = position["case_pack_qty"]
        rationale = f"Inventory position ({risk['inventory_position_units']:,}) is at or below the reorder point ({risk['reorder_point_units']:,}). Order {qty:,} units ({qty // pack:,} cases of {pack}) to reach the target stock position of {risk['order_up_to_units']:,}."
    elif (
        elevated
        or (
            forecast["method"] != "store_sku"
            and float(
                forecast.get(
                    "base_daily_demand", forecast.get("deseasonalized_level_units", 0)
                )
            )
            > 0
        )
        or forecast["method"] == "insufficient_data"
    ):
        action = "monitor"
        rationale = (
            f"Risk is elevated ({risk['stockout_probability'] * 100:.1f}%) but inventory position is above the reorder point; review again at the next weekly cycle."
            if elevated and forecast["method"] == "store_sku"
            else "The demand estimate relies on chain-wide data; verify shelf availability and on-hand accuracy."
        )
    else:
        action = "no_action"
        rationale = (
            "Inventory and inbound supply cover expected demand with acceptable risk."
        )
    return {
        **{k: risk[k] for k in ("store_id", "product_id", "supplier_id")},
        "action_type": action,
        "urgency": None
        if action == "no_action"
        else ("urgent" if risk["risk_tier"] in ("critical", "high") else "standard"),
        "priority_rank": None,
        "recommended_order_units": order["recommended_order_units"],
        "recommended_order_cost_usd": order["recommended_order_cost_usd"],
        "related_purchase_order_id": related,
        "rationale": rationale,
    }


def rank(
    recommendations: Sequence[Mapping[str, Any]], risks: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Rank actionable positions lexicographically without weighted scores (§9.3)."""
    lookup = {(r["store_id"], r["product_id"]): r for r in risks}
    tiers = {"critical": 0, "high": 1, "moderate": 2, "low": 3}
    severity = {"expedite_po": 0, "reorder": 1, "monitor": 2, "no_action": 3}

    def key(a: Mapping[str, Any]) -> tuple[int, float, int, int, int, int]:
        r = lookup[(a["store_id"], a["product_id"])]
        return (
            tiers[r["risk_tier"]],
            -float(r["margin_at_risk_usd"]),
            r["days_until_projected_stockout"]
            if r["days_until_projected_stockout"] is not None
            else 10**9,
            severity[a["action_type"]],
            int(a["store_id"]),
            int(a["product_id"]),
        )

    ranked = {
        (a["store_id"], a["product_id"]): i
        for i, a in enumerate(
            sorted(
                (a for a in recommendations if a["action_type"] != "no_action"), key=key
            ),
            1,
        )
    }
    return [
        {**a, "priority_rank": ranked.get((a["store_id"], a["product_id"]))}
        for a in recommendations
    ]
