"""Independent numerical examples and boundary rules from docs/05."""

from datetime import date, timedelta

import pytest

from stocgain.analytics import distributions, leadtime, policy, risk
from stocgain.analytics.config import AnalyticsConfig

T = date(2026, 9, 30)


def test_window_and_count_golden():
    mean, std = distributions.window_demand([0.4] * 42, 8, 2, 0.9)
    assert mean == pytest.approx(3.2)
    assert std**2 == pytest.approx(7.12)
    assert distributions.select_family(mean, std) == "negative_binomial"
    assert distributions.prob_exceeds(mean, std, 2) == pytest.approx(0.5211, abs=0.002)
    assert distributions.expected_shortage(mean, std, 2) == pytest.approx(
        1.6256, abs=0.002
    )
    assert distributions.quantile(mean, std, 0.95) == 8


def test_policy_golden_and_zero():
    p = policy.compute_policy([12.0] * 42, 5, 10, 2, AnalyticsConfig())
    assert p["reorder_point_units"] == 168
    assert p["order_up_to_units"] == 257
    assert (
        policy.order_quantity(100, 168, 257, 12, 24, 15.49)["recommended_order_units"]
        == 168
    )
    assert policy.order_quantity(0, 0, 0, 1, 1, 1)["recommended_order_units"] is None


def test_overdue_and_half_up():
    lane = {"mean_delay_when_late_days": 4, "mean_delay_days": 0.5}
    assert leadtime.expected_arrival(T, T - timedelta(days=2), lane) == T + timedelta(
        days=2
    )
    assert leadtime.expected_arrival(T, T - timedelta(days=6), lane) == T + timedelta(
        days=1
    )
    assert leadtime.expected_arrival(T, T + timedelta(days=2), lane) == T + timedelta(
        days=3
    )


def test_zero_window_and_fractional_forecast():
    assert distributions.window_demand([1.0, 3.0], 0, 4, 2) == (0.0, 0.0)
    assert distributions.window_demand([1.0, 3.0], 1.5, 0, 0) == (2.5, 0.0)
    assert distributions.prob_exceeds(0, 0, 0) == 0
    assert distributions.prob_exceeds(5, 0, 4) == 1


def hero():
    return (
        {
            "store_id": 3,
            "product_id": 187,
            "supplier_id": 1,
            "on_hand_units": 100,
            "unit_price": 24.98,
            "unit_cost": 15.49,
            "case_pack_qty": 12,
            "min_order_qty": 24,
            "lost_sale_rate": 0.65,
            "supplier_name": "Gulfmark Plumbing Supply Co.",
        },
        {
            "daily_demand_std_units": 5.0,
            "deseasonalized_level_units": 12.0,
            "method": "store_sku",
            "recent_censored_days": 0,
        },
        {
            "mean_lead_time_days": 10.0,
            "std_lead_time_days": 2.0,
            "std_delay_days": 2.0,
            "mean_delay_days": 0.0,
            "mean_delay_when_late_days": 3.0,
            "on_time_rate": 0.7037,
        },
    )


def test_hero_end_to_end():
    p, f, lane = hero()
    r, c, a = risk.score_position(p, f, [12.0] * 42, lane, [], T, AnalyticsConfig())
    assert r["stockout_probability"] == pytest.approx(0.7568, abs=0.002)
    assert r["expected_shortage_units"] == pytest.approx(24.14, abs=0.05)
    assert r["margin_at_risk_usd"] == pytest.approx(148.88, abs=0.05)
    assert r["days_until_projected_stockout"] == 9
    assert r["risk_tier"] == "critical"
    assert a["action_type"] == "reorder"
    assert a["recommended_order_units"] == 168
    assert len(c) == 1 and c[0]["is_binding"]


def test_same_eta_orders_combine_without_double_counting():
    p, f, lane = hero()
    orders = [
        {
            "purchase_order_id": i,
            "promised_delivery_date": T + timedelta(days=4),
            "open_quantity_as_of": q,
        }
        for i, q in [(9, 20), (2, 30)]
    ]
    r, c, a = risk.score_position(p, f, [12.0] * 42, lane, orders, T, AnalyticsConfig())
    assert len(c) == 2
    assert c[0]["purchase_order_id"] == 2
    assert c[0]["supply_units"] == 100
    assert c[1]["supply_units"] == 150
    assert r["inventory_position_units"] == 150
    assert r["next_receipt_units"] == 50


