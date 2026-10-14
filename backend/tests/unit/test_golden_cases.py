"""Published illustrative outputs are independent numerical acceptance fixtures."""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from stocgain.analytics.config import AnalyticsConfig
from stocgain.analytics.leadtime import expected_arrival
from stocgain.analytics.risk import score_position

CASES = json.loads(
    (Path(__file__).parents[1] / "fixtures/golden_cases.json").read_text()
)
T = date(2026, 9, 30)


@pytest.mark.parametrize("case_id", ["G1", "G2", "G3", "G5", "G6", "G7", "G8", "G9"])
def test_golden_inventory(case_id):
    case = CASES[case_id]
    position = {
        "store_id": 1,
        "product_id": 1,
        "supplier_id": 1,
        "on_hand_units": case["on_hand"],
        "unit_price": case["price"],
        "unit_cost": case["cost"],
        "lost_sale_rate": case["loss"],
        "case_pack_qty": case["pack"],
        "min_order_qty": case["moq"],
    }
    forecast = {
        "method": "store_sku",
        "base_daily_demand": case["demand"],
        "daily_demand_std": case["std"],
    }
    lane = {
        "mean_lead_time_days": case["lead"],
        "std_lead_time_days": case["lead_std"],
        "mean_delay_days": case.get("delay", 0),
        "std_delay_days": case.get("delay_std", 1),
        "mean_delay_when_late_days": 3,
    }
    pos = []
    if "po" in case:
        pos = [
            {
                **case["po"],
                "promised_delivery_date": date.fromisoformat(
                    case["po"]["promised_delivery_date"]
                ),
            }
        ]
    result, checkpoints, recommendation = score_position(
        position,
        forecast,
        [case["demand"]] * 42,
        lane,
        pos,
        T,
        AnalyticsConfig(),
        case.get("service_level"),
    )
    expected = case["expected"]
    mapping = {
        "probability": "stockout_probability",
        "shortage": "expected_shortage_units",
        "margin": "margin_at_risk_usd",
        "rop": "reorder_point_units",
        "target": "order_up_to_units",
        "tier": "risk_tier",
        "family": "distribution_family",
        "doc": "days_of_cover",
    }
    for short, long in mapping.items():
        if short in expected:
            if short in ("probability", "shortage", "margin"):
                assert result[long] == pytest.approx(
                    expected[short], abs=0.002 if short == "probability" else 0.05
                )
            else:
                assert result[long] == expected[short]
    for short, long in {
        "qty": "recommended_order_units",
        "action": "action_type",
    }.items():
        if short in expected:
            assert recommendation[long] == expected[short]
    if "driver" in expected:
        assert expected["driver"] in result["risk_drivers"]
    if "second_probability" in expected:
        assert checkpoints[1]["stockout_probability"] == pytest.approx(
            expected["second_probability"], abs=0.002
        )
    if "receipt_probability" in expected:
        assert checkpoints[0]["stockout_probability"] == expected["receipt_probability"]


@pytest.mark.parametrize("case_id", ["G10", "G11"])
def test_overdue_golden(case_id):
    case = CASES[case_id]
    assert expected_arrival(
        T,
        T + timedelta(days=case["promised_offset"]),
        {"mean_delay_when_late_days": case["mean_delay_when_late"]},
    ) == T + timedelta(days=case["expected"]["eta_offset"])
