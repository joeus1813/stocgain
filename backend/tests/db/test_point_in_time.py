"""Historical extraction must be invariant to removal of future observations."""

from datetime import timedelta

import pytest
from sqlalchemy import text

from stocgain.db.sql_loader import SQL_ROOT, read_sql

pytestmark = pytest.mark.db


def extract_all(connection, as_of):
    results = {}
    files = sorted((SQL_ROOT / "pipeline").glob("*.sql"))
    assert len(files) == 11
    for path in files:
        rows = connection.execute(
            text(read_sql(path)), {"as_of": as_of, "history_days": 56}
        ).all()
        results[path.name] = sorted([tuple(r) for r in rows], key=repr)
    return results


def test_point_in_time_future_deletion(db_tx):
    as_of = db_tx.scalar(
        text("SELECT history_end_date FROM ops.dataset_manifest")
    ) - timedelta(days=30)
    before = extract_all(db_tx, as_of)
    for table, column in [
        ("daily_sales", "sales_date"),
        ("inventory_snapshots", "snapshot_date"),
        ("inventory_receipts", "received_date"),
        ("inventory_adjustments", "adjustment_date"),
    ]:
        db_tx.execute(
            text(f"DELETE FROM ops.{table} WHERE {column} > :as_of"), {"as_of": as_of}
        )
    db_tx.execute(
        text(
            "DELETE FROM ops.purchase_order_lines WHERE purchase_order_id IN (SELECT purchase_order_id FROM ops.purchase_orders WHERE order_date > :as_of)"
        ),
        {"as_of": as_of},
    )
    db_tx.execute(
        text("DELETE FROM ops.purchase_orders WHERE order_date > :as_of"),
        {"as_of": as_of},
    )
    db_tx.execute(text("REFRESH MATERIALIZED VIEW analytics.mv_daily_position"))
    assert before == extract_all(db_tx, as_of)


def test_chain_rate_is_deseasonalized_for_forecast_contract(db_tx):
    from collections import defaultdict
    from decimal import Decimal

    as_of = db_tx.scalar(text("SELECT history_end_date FROM ops.dataset_manifest"))
    params = {"as_of": as_of, "history_days": 56}
    indices = {
        (r["category_id"], r["iso_day_of_week"]): r["dow_index"]
        for r in db_tx.execute(
            text(read_sql("pipeline/extract_category_dow_profile.sql")), params
        ).mappings()
    }
    history = (
        db_tx.execute(text(read_sql("pipeline/extract_daily_history.sql")), params)
        .mappings()
        .all()
    )
    values = defaultdict(list)
    for r in history:
        if r["availability_status"] == "in_stock" and not r["is_promo_day"]:
            idx = indices.get((r["category_id"], r["iso_day_of_week"])) or Decimal(1)
            values[r["product_id"]].append(Decimal(r["units_sold"]) / idx)
    actual = (
        db_tx.execute(text(read_sql("pipeline/extract_product_chain_rate.sql")), params)
        .mappings()
        .all()
    )
    for r in actual:
        expected = values[r["product_id"]]
        assert r["n_clean_chain"] == len(expected)
        assert abs(r["chain_rate"] - sum(expected) / len(expected)) < Decimal("1e-9")


def test_cancellation_not_known_before_first_receipt(db_tx):
    line = (
        db_tx.execute(
            text("""SELECT l.po_line_id,p.order_date,l.quantity_ordered,l.quantity_cancelled,min(r.received_date) AS first_date
    FROM ops.purchase_order_lines l JOIN ops.purchase_orders p USING(purchase_order_id)
    JOIN ops.inventory_receipts r USING(po_line_id) WHERE l.quantity_cancelled>0
    GROUP BY l.po_line_id,p.order_date LIMIT 1""")
        )
        .mappings()
        .one()
    )
    sql = read_sql("pipeline/extract_open_po_lines.sql")
    before = (
        db_tx.execute(text(sql), {"as_of": line["first_date"] - timedelta(days=1)})
        .mappings()
        .all()
    )
    # The contract's line identity is PO/product, resolved independently.
    key = db_tx.execute(
        text(
            "SELECT purchase_order_id,product_id FROM ops.purchase_order_lines WHERE po_line_id=:id"
        ),
        {"id": line["po_line_id"]},
    ).one()
    row = next(
        r for r in before if (r["purchase_order_id"], r["product_id"]) == tuple(key)
    )
    assert row["open_quantity_as_of"] == line["quantity_ordered"]
    after = db_tx.execute(text(sql), {"as_of": line["first_date"]}).mappings().all()
    assert not any(
        (r["purchase_order_id"], r["product_id"]) == tuple(key) for r in after
    )