def test_exact_boundary_po_excluded_from_protection_but_counted_in_position():
    p, f, lane = hero()
    orders = [
        {
            "purchase_order_id": 1,
            "promised_delivery_date": T + timedelta(days=11),
            "open_quantity_as_of": 500,
        }
    ]
    r, c, a = risk.score_position(p, f, [12.0] * 42, lane, orders, T, AnalyticsConfig())
    assert len(c) == 1 and c[0]["supply_units"] == 100
    assert r["inventory_position_units"] == 600
    assert not r["below_reorder_point"]
    assert a["action_type"] == "expedite_po"


def test_projection_floors_lost_sales_and_sells_start_day_receipt():
    points, first = risk.project_inventory(
        [4.0, 4.0, 4.0],
        1,
        0,
        [{"expected_arrival_date": T + timedelta(days=2), "open_quantity_as_of": 10}],
        T,
    )
    assert first == 1
    assert [p["projected_on_hand_units"] for p in points] == [0, 6, 2]
    assert all(p["low_units"] >= 0 and p["high_units"] >= 0 for p in points)


def test_lane_fallback_hierarchy_and_lane_rate_preserved():
    lane = {"contract_lead_time_days": 10, "n_received": 0, "on_time_rate_90d": 0.2}
    contract = leadtime.select_lane_estimate(lane, {}, AnalyticsConfig())
    assert contract["lead_time_source"] == "contract"
    assert contract["std_lead_time_days"] == 2.5
    supplier = {
        "n_received": 8,
        "mean_delay_days": 2,
        "std_delay_days": 0,
        "mean_delay_when_late_days": 4,
    }
    pooled = leadtime.select_lane_estimate(lane, supplier, AnalyticsConfig())
    assert pooled["mean_lead_time_days"] == 12
    assert pooled["std_lead_time_days"] == 0.5
    assert pooled["on_time_rate"] == 0.2
    lane.update(
        n_received=8,
        mean_lead_time_days=9,
        std_lead_time_days=0.2,
        mean_delay_days=-1,
        std_delay_days=0.1,
        mean_delay_when_late_days=None,
    )
    own = leadtime.select_lane_estimate(lane, supplier, AnalyticsConfig())
    assert own["lead_time_source"] == "lane"
    assert own["mean_lead_time_days"] == 9
    assert own["std_delay_days"] == 0.5
    assert own["mean_delay_when_late_days"] == 3


@pytest.mark.parametrize("mean,std", [(0, 0), (3, 2.5), (3, 1), (25, 7), (100, 20)])
def test_supply_probability_and_shortage_monotonic(mean, std):
    probabilities = [distributions.prob_exceeds(mean, std, s) for s in range(0, 150, 3)]
    shortages = [
        distributions.expected_shortage(mean, std, s) for s in range(0, 150, 3)
    ]
    assert all(0 <= p <= 1 for p in probabilities)
    assert all(a >= b for a, b in zip(probabilities, probabilities[1:], strict=False))
    assert all(
        a + 1e-10 >= b >= 0 for a, b in zip(shortages, shortages[1:], strict=False)
    )


def test_service_level_changes_policy_only_and_normal_variability_monotone():
    p, f, lane = hero()
    outputs = [
        risk.score_position(p, f, [12.0] * 42, lane, [], T, AnalyticsConfig(), a)[0]
        for a in (0.8, 0.9, 0.95, 0.98, 0.995)
    ]
    assert len({r["stockout_probability"] for r in outputs}) == 1
    assert all(
        a["reorder_point_units"] <= b["reorder_point_units"]
        for a, b in zip(outputs, outputs[1:], strict=False)
    )
    policies = [
        policy.compute_policy([12.0] * 42, s, 10, 2, AnalyticsConfig())
        for s in (0, 1, 5, 10, 20)
    ]
    assert all(
        a["safety_stock_units"] <= b["safety_stock_units"]
        for a, b in zip(policies, policies[1:], strict=False)
    )
    assert all(p["reorder_point_units"] <= p["order_up_to_units"] for p in policies)


def test_tier_boundaries_and_insufficient_data_override():
    c = AnalyticsConfig()
    assert risk.assign_tier(0.5, 0, 1, 1, "store_sku", c) == "critical"
    assert risk.assign_tier(0.25, 0, 1, 1, "store_sku", c) == "high"
    assert risk.assign_tier(0.1, 250, 1, 1, "store_sku", c) == "high"
    assert risk.assign_tier(0.1, 249.99, 1, 1, "store_sku", c) == "moderate"
    assert risk.assign_tier(0.09999, 999, 1, 1, "store_sku", c) == "low"
    assert risk.assign_tier(1, 999, 0, 20, "insufficient_data", c) == "moderate"


