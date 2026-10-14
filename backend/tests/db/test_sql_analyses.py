"""All fifteen normative analyses execute on PostgreSQL, including empty runs."""

import pytest
from sqlalchemy import text

from stocgain.db.sql_loader import SQL_ROOT, read_sql

pytestmark = pytest.mark.db


def test_analysis_inventory():
    assert len(list((SQL_ROOT / "analyses").glob("*.sql"))) == 15


@pytest.mark.parametrize("number", range(1, 16))
def test_analysis_executes(db_tx, number):
    files = list((SQL_ROOT / "analyses").glob(f"{number:02}_*.sql"))
    assert len(files) == 1
    result = db_tx.execute(text(read_sql(files[0])))
    assert result.keys()
    result.all()


def test_run_analysis_cli(loaded_small_db, monkeypatch):
    from typer.testing import CliRunner

    from stocgain.cli import app
    from stocgain.settings import Settings, get_settings

    monkeypatch.setenv("DATABASE_URL", Settings().test_database_url)
    get_settings.cache_clear()
    try:
        result = CliRunner().invoke(app, ["db", "run-analysis", "06"])
        assert result.exit_code == 0, result.output
        assert "stockout_day_rate" in result.output
        assert CliRunner().invoke(app, ["db", "run-analysis", "../06"]).exit_code != 0
    finally:
        get_settings.cache_clear()


EXPECTED_COLUMNS = {
    1: "store_code sku product_name avg_units_7d avg_units_28d avg_units_28d_in_stock censored_days_28d censoring_gap_units",
    2: "week_start_date category_name region_name units revenue censored_share prior_week_units wow_change_pct units_4wk_moving_avg",
    3: "category_name cover_bucket positions median_cover_days",
    4: "supplier_code supplier_name received_pos avg_contract_lead_time_days mean_lead_time_days std_lead_time_days p50_lead_time_days p90_lead_time_days lead_time_cv mean_days_over_contract variability_rank",
    5: "supplier_code supplier_name pos_recent on_time_rate_recent on_time_rate_prior in_full_rate_recent otif_rate_recent on_time_rate_change worst_first_rank",
    6: "store_code sku product_name out_all_day_days sold_out_days stockout_day_rate stockout_episodes longest_episode_days last_stockout_date",
    7: "store_code rank_in_store sku product_name category_name risk_tier stockout_probability_pct on_hand_units avg_daily_demand_units days_of_cover next_receipt_date margin_at_risk_usd action_type",
    8: "sku product_name category_name at_risk_stores margin_at_risk_usd revenue_at_risk_usd share_of_total cumulative_share",
    9: "region_name positions critical high moderate low at_risk_share at_risk_share_vs_chain margin_at_risk_usd mean_stockout_probability",
    10: "store_code sku product_name clean_days nonzero_days mean_units cv adi cv_squared trend_units_per_day demand_pattern",
    11: "supplier_code promised_month pos lines units_ordered units_received unit_fill_rate split_deliveries lines_closed_short lines_still_open",
    12: "priority_rank store_code store_rank sku product_name risk_tier action_type urgency stockout_probability margin_at_risk_usd recommended_order_units recommended_order_cost_usd cumulative_order_cost_usd",
    13: "store_code reason_code adjustment_events net_units net_value_at_cost_usd",
    14: "abc_class x_products y_products z_products revenue_56d",
    15: "week_start_date region_name in_stock_rate in_stock_rate_promo in_stock_rate_non_promo",
}


def analysis(connection, number):
    path = next((SQL_ROOT / "analyses").glob(f"{number:02}_*.sql"))
    result = connection.execute(text(read_sql(path)))
    assert list(result.keys()) == EXPECTED_COLUMNS[number].split()
    return result.mappings().all()