@pytest.mark.parametrize("days", [3, 7])
def test_chain_rate_flat_profile_with_sparse_weekdays(db_tx, days):
    from decimal import Decimal

    start = db_tx.scalar(text("SELECT history_start_date FROM ops.dataset_manifest"))
    cutoff = start + timedelta(days=days - 1)
    params = {"as_of": cutoff, "history_days": days}
    # Restrict a category to two positions, giving fewer than 30 observations
    # per weekday; days=3 additionally omits weekdays. These mutations roll back.
    db_tx.execute(
        text("""DELETE FROM ops.daily_sales d USING ops.products p
    WHERE d.product_id=p.product_id AND p.category_id=1 AND NOT (d.store_id=1 AND d.product_id IN (1,2))""")
    )
    db_tx.execute(
        text(
            "UPDATE ops.daily_sales SET units_sold=CASE WHEN product_id=1 THEN extract(isodow FROM sales_date)::int*2 ELSE 1 END WHERE store_id=1 AND product_id IN (1,2)"
        )
    )
    db_tx.execute(
        text(
            "UPDATE ops.inventory_snapshots SET opening_on_hand=100 WHERE store_id=1 AND product_id IN (1,2)"
        )
    )
    db_tx.execute(
        text(
            "DELETE FROM ops.promotion_products WHERE product_id IN (SELECT product_id FROM ops.products WHERE category_id=1)"
        )
    )
    db_tx.execute(text("REFRESH MATERIALIZED VIEW analytics.mv_daily_position"))
    expected = db_tx.scalar(
        text("""SELECT avg(units_sold) FROM analytics.mv_daily_position
    WHERE product_id=1 AND position_date<=:as_of AND availability_status='in_stock' AND NOT is_promo_day"""),
        params,
    )
    rows = (
        db_tx.execute(text(read_sql("pipeline/extract_product_chain_rate.sql")), params)
        .mappings()
        .all()
    )
    row = next(r for r in rows if r["product_id"] == 1)
    assert abs(row["chain_rate"] - expected) < Decimal("1e-9")


def test_historical_supplier_views_ignore_future_receipts(db_tx, sql_run):
    as_of = db_tx.scalar(
        text("SELECT history_end_date FROM ops.dataset_manifest")
    ) - timedelta(days=30)
    db_tx.execute(
        text("UPDATE analytics.analytics_runs SET as_of_date=:as_of WHERE run_id=:run"),
        {"as_of": as_of, "run": sql_run},
    )

    def snapshots():
        result = {
            name: sorted(
                [
                    tuple(r)
                    for r in db_tx.execute(text(f"SELECT * FROM analytics.{name}"))
                ],
                key=repr,
            )
            for name in ("v_supplier_lane_performance", "v_supplier_performance")
        }

        result["overview_summary"] = [
            tuple(
                db_tx.execute(
                    text(read_sql("api/overview_summary.sql")),
                    dict(
                        run_id=sql_run,
                        prior_run_id=None,
                        as_of_date=as_of,
                        store_ids=None,
                        region_ids=None,
                        category_ids=None,
                    ),
                ).one()
            )
        ]
        return result

    before = snapshots()
    db_tx.execute(
        text("DELETE FROM ops.inventory_receipts WHERE received_date>:as_of"),
        {"as_of": as_of},
    )
    db_tx.execute(
        text(
            "DELETE FROM ops.purchase_order_lines WHERE purchase_order_id IN (SELECT purchase_order_id FROM ops.purchase_orders WHERE order_date>:as_of)"
        ),
        {"as_of": as_of},
    )
    db_tx.execute(
        text("DELETE FROM ops.purchase_orders WHERE order_date>:as_of"),
        {"as_of": as_of},
    )
    assert before == snapshots()
