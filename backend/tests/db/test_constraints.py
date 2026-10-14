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


@pytest.fixture
def risk_position(db_tx):
    from stocgain.db.models import Base

    t = Base.metadata.tables
    run = db_tx.execute(
        t["analytics.analytics_runs"]
        .insert()
        .values(
            run_type="current",
            as_of_date="2026-09-30",
            model_version="test",
            config={},
            dataset_checksum="0" * 64,
        )
        .returning(t["analytics.analytics_runs"].c.run_id)
    ).scalar_one()
    db_tx.execute(
        t["analytics.demand_forecasts"]
        .insert()
        .values(
            run_id=run,
            store_id=1,
            product_id=1,
            method="store_sku",
            demand_pattern="smooth",
            lookback_days=56,
            clean_days=49,
            censored_days=4,
            promo_days=3,
            base_daily_demand=12,
            daily_demand_std=5,
            forecast_7d_units=84,
            forecast_14d_units=168,
            forecast_28d_units=336,
            forecast_7d_std_units=13.23,
            forecast_14d_std_units=18.71,
            forecast_28d_std_units=26.46,
        )
    )
    db_tx.execute(
        t["analytics.supplier_lane_estimates"]
        .insert()
        .values(
            run_id=run,
            supplier_id=1,
            store_id=1,
            lead_time_source="lane",
            n_received_pos=27,
            mean_lead_time_days=10,
            std_lead_time_days=2,
            mean_delay_days=0.92,
            std_delay_days=1.88,
            mean_delay_when_late_days=3.10,
            on_time_rate=0.7037,
        )
    )
    db_tx.execute(
        t["analytics.inventory_risk_snapshots"]
        .insert()
        .values(
            run_id=run,
            store_id=1,
            product_id=1,
            supplier_id=1,
            on_hand_units=100,
            on_order_units=0,
            inventory_position_units=100,
            open_po_count=0,
            next_receipt_overdue=False,
            avg_daily_demand_units=12,
            daily_demand_std_units=5,
            days_of_cover=8.3,
            lead_time_mean_days=10,
            lead_time_std_days=2,
            protection_window_days=10,
            lead_time_demand_mean_units=120,
            lead_time_demand_std_units=28.74,
            distribution_family="normal",
            service_level=0.95,
            safety_stock_units=47.27,
            reorder_point_units=168,
            order_up_to_units=257,
            below_reorder_point=True,
            binding_checkpoint_type="window_end",
            binding_window_days=10,
            binding_supply_units=100,
            binding_demand_mean_units=120,
            binding_demand_std_units=28.74,
            stockout_probability=0.7568,
            expected_shortage_units=24.14,
            lost_sale_rate=0.65,
            expected_lost_units=15.69,
            revenue_at_risk_usd=391.88,
            margin_at_risk_usd=148.88,
            currently_out_of_stock=False,
            recent_censored_days=2,
            risk_tier="critical",
            explanation="Illustrative test fixture.",
        )
    )
    db_tx.execute(
        t["analytics.replenishment_recommendations"]
        .insert()
        .values(
            run_id=run,
            store_id=1,
            product_id=1,
            supplier_id=1,
            action_type="no_action",
            rationale="Constraint fixture",
        )
    )
    return run


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
