"""Scenario neutrality, documented tradeoffs and scope acceptance."""

from datetime import date

import pytest

from stocgain.analytics.config import AnalyticsConfig
from stocgain.analytics.risk import score_position
from stocgain.analytics.scenario import ScenarioParameters, evaluate
from stocgain.analytics.types import ModelInputs, ModelOutputs


def hero_inputs():
    config = AnalyticsConfig()
    position = {
        "store_id": 3,
        "product_id": 187,
        "supplier_id": 1,
        "category_id": 4,
        "category_code": "PL",
        "on_hand_units": 100,
        "unit_price": 24.98,
        "unit_cost": 15.49,
        "case_pack_qty": 12,
        "min_order_qty": 24,
    }
    forecast = {
        "store_id": 3,
        "product_id": 187,
        "method": "store_sku",
        "base_daily_demand": 12.0,
        "daily_demand_std": 5.0,
    }
    lane = {
        "store_id": 3,
        "supplier_id": 1,
        "mean_lead_time_days": 10.0,
        "std_lead_time_days": 2.0,
        "std_delay_days": 2.0,
        "mean_delay_days": 0.0,
        "mean_delay_when_late_days": 3.0,
    }
    inputs = ModelInputs(
        date(2026, 9, 30), config, [position], [], [], [], [], [], [], [], []
    )
    result, checkpoints, recommendation = score_position(
        position, forecast, [12.0] * 42, lane, [], inputs.as_of, config
    )
    outputs = ModelOutputs(
        [forecast],
        [
            {"store_id": 3, "product_id": 187, "horizon_day": i, "forecast_units": 12.0}
            for i in range(1, 43)
        ],
        [lane],
        [result],
        checkpoints,
        [recommendation],
    )
    return inputs, outputs


def test_neutral_g12_is_identical_per_position_and_aggregate():
    inputs, outputs = hero_inputs()
    result = evaluate(inputs, outputs, ScenarioParameters())
    assert result["baseline"] == result["scenario"]
    assert result["position_results"][0]["scenario"] == outputs.risks[0]
    assert all(value == 0 for value in result["delta"]["absolute"].values())
    assert result["tier_transitions"]["matrix"][0][0] == 1


def test_scenario_g5_and_g6_tradeoffs():
    inputs, outputs = hero_inputs()
    g5 = evaluate(
        inputs,
        outputs,
        ScenarioParameters(lead_time_change_days=4, demand_change_rate=0.2),
    )
    assert g5["scenario"]["margin_at_risk_usd"] == pytest.approx(626.90, abs=0.05)
    assert g5["scenario"]["recommended_order_units"] == 276
    g6 = evaluate(inputs, outputs, ScenarioParameters(service_level=0.98))
    assert (
        g6["scenario"]["mean_stockout_probability"]
        == g6["baseline"]["mean_stockout_probability"]
    )
    assert g6["scenario"]["recommended_order_units"] == 180
    assert g6["scenario"]["annual_carrying_cost_usd"] == pytest.approx(228.58, abs=0.05)
    assert g6["scenario"]["annual_expected_shortfall_margin_usd"] == pytest.approx(
        74.58, abs=0.05
    )


def test_empty_scope_zero_summaries_and_floor_warnings():
    inputs, outputs = hero_inputs()
    empty = evaluate(inputs, outputs, ScenarioParameters(store_ids=(999,)))
    assert empty["positions_in_scope"] == 0
    assert empty["top_changes"] == []
    assert empty["scenario"]["mean_stockout_probability"] == 0
    assert empty["delta"]["relative"]["margin_at_risk_usd"] is None
    outputs.lanes[0]["mean_lead_time_days"] = 2
    result = evaluate(
        inputs,
        outputs,
        ScenarioParameters(lead_time_change_days=-7, service_level=0.995),
    )
    assert result["scenario"]["avg_lead_time_days"] == 1
    assert len(result["warnings"]) == 2


def test_changed_protection_window_reselects_upcoming_promotion():
    inputs, outputs = hero_inputs()
    from datetime import timedelta

    promo = {
        "store_id": 3,
        "product_id": 187,
        "target_date": inputs.as_of + timedelta(days=12),
        "start_date": inputs.as_of + timedelta(days=12),
        "promotion_name": "Test promotion",
        "planned_lift": 1.2,
    }
    inputs.promotions.append(promo)
    changed = evaluate(inputs, outputs, ScenarioParameters(lead_time_change_days=4))
    assert (
        "upcoming_promotion"
        in changed["position_results"][0]["scenario"]["risk_drivers"]
    )
    assert "upcoming_promotion" not in inputs.positions[0]