def test_sensitivity_uses_same_scoring_and_keeps_original_inputs():
    p, f, lane = hero()
    result = risk.sensitivity(
        p, f, [12.0] * 42, lane, [], T, AnalyticsConfig(), [1.0] * 42
    )
    baseline = risk.score_position(p, f, [12.0] * 42, lane, [], T, AnalyticsConfig())[
        0
    ]["stockout_probability"]
    assert result["baseline"] == baseline
    assert result["promised_arrival"] == baseline
    assert result["no_promotion"] == baseline
    assert result["reliable_lead_times"] != baseline
    assert lane["std_lead_time_days"] == 2


def test_vector_distribution_batch_matches_golden_families():
    probabilities, shortages = distributions.evaluate_batch(
        [120.0, 3.2, 3.0, 0.0, 5.0],
        [826**0.5, 7.12**0.5, 1.0, 0.0, 0.0],
        [100, 2, 2, 0, 4],
    )
    assert list(probabilities) == pytest.approx(
        [0.7568, 0.5211, 1 - 8.5 * __import__("math").exp(-3), 0, 1], abs=0.002
    )
    assert list(shortages[:2]) == pytest.approx([24.14, 1.6256], abs=0.05)
    assert list(shortages[-2:]) == [0, 1]


def test_recommendation_rank_uses_each_tiebreak_and_null_last():
    from stocgain.analytics.replenishment import rank

    risks = [
        {
            "store_id": 1,
            "product_id": i,
            "risk_tier": tier,
            "margin_at_risk_usd": margin,
            "days_until_projected_stockout": days,
        }
        for i, tier, margin, days in [
            (1, "high", 500, 1),
            (2, "critical", 20, None),
            (3, "critical", 20, 3),
            (4, "critical", 20, 3),
            (5, "critical", 20, 3),
            (6, "critical", 20, 3),
            (7, "low", 0, None),
        ]
    ]
    actions = [
        "reorder",
        "reorder",
        "monitor",
        "reorder",
        "expedite_po",
        "expedite_po",
        "no_action",
    ]
    recommendations = [
        {"store_id": 1, "product_id": i, "action_type": a}
        for i, a in enumerate(actions, 1)
    ]
    ranked = rank(recommendations, risks)
    assert [r["priority_rank"] for r in ranked] == [6, 5, 4, 3, 1, 2, None]


def test_binding_tie_prefers_earliest_then_only_one_binding():
    p, f, lane = hero()
    p["on_hand_units"] = 10000
    orders = [
        {
            "purchase_order_id": 1,
            "promised_delivery_date": T + timedelta(days=4),
            "open_quantity_as_of": 1,
        }
    ]
    _, points, _ = risk.score_position(
        p, f, [12.0] * 42, lane, orders, T, AnalyticsConfig()
    )
    assert [c["is_binding"] for c in points] == [True, False]


def test_insufficient_history_forces_monitor_even_when_po_overdue():
    p, f, lane = hero()
    f.update(method="insufficient_data", base_daily_demand=0, daily_demand_std=0)
    orders = [
        {
            "purchase_order_id": 1,
            "promised_delivery_date": T - timedelta(days=2),
            "open_quantity_as_of": 1,
        }
    ]
    result, _, action = risk.score_position(
        p, f, [0.0] * 42, lane, orders, T, AnalyticsConfig()
    )
    assert result["risk_tier"] == "moderate"
    assert action["action_type"] == "monitor"


def test_driver_descriptions_handle_zero_demand_and_replenishment_days():
    from stocgain.analytics.explanations import describe_driver

    p, f, lane = hero()
    result, _, _ = risk.score_position(
        p, f, [12.0] * 42, lane, [], T, AnalyticsConfig()
    )
    description = describe_driver(
        "coverage_gap", result, {**f, "clean_days": 20}, lane, T
    )
    assert "10.0 days" in description["description"]
    result["days_of_cover"] = None
    description = describe_driver(
        "limited_history", result, {**f, "clean_days": 0}, lane, T
    )
    assert "0 clean" in description["description"]


def test_optimized_shortage_matches_independent_finite_sum():
    from scipy import stats

    from stocgain.analytics.distributions import expected_shortage

    for mean, std in ((0.4, 0.9), (3.2, 7.12**0.5), (10, 10**0.5), (19, 8)):
        distribution = (
            stats.poisson(mean)
            if std**2 <= mean
            else stats.nbinom(mean**2 / (std**2 - mean), mean / std**2)
        )
        for supply in (0, 1, 2, 7, 20, 60):
            if supply > distribution.ppf(1 - 1e-9):
                expected = 0
            else:
                expected = (
                    mean
                    - supply
                    + sum((supply - k) * distribution.pmf(k) for k in range(supply))
                )
            assert expected_shortage(mean, std, supply) == pytest.approx(
                max(0, expected), abs=1e-10
            )
