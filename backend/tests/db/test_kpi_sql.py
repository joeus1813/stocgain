"""KPI tests use rollback-only illustrative fixtures, never model outputs in production."""

from decimal import Decimal

import pytest
from sqlalchemy import text

from stocgain.db.sql_loader import read_sql

pytestmark = pytest.mark.db


def summary(connection, run, **filters):
    params = dict(
        run_id=run,
        prior_run_id=None,
        as_of_date="2026-09-30",
        store_ids=None,
        region_ids=None,
        category_ids=None,
    )
    params.update(filters)
    return (
        connection.execute(text(read_sql("api/overview_summary.sql")), params)
        .mappings()
        .one()
    )


def test_kpi_missing_prior_and_filter_totals(db_tx, sql_run):
    chain = summary(db_tx, sql_run)
    assert chain["prior_at_risk_positions"] is None
    assert chain["active_positions"] == chain["at_risk_positions"] == 1
    assert chain["gross_margin_at_risk_usd"] == Decimal("148.88")
    assert chain["median_days_of_cover"] == 8.3
    stores = db_tx.execute(text("SELECT store_id FROM ops.stores")).scalars().all()
    assert (
        sum(summary(db_tx, sql_run, store_ids=[s])["at_risk_positions"] for s in stores)
        == chain["at_risk_positions"]
    )
    empty = summary(db_tx, sql_run, store_ids=[])
    assert empty["active_positions"] == 0 and empty["supplier_on_time_rate"] is None
    expected = db_tx.scalar(
        text(
            "SELECT avg((closing_on_hand>0)::int) FROM ops.inventory_snapshots WHERE snapshot_date BETWEEN '2026-09-03' AND '2026-09-30'"
        )
    )
    assert chain["in_stock_rate"] == expected


def test_kpi_supplier_rate_uses_all_due_pos(db_tx, sql_run):
    expected = db_tx.execute(
        text("""SELECT count(*),count(*) FILTER(WHERE first_receipt_date<=promised_delivery_date)::numeric/nullif(count(*),0)
    FROM analytics.v_po_status WHERE promised_delivery_date BETWEEN '2026-07-03' AND '2026-09-30'""")
    ).one()
    actual = summary(db_tx, sql_run)
    assert (actual["supplier_pos_due"], actual["supplier_on_time_rate"]) == tuple(
        expected
    )
    supplier_category = db_tx.scalar(
        text("SELECT primary_category_id FROM ops.suppliers WHERE supplier_id=1")
    )
    filtered = summary(db_tx, sql_run, category_ids=[supplier_category])
    due = db_tx.scalar(
        text("""SELECT count(*) FROM analytics.v_po_status v JOIN ops.suppliers s USING(supplier_id)
    WHERE s.primary_category_id=:category AND v.promised_delivery_date BETWEEN '2026-07-03' AND '2026-09-30'"""),
        {"category": supplier_category},
    )
    assert filtered["supplier_pos_due"] == due


@pytest.mark.requires_run
def test_real_current_run_kpi(loaded_small_db):
    with loaded_small_db.connect() as connection:
        run = connection.scalar(text("SELECT run_id FROM analytics.v_current_run"))
        if run is None:
            pytest.skip(
                "Phase 3 must generate actual model outputs; rollback SQL fixtures are covered separately"
            )
        actual = summary(connection, run)
        expected = connection.scalar(
            text(
                "SELECT count(*) FROM analytics.v_current_risk WHERE risk_tier IN ('high','critical')"
            )
        )
        assert actual["at_risk_positions"] == expected
