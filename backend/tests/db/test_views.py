"""Phase 2 views against real operational data."""

import pytest
from sqlalchemy import text

from stocgain.db.sql_loader import SQL_ROOT

pytestmark = pytest.mark.db


def test_required_view_inventory():
    assert len(list((SQL_ROOT / "views").glob("*.sql"))) == 12


def test_daily_position_availability(db_tx):
    rows = (
        db_tx.execute(text("SELECT * FROM analytics.mv_daily_position"))
        .mappings()
        .all()
    )
    assert len(rows) == 21600
    for r in rows:
        available = r["opening_on_hand"] + r["units_received"]
        expected = (
            "out_all_day"
            if available == 0
            else "sold_out"
            if r["units_sold"] >= available
            else "in_stock"
        )
        assert r["availability_status"] == expected
        assert r["is_censored"] == (expected != "in_stock")
        assert r["closing_on_hand"] == available - r["units_sold"] + r["net_adjustment"]


def test_po_quantities_and_episodes(db_tx):
    assert (
        db_tx.scalar(
            text(
                "SELECT count(*) FROM analytics.v_po_line_status WHERE open_quantity < 0 OR open_quantity <> quantity_ordered - quantity_received - quantity_cancelled"
            )
        )
        == 0
    )
    assert (
        db_tx.scalar(
            text(
                "SELECT count(*) FROM analytics.v_po_status WHERE first_receipt_date IS NOT NULL AND lead_time_days <= 0"
            )
        )
        == 0
    )
    assert (
        db_tx.scalar(
            text(
                "SELECT count(*) FROM analytics.v_inventory_reconciliation WHERE discrepancy <> 0"
            )
        )
        == 0
    )
    assert (
        db_tx.scalar(
            text("""WITH a AS (SELECT store_id,product_id,count(*) AS n FROM analytics.mv_daily_position WHERE is_censored GROUP BY 1,2),
    b AS (SELECT store_id,product_id,sum(episode_days) AS n FROM analytics.v_stockout_episodes GROUP BY 1,2)
    SELECT count(*) FROM a FULL JOIN b USING(store_id,product_id) WHERE a.n IS DISTINCT FROM b.n""")
        )
        == 0
    )


def test_current_run_views(db_tx, sql_run):
    assert db_tx.scalar(text("SELECT count(*) FROM analytics.v_current_risk")) == 1
    assert db_tx.scalar(text("SELECT sum(positions) FROM analytics.v_risk_trend")) == 1
    indices = db_tx.execute(
        text(
            "SELECT category_id,avg(dow_index) FROM analytics.v_category_dow_profile GROUP BY category_id"
        )
    ).all()
    assert len(indices) == 8
    assert all(abs(float(value) - 1) < 1e-9 for _, value in indices)
    assert (
        db_tx.scalar(
            text(
                "SELECT abc_class FROM analytics.v_product_abc_class ORDER BY revenue DESC,product_id LIMIT 1"
            )
        )
        == "A"
    )


def test_supplier_view_without_run_is_empty(db_tx):
    assert (
        db_tx.scalar(text("SELECT count(*) FROM analytics.v_supplier_performance")) == 0
    )


def test_competing_runs_choose_successful_current_then_latest(db_tx, sql_run):
    from stocgain.db.models import Base

    tables = Base.metadata.tables
    runs = tables["analytics.analytics_runs"]
    risk = tables["analytics.inventory_risk_snapshots"]
    original = dict(
        db_tx.execute(risk.select().where(risk.c.run_id == sql_run)).mappings().one()
    )

    def add(kind, status, day, completed):
        run = db_tx.execute(
            runs.insert()
            .values(
                run_type=kind,
                status=status,
                error_message="Expected fixture failure"
                if status == "failed"
                else None,
                as_of_date=day,
                completed_at=completed,
                model_version="test-selection",
                config={},
                dataset_checksum="0" * 64,
            )
            .returning(runs.c.run_id)
        ).scalar_one()
        for name in ("demand_forecasts", "supplier_lane_estimates"):
            table = tables[f"analytics.{name}"]
            source = dict(
                db_tx.execute(table.select().where(table.c.run_id == sql_run))
                .mappings()
                .one()
            )
            db_tx.execute(table.insert().values(**(source | {"run_id": run})))
        db_tx.execute(risk.insert().values(**(original | {"run_id": run})))
        return run

    add("backfill", "succeeded", "2026-09-30", "2026-10-04T00:00:00+00")
    newer = add("current", "succeeded", "2026-09-30", "2026-10-02T00:00:00+00")
    add("current", "failed", "2026-09-30", "2026-10-03T00:00:00+00")
    add("current", "running", "2026-10-01", None)
    earlier = add("backfill", "succeeded", "2026-09-23", "2026-10-02T00:00:00+00")
    assert db_tx.scalar(text("SELECT run_id FROM analytics.v_current_run")) == newer
    trend = db_tx.execute(
        text("SELECT run_id,sum(positions) FROM analytics.v_risk_trend GROUP BY run_id")
    ).all()
    assert dict(trend) == {newer: 1, earlier: 1}
    later = add("current", "succeeded", "2026-10-01", "2026-10-02T00:00:00+00")
    assert db_tx.scalar(text("SELECT run_id FROM analytics.v_current_run")) == later
