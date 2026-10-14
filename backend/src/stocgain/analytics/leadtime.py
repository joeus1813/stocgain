"""Pure lane estimates and inbound timing; docs/05 §4."""

from collections.abc import Mapping
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from stocgain.analytics.config import AnalyticsConfig


def select_lane_estimate(
    lane: Mapping[str, Any], supplier: Mapping[str, Any], config: AnalyticsConfig
) -> dict[str, Any]:
    """Choose lane, pooled supplier, then contractual lead time in days (§4.2)."""
    contract = float(lane["contract_lead_time_days"])
    n = int(lane["n_received"])
    if n >= config.lane_min_observations:
        source = "lane"
        base = lane
        mean = float(lane["mean_lead_time_days"])
        std = max(0.5, float(lane["std_lead_time_days"] or 0))
    elif int(supplier.get("n_received", 0)) >= config.lane_min_observations:
        source = "supplier"
        base = supplier
        mean = contract + float(supplier["mean_delay_days"])
        std = max(0.5, float(supplier["std_delay_days"] or 0))
    else:
        source = "contract"
        base = {}
        mean = contract
        std = contract * config.contract_lead_time_cv
    result: dict[str, Any] = {
        "lead_time_source": source,
        "n_received_pos": n,
        "mean_lead_time_days": mean,
        "std_lead_time_days": std,
        "mean_delay_days": float(base.get("mean_delay_days") or 0),
        "std_delay_days": max(0.5, float(base.get("std_delay_days") or 0))
        if base
        else std,
        "mean_delay_when_late_days": float(
            base.get("mean_delay_when_late_days") or config.default_delay_when_late_days
        ),
        "on_time_rate": float(lane["on_time_rate_90d"])
        if lane.get("on_time_rate_90d") is not None
        else None,
    }
    result.update(
        {key: lane[key] for key in ("supplier_id", "store_id") if key in lane}
    )
    return result


def round_half_up(value: float) -> int:
    """Round a number of days with decimal half-up ties, docs/05 §4.3."""
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def expected_arrival(as_of: date, promised: date, estimate: Mapping[str, Any]) -> date:
    """Expected start-of-day receipt date using only the as-of estimate (§4.3)."""
    if promised > as_of:
        return promised + timedelta(
            days=max(0, round_half_up(float(estimate["mean_delay_days"])))
        )
    remaining = max(
        1,
        round_half_up(
            float(estimate["mean_delay_when_late_days"]) - (as_of - promised).days
        ),
    )
    return as_of + timedelta(days=remaining)
