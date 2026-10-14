"""Stateless inventory counterfactuals using pipeline mathematics, docs/05 §10."""

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta

from stocgain.analytics.distributions import expected_shortage, window_demand
from stocgain.analytics.risk import prepare_pos, score_position
from stocgain.analytics.types import ModelInputs, ModelOutputs, Record

TIERS = ("critical", "high", "moderate", "low")


@dataclass(frozen=True)
class ScenarioParameters:
    """Validated pure model controls; omitted service level uses run config (§10.1)."""

    lead_time_change_days: int = 0
    demand_change_rate: float = 0.0
    service_level: float | None = None
    safety_stock_buffer_rate: float = 0.0
    store_ids: tuple[int, ...] | None = None
    category_ids: tuple[int, ...] | None = None
    supplier_ids: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if (
            type(self.lead_time_change_days) is not int
            or not -7 <= self.lead_time_change_days <= 14
        ):
            raise ValueError("Lead-time change must be an integer from -7 to 14 days")
        for value, low, high in (
            (self.demand_change_rate, -0.5, 1.0),
            (self.safety_stock_buffer_rate, -0.5, 1.0),
            (
                self.service_level if self.service_level is not None else 0.95,
                0.8,
                0.995,
            ),
        ):
            if not math.isfinite(value) or not low <= value <= high:
                raise ValueError("Scenario assumption outside its supported range")


def _summary(
    rows: list[Record],
    recommendations: list[Record],
    positions: list[Record],
    forecasts: dict[tuple[int, int], list[float]],
    inputs: ModelInputs,
) -> Record:
    config = inputs.config
    lookup = {(p["store_id"], p["product_id"]): p for p in positions}
    summary: Record = {
        "positions_in_scope": len(rows),
        "positions_by_tier": {
            tier: sum(r["risk_tier"] == tier for r in rows) for tier in TIERS
        },
        "at_risk_positions": sum(r["risk_tier"] in ("critical", "high") for r in rows),
        "mean_stockout_probability": sum(r["stockout_probability"] for r in rows)
        / len(rows)
        if rows
        else 0.0,
        "expected_shortage_units": sum(r["expected_shortage_units"] for r in rows),
        "revenue_at_risk_usd": sum(r["revenue_at_risk_usd"] for r in rows),
        "margin_at_risk_usd": sum(r["margin_at_risk_usd"] for r in rows),
        "lead_time_demand_units": sum(r["lead_time_demand_mean_units"] for r in rows),
        "safety_stock_units": sum(r["safety_stock_units"] for r in rows),
        "safety_stock_value_usd": sum(
            r["safety_stock_units"]
            * float(lookup[r["store_id"], r["product_id"]]["unit_cost"])
            for r in rows
        ),
        "positions_below_reorder_point": sum(r["below_reorder_point"] for r in rows),
        "recommended_order_units": sum(
            r["recommended_order_units"] or 0 for r in recommendations
        ),
        "recommended_order_value_usd": sum(
            r["recommended_order_cost_usd"] or 0 for r in recommendations
        ),
        "avg_lead_time_days": sum(r["lead_time_mean_days"] for r in rows) / len(rows)
        if rows
        else 0.0,
    }
    summary["annual_carrying_cost_usd"] = (
        summary["safety_stock_value_usd"] * config.carrying_cost_rate_annual
    )
    shortfall = 0.0
    for r in rows:
        p = lookup[r["store_id"], r["product_id"]]
        mean, std = window_demand(
            forecasts[r["store_id"], r["product_id"]],
            r["lead_time_mean_days"] + config.review_period_days,
            r["lead_time_std_days"],
            r["daily_demand_std_units"],
        )
        shortfall += (
            expected_shortage(
                mean, std, r["order_up_to_units"], config.normal_min_mean_units
            )
            * r["lost_sale_rate"]
            * (float(p["unit_price"]) - float(p["unit_cost"]))
            * 365
            / config.review_period_days
        )
    summary["annual_expected_shortfall_margin_usd"] = shortfall
    return summary


