"""Constraint rejection tests from docs/10 §2 on a populated PostgreSQL DB."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.db


@pytest.mark.parametrize(
    ("statement", "sqlstate"),
    [
        ("INSERT INTO ops.daily_sales VALUES (32000,1,'2026-09-30',1,20,10)", "23503"),
        (
            "INSERT INTO ops.purchase_order_lines VALUES (999999,999999,1,1,1,0,10)",
            "23503",
        ),
        (
            "INSERT INTO ops.inventory_receipts VALUES (999999,999999,'2026-09-30',1)",
            "23503",
        ),
        (
            "UPDATE ops.products SET sku=(SELECT sku FROM ops.products WHERE product_id=1) WHERE product_id=2",
            "23505",
        ),
        ("INSERT INTO ops.daily_sales SELECT * FROM ops.daily_sales LIMIT 1", "23505"),
        (
            "UPDATE ops.inventory_snapshots SET closing_on_hand=-1 WHERE store_id=1 AND product_id=1",
            "23514",
        ),
        ("UPDATE ops.products SET unit_price=unit_cost WHERE product_id=1", "23514"),
        ("UPDATE ops.products SET unit_price=0 WHERE product_id=1", "23514"),
        ("INSERT INTO ops.product_suppliers VALUES (1,10,true,6,12)", "23505"),
        (
            "UPDATE ops.purchase_orders SET promised_delivery_date=order_date WHERE purchase_order_id=100001",
            "23514",
        ),
        (
            "UPDATE ops.purchase_order_lines SET quantity_cancelled=quantity_ordered+1 WHERE po_line_id=300001",
            "23514",
        ),
        (
            "UPDATE ops.inventory_adjustments SET quantity_delta=0 WHERE adjustment_id=(SELECT min(adjustment_id) FROM ops.inventory_adjustments)",
            "23514",
        ),
        (
            "UPDATE ops.inventory_adjustments SET quantity_delta=1,reason_code='shrink' WHERE adjustment_id=(SELECT min(adjustment_id) FROM ops.inventory_adjustments WHERE reason_code='shrink')",
            "23514",
        ),
        ("UPDATE ops.products SET product_name=NULL WHERE product_id=1", "23502"),
        (
            "UPDATE ops.product_suppliers SET min_order_qty=1,case_pack_qty=6 WHERE product_id=1",
            "23514",
        ),
        ("SELECT 'not_a_tier'::analytics.risk_tier", "22P02"),
        (
            "INSERT INTO ops.stores VALUES (32000,'S99','Constraint Store','Atlanta','GA',1,'2020-01-01',1000,true); INSERT INTO ops.purchase_orders VALUES (999999,'PO-999999',1,32000,'2026-09-01','2026-09-10')",
            "23503",
        ),
        ("UPDATE ops.dataset_manifest SET dataset_id=2", "23514"),
    ],
)
def test_constraints_reject_invalid_data(db_tx, statement, sqlstate):
    with pytest.raises(DBAPIError) as caught, db_tx.begin_nested():
        db_tx.execute(text(statement))
    assert caught.value.orig.sqlstate == sqlstate


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE analytics.inventory_risk_snapshots SET stockout_probability=1.2 WHERE run_id=:run",
        "UPDATE analytics.inventory_risk_snapshots SET inventory_position_units=999 WHERE run_id=:run",
        "UPDATE analytics.replenishment_recommendations SET action_type='expedite_po',urgency='urgent',priority_rank=1 WHERE run_id=:run",
        "UPDATE analytics.replenishment_recommendations SET priority_rank=1 WHERE run_id=:run",
    ],
)
def test_constraints_risk_and_recommendation(db_tx, risk_position, statement):
    with pytest.raises(DBAPIError) as caught, db_tx.begin_nested():
        db_tx.execute(text(statement), {"run": risk_position})
    assert caught.value.orig.sqlstate == "23514"


def test_constraints_single_binding_checkpoint(db_tx, risk_position):
    from stocgain.db.models import Base

    table = Base.metadata.tables["analytics.risk_checkpoints"]
    values = dict(
        run_id=risk_position,
        store_id=1,
        product_id=1,
        checkpoint_type="window_end",
        window_days=10,
        window_std_days=2,
        supply_units=100,
        demand_mean_units=120,
        demand_std_units=28.74,
        distribution_family="normal",
        stockout_probability=0.7568,
        expected_shortage_units=24.14,
        is_binding=True,
    )
    db_tx.execute(table.insert().values(checkpoint_seq=1, **values))
    with pytest.raises(DBAPIError) as caught, db_tx.begin_nested():
        db_tx.execute(table.insert().values(checkpoint_seq=2, **values))
    assert caught.value.orig.sqlstate == "23505"


def test_models_match_migrated_schema(loaded_small_db):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from stocgain.db.models import Base

    with loaded_small_db.connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={
                "include_schemas": True,
                "include_name": lambda name, type_, parent: (
                    type_ != "schema" or name in ("ops", "analytics", "sim_truth")
                ),
                "compare_type": True,
            },
        )
        assert compare_metadata(context, Base.metadata) == []
