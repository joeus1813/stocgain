"""Clean-data and deliberate corruption tests on actual PostgreSQL rows."""

import pytest
from sqlalchemy import text
from typer.testing import CliRunner

from stocgain.cli import app
from stocgain.db.sql_loader import SQL_ROOT
from stocgain.quality.checks import check_connection

pytestmark = pytest.mark.db


def run_check(connection, code):
    path = next((SQL_ROOT / "quality").glob(code + "_*.sql"))
    return connection.execute(text(path.read_text())).fetchall()


def test_data_quality_clean(loaded_small_db):
    with loaded_small_db.connect() as connection:
        results = check_connection(connection)
    assert len(results) == 18
    assert all(r.violations == 0 for r in results)


@pytest.mark.parametrize(
    ("code", "mutation"),
    [
        (
            "DQ01",
            "UPDATE ops.inventory_snapshots SET closing_on_hand=closing_on_hand+1 WHERE store_id=1 AND product_id=1 AND snapshot_date='2026-09-29'",
        ),
        (
            "DQ02",
            "UPDATE ops.inventory_snapshots SET opening_on_hand=opening_on_hand+1 WHERE store_id=1 AND product_id=1 AND snapshot_date='2026-09-29'",
        ),
        (
            "DQ03",
            "UPDATE ops.daily_sales SET units_sold=1000000 WHERE store_id=1 AND product_id=1 AND sales_date='2026-09-29'",
        ),
        (
            "DQ04",
            "DELETE FROM ops.daily_sales WHERE store_id=1 AND product_id=1 AND sales_date='2026-09-29'",
        ),
        (
            "DQ05",
            "UPDATE ops.inventory_receipts SET quantity_received=1000000 WHERE receipt_id=(SELECT min(receipt_id) FROM ops.inventory_receipts)",
        ),
        (
            "DQ06",
            "UPDATE ops.inventory_receipts r SET received_date=p.order_date FROM ops.purchase_order_lines l JOIN ops.purchase_orders p USING(purchase_order_id) WHERE r.po_line_id=l.po_line_id AND r.receipt_id=(SELECT min(receipt_id) FROM ops.inventory_receipts)",
        ),
        (
            "DQ07",
            "DELETE FROM ops.product_suppliers WHERE product_id=(SELECT product_id FROM ops.purchase_order_lines ORDER BY po_line_id LIMIT 1)",
        ),
        ("DQ08", "DELETE FROM ops.product_suppliers WHERE product_id=1"),
        (
            "DQ09",
            "INSERT INTO ops.promotions SELECT 9999,'PRM-9999','Corrupted overlapping plan',region_id,start_date,end_date,discount_rate,planned_lift FROM ops.promotions WHERE promotion_id=1; INSERT INTO ops.promotion_products SELECT 9999,product_id FROM ops.promotion_products WHERE promotion_id=1",
        ),
        (
            "DQ10",
            "UPDATE ops.daily_sales SET net_sales_amount=net_sales_amount+100 WHERE (store_id,product_id,sales_date)=(SELECT store_id,product_id,sales_date FROM ops.daily_sales WHERE units_sold>0 ORDER BY sales_date,store_id,product_id LIMIT 1)",
        ),
        (
            "DQ11",
            "UPDATE ops.daily_sales SET cogs_amount=cogs_amount+100 WHERE (store_id,product_id,sales_date)=(SELECT store_id,product_id,sales_date FROM ops.daily_sales WHERE units_sold>0 ORDER BY sales_date,store_id,product_id LIMIT 1)",
        ),
        (
            "DQ12",
            "UPDATE ops.inventory_receipts SET received_date='2026-10-01' WHERE receipt_id=(SELECT min(receipt_id) FROM ops.inventory_receipts)",
        ),
        (
            "DQ15",
            "UPDATE sim_truth.latent_demand SET latent_units=0 WHERE (store_id,product_id,demand_date)=(SELECT store_id,product_id,sales_date FROM ops.daily_sales WHERE units_sold>0 ORDER BY sales_date,store_id,product_id LIMIT 1)",
        ),
        ("DQ16", "DELETE FROM ops.dataset_manifest"),
    ],
)
def test_data_quality_detects_corruption(db_tx, code, mutation):
    assert run_check(db_tx, code) == []
    expected = 1
    if code == "DQ07":
        expected = db_tx.scalar(
            text(
                "SELECT count(*) FROM ops.purchase_order_lines WHERE product_id=(SELECT product_id FROM ops.purchase_order_lines ORDER BY po_line_id LIMIT 1)"
            )
        )
    elif code == "DQ09":
        expected = db_tx.scalar(
            text("SELECT count(*) FROM ops.promotion_products WHERE promotion_id=1")
        )
    db_tx.execute(text(mutation))
    found = run_check(db_tx, code)
    assert len(found) == expected
    assert found


def test_data_quality_cli_nonzero(db_tx, monkeypatch):
    from contextlib import contextmanager

    class TransactionEngine:
        @contextmanager
        def connect(self):
            yield db_tx

        def dispose(self):
            pass

    # Bind the real transaction so the CLI sees the uncommitted corruption.
    monkeypatch.setattr("stocgain.cli.create_db_engine", lambda _: TransactionEngine())
    monkeypatch.setattr("stocgain.cli.validate", lambda _: check_connection(db_tx))
    db_tx.execute(
        text(
            "UPDATE ops.inventory_snapshots SET closing_on_hand=closing_on_hand+1 WHERE store_id=1 AND product_id=1 AND snapshot_date='2026-09-29'"
        )
    )
    result = CliRunner().invoke(app, ["data", "validate"])
    assert result.exit_code == 1
    assert "DQ01_inventory_equation\terror\t1" in result.output


def test_data_quality_history_dates(db_tx):
    rows = db_tx.execute(
        text(
            "SELECT min(sales_date),max(sales_date),count(DISTINCT sales_date),count(*) FROM ops.daily_sales"
        )
    ).one()
    assert tuple(map(str, rows[:2])) == ("2026-06-03", "2026-09-30")
    assert rows[2:] == (120, 21600)