def evaluate(
    inputs: ModelInputs,
    baseline: ModelOutputs,
    parameters: ScenarioParameters | None = None,
) -> Record:
    """Re-score in-scope positions and aggregate full-precision tradeoffs (§10).

    Baseline must be full-precision model outputs for these inputs. Storage-rounded
    snapshots can be compared by the caller at their serialization boundary.
    """
    params = parameters or ScenarioParameters()
    alpha = (
        inputs.config.service_level
        if params.service_level is None
        else params.service_level
    )
    positions = [
        p
        for p in inputs.positions
        if all(
            ids is None or p[field] in ids
            for field, ids in (
                ("store_id", params.store_ids),
                ("category_id", params.category_ids),
                ("supplier_id", params.supplier_ids),
            )
        )
    ]
    keys = {(p["store_id"], p["product_id"]) for p in positions}
    forecasts = {(r["store_id"], r["product_id"]): r for r in baseline.forecasts}
    lanes = {(r["supplier_id"], r["store_id"]): r for r in baseline.lanes}
    daily: dict[tuple[int, int], list[float]] = defaultdict(list)
    for r in sorted(baseline.daily, key=lambda r: r["horizon_day"]):
        daily[r["store_id"], r["product_id"]].append(float(r["forecast_units"]))
    pos: dict[tuple[int, int], list[Record]] = defaultdict(list)
    for r in inputs.open_pos:
        pos[r["store_id"], r["product_id"]].append(r)
    promotions: dict[tuple[int, int], list[Record]] = defaultdict(list)
    for promotion in inputs.promotions:
        promotions[promotion["store_id"], promotion["product_id"]].append(promotion)
    base_risks = [r for r in baseline.risks if (r["store_id"], r["product_id"]) in keys]
    base_recommendations = [
        r for r in baseline.recommendations if (r["store_id"], r["product_id"]) in keys
    ]
    scenario_risks = []
    recommendations = []
    scenario_daily = {}
    floored = 0
    insufficient = 0
    for p in positions:
        key = p["store_id"], p["product_id"]
        lane = lanes[p["supplier_id"], p["store_id"]]
        f = forecasts[key]
        shift = params.lead_time_change_days
        scale = 1 + params.demand_change_rate
        if float(lane["mean_lead_time_days"]) + shift < 1:
            floored += 1
        insufficient += f["method"] == "insufficient_data"
        changed_lane = {
            **lane,
            "mean_lead_time_days": max(1.0, float(lane["mean_lead_time_days"]) + shift),
        }
        changed_forecast = {
            **f,
            "base_daily_demand": float(f["base_daily_demand"]) * scale,
            "daily_demand_std": float(f["daily_demand_std"]) * scale,
        }
        changed_daily = [value * scale for value in daily[key]]
        scenario_daily[key] = changed_daily
        orders = prepare_pos(pos[key], inputs.as_of, lane)
        changed_pos = [
            {
                **po,
                "expected_arrival_date": max(
                    inputs.as_of + timedelta(days=1),
                    po["expected_arrival_date"] + timedelta(days=shift),
                ),
            }
            for po in orders
        ]
        changed_position = dict(p)
        changed_position.pop("upcoming_promotion", None)
        future = [
            promotion
            for promotion in promotions[key]
            if inputs.as_of
            < promotion["target_date"]
            <= inputs.as_of
            + timedelta(days=math.ceil(changed_lane["mean_lead_time_days"]))
        ]
        if future:
            changed_position["upcoming_promotion"] = min(
                future, key=lambda promotion: promotion["target_date"]
            )
        r, _, a = score_position(
            changed_position,
            changed_forecast,
            changed_daily,
            changed_lane,
            changed_pos,
            inputs.as_of,
            inputs.config,
            alpha,
            params.safety_stock_buffer_rate,
        )
        scenario_risks.append(r)
        recommendations.append(a)
    base = _summary(base_risks, base_recommendations, positions, daily, inputs)
    scenario = _summary(
        scenario_risks, recommendations, positions, scenario_daily, inputs
    )
    numeric = [k for k in base if k != "positions_by_tier"]
    absolute = {k: scenario[k] - base[k] for k in numeric}
    relative = {
        k: absolute[k] / base[k]
        if base[k] and k != "mean_stockout_probability"
        else None
        for k in numeric
    }
    base_map = {(r["store_id"], r["product_id"]): r for r in base_risks}
    base_orders = {(r["store_id"], r["product_id"]): r for r in base_recommendations}
    order_map = {(r["store_id"], r["product_id"]): r for r in recommendations}
    position_map = {(p["store_id"], p["product_id"]): p for p in positions}
    matrix = [[0] * 4 for _ in TIERS]
    changes = []
    categories: dict[int, Record] = {}
    per_position = []
    for r in scenario_risks:
        key = r["store_id"], r["product_id"]
        b = base_map[key]
        p = position_map[key]
        matrix[TIERS.index(b["risk_tier"])][TIERS.index(r["risk_tier"])] += 1
        per_position.append(
            {"store_id": key[0], "product_id": key[1], "baseline": b, "scenario": r}
        )
        change: Record = {
            k: p[k]
            for k in ("store_id", "product_id", "sku", "product_name", "store_code")
            if k in p
        }
        change.update(
            baseline_tier=b["risk_tier"],
            scenario_tier=r["risk_tier"],
            baseline_stockout_probability=b["stockout_probability"],
            scenario_stockout_probability=r["stockout_probability"],
            baseline_margin_at_risk_usd=b["margin_at_risk_usd"],
            scenario_margin_at_risk_usd=r["margin_at_risk_usd"],
            baseline_recommended_order_units=base_orders[key][
                "recommended_order_units"
            ],
            scenario_recommended_order_units=order_map[key]["recommended_order_units"],
        )
        changes.append(change)
        category = categories.setdefault(
            p["category_id"],
            {
                "category_id": p["category_id"],
                "category_name": p.get("category_name", p["category_code"]),
                "baseline_margin_at_risk_usd": 0.0,
                "scenario_margin_at_risk_usd": 0.0,
                "baseline_at_risk_positions": 0,
                "scenario_at_risk_positions": 0,
            },
        )
        for prefix, row in (("baseline", b), ("scenario", r)):
            category[f"{prefix}_margin_at_risk_usd"] += row["margin_at_risk_usd"]
            category[f"{prefix}_at_risk_positions"] += row["risk_tier"] in (
                "critical",
                "high",
            )
    changes.sort(
        key=lambda r: (
            -(r["scenario_margin_at_risk_usd"] - r["baseline_margin_at_risk_usd"]),
            -(r["scenario_stockout_probability"] - r["baseline_stockout_probability"]),
            r["store_id"],
            r["product_id"],
        )
    )
    warnings = []
    if floored:
        warnings.append(f"Lead time was floored at 1 day for {floored} positions")
    if alpha > 0.99:
        warnings.append(
            "Service levels above 99% require disproportionately more safety stock"
        )
    if insufficient:
        warnings.append(
            f"{insufficient} positions in scope have insufficient demand history"
        )
    return {
        "as_of_date": inputs.as_of,
        "assumptions_applied": {
            "lead_time_change_days": params.lead_time_change_days,
            "demand_change_rate": params.demand_change_rate,
            "service_level": alpha,
            "safety_stock_buffer_rate": params.safety_stock_buffer_rate,
        },
        "positions_in_scope": len(positions),
        "baseline": base,
        "scenario": scenario,
        "delta": {"absolute": absolute, "relative": relative},
        "tier_transitions": {"order": list(TIERS), "matrix": matrix},
        "by_category": list(
            sorted(categories.values(), key=lambda r: r["category_id"])
        ),
        "top_changes": changes[:20],
        "warnings": warnings,
        "position_results": per_position,
    }
