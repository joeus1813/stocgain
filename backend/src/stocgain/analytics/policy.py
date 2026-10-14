"""Periodic-review replenishment policy, docs/05 §6."""

import math
from collections.abc import Sequence
from typing import Any

from stocgain.analytics.config import AnalyticsConfig
from stocgain.analytics.distributions import quantile, window_demand


def compute_policy(
    daily: Sequence[float],
    daily_std: float,
    lead_mean: float,
    lead_std: float,
    config: AnalyticsConfig,
    service_level: float | None = None,
    buffer_rate: float = 0.0,
) -> dict[str, Any]:
    """Compute full-precision safety stock and integer target levels (§6.1–6.2)."""
    alpha = config.service_level if service_level is None else service_level
    mean, std = window_demand(daily, lead_mean, lead_std, daily_std)
    ss = max(0.0, quantile(mean, std, alpha, config.normal_min_mean_units) - mean) * (
        1 + buffer_rate
    )
    rop = math.ceil(mean + ss - 1e-9)
    review_mean, review_std = window_demand(
        daily, lead_mean + config.review_period_days, lead_std, daily_std
    )
    target = max(
        rop,
        math.ceil(
            review_mean
            + max(
                0.0,
                quantile(review_mean, review_std, alpha, config.normal_min_mean_units)
                - review_mean,
            )
            * (1 + buffer_rate)
            - 1e-9
        ),
    )
    return {
        "lead_time_demand_mean_units": mean,
        "lead_time_demand_std_units": std,
        "safety_stock_units": ss,
        "reorder_point_units": rop,
        "order_up_to_units": target,
        "service_level": alpha,
    }


def order_quantity(
    inventory_position: int,
    reorder_point: int,
    order_up_to: int,
    case_pack: int,
    minimum: int,
    unit_cost: float,
) -> dict[str, Any]:
    """Round reorder units to cases and MOQ only when triggered; docs/05 §6.3."""
    below = inventory_position <= reorder_point and order_up_to > inventory_position
    qty = (
        max(
            minimum,
            math.ceil((order_up_to - inventory_position) / case_pack - 1e-9)
            * case_pack,
        )
        if below
        else None
    )
    return {
        "below_reorder_point": below,
        "recommended_order_units": qty,
        "recommended_order_cost_usd": qty * unit_cost if qty is not None else None,
    }