@pytest.mark.parametrize("number", range(1, 16))
def test_analysis_columns_and_invariants(db_tx, sql_run, number):
    from decimal import Decimal

    rows = analysis(db_tx, number)
    assert rows
    if number == 1:
        assert all(0 <= r["censored_days_28d"] <= 28 for r in rows)
        for row in rows:
            expected = db_tx.execute(
                text("""SELECT round(avg(units_sold),2), count(*) FILTER (WHERE availability_status<>'in_stock')
            FROM analytics.mv_daily_position m JOIN ops.stores s USING(store_id) JOIN ops.products p USING(product_id)
            WHERE s.store_code=:store AND p.sku=:sku AND position_date BETWEEN '2026-09-03' AND '2026-09-30'"""),
                dict(store=row["store_code"], sku=row["sku"]),
            ).one()
            assert (row["avg_units_28d"], row["censored_days_28d"]) == tuple(expected)
    elif number == 2:
        for r in rows:
            dates = db_tx.scalar(
                text(
                    "SELECT count(DISTINCT position_date) FROM analytics.mv_daily_position WHERE position_date BETWEEN :start AND CAST(:start AS date)+6"
                ),
                {"start": r["week_start_date"]},
            )
            assert dates == 7
        groups = {}
        for r in rows:
            group = groups.setdefault((r["category_name"], r["region_name"]), [])
            assert r["prior_week_units"] == (group[-1]["units"] if group else None)
            group.append(r)
    elif number == 3:
        assert (
            sum(r["positions"] for r in rows if r["category_name"] == "All categories")
            == 180
        )
        assert all(
            r["median_cover_days"] is None or 0 <= r["median_cover_days"] <= 365
            for r in rows
        )
    elif number == 4:
        assert all(
            r["received_pos"] > 0 and r["p50_lead_time_days"] <= r["p90_lead_time_days"]
            for r in rows
        )
    elif number == 5:
        for r in rows:
            assert all(
                r[k] is None or 0 <= r[k] <= 1
                for k in [
                    "on_time_rate_recent",
                    "on_time_rate_prior",
                    "in_full_rate_recent",
                    "otif_rate_recent",
                ]
            )
            assert r["otif_rate_recent"] <= min(
                r["on_time_rate_recent"], r["in_full_rate_recent"]
            )
    elif number == 6:
        assert all(
            0 <= r["stockout_day_rate"] <= 1
            and r["longest_episode_days"] <= r["out_all_day_days"] + r["sold_out_days"]
            for r in rows
        )
    elif number == 7:
        assert (
            len(rows) == 1
            and rows[0]["rank_in_store"] == 1
            and rows[0]["risk_tier"] == "critical"
        )
    elif number == 8:
        assert rows[-1]["cumulative_share"] == 1
        assert sum(r["margin_at_risk_usd"] for r in rows) == Decimal("148.88")
    elif number == 9:
        chain = next(r for r in rows if r["region_name"] == "Chain total")
        assert (
            chain["positions"]
            == sum(r["positions"] for r in rows if r["region_name"] != "Chain total")
            == 1
        )
    elif number == 10:
        assert all(r["nonzero_days"] <= r["clean_days"] <= 56 for r in rows)
        assert all(
            r["demand_pattern"]
            in {"no_demand", "smooth", "erratic", "intermittent", "lumpy"}
            for r in rows
        )
    elif number == 11:
        assert all(
            0 <= r["unit_fill_rate"] <= 1 and r["units_received"] <= r["units_ordered"]
            for r in rows
        )
    elif number == 12:
        assert [r["priority_rank"] for r in rows] == list(range(1, len(rows) + 1))
        assert rows[-1]["cumulative_order_cost_usd"] == sum(
            r["recommended_order_cost_usd"] or 0 for r in rows
        )
    elif number == 13:
        total = next(r for r in rows if r["store_code"] == "ALL")
        assert total["net_units"] == db_tx.scalar(
            text("SELECT sum(quantity_delta) FROM ops.inventory_adjustments")
        )
    elif number == 14:
        assert (
            sum(r["x_products"] + r["y_products"] + r["z_products"] for r in rows) == 60
        )
    elif number == 15:
        assert all(0 <= r["in_stock_rate"] <= 1 for r in rows)


@pytest.mark.requires_run
def test_volatility_matches_real_forecast_patterns(db_tx):
    run = db_tx.scalar(text("SELECT run_id FROM analytics.v_current_run"))
    if run is None:
        pytest.skip(
            "Phase 3 actual forecasts required for cross-engine classification comparison"
        )
    expected = dict(
        db_tx.execute(
            text("""SELECT s.store_code || '/' || p.sku, f.demand_pattern::text
    FROM analytics.demand_forecasts f JOIN ops.stores s USING(store_id)
    JOIN ops.products p USING(product_id) WHERE f.run_id=:run"""),
            {"run": run},
        ).all()
    )
    for row in analysis(db_tx, 10):
        if row["clean_days"] >= 14:
            assert (
                row["demand_pattern"] == expected[row["store_code"] + "/" + row["sku"]]
            )
