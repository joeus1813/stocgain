"""Real PostgreSQL position endpoints; fixtures run the actual model."""

import pytest
import sqlalchemy as sa

pytestmark = pytest.mark.api


def position_id(db_tx):
    return db_tx.execute(
        sa.text(
            "SELECT store_id,product_id FROM analytics.inventory_risk_snapshots ORDER BY store_id,product_id LIMIT 1"
        )
    ).one()


def test_position_detail_and_projection_match_stored_run(api_client, db_tx):
    store, product = position_id(db_tx)
    detail = api_client.get(f"/api/v1/positions/{store}/{product}")
    assert detail.status_code == 200, detail.text
    value = detail.json()
    assert (
        value["inventory"]["inventory_position_units"]
        == value["inventory"]["on_hand_units"] + value["inventory"]["on_order_units"]
    )
    assert len([c for c in value["checkpoints"] if c["is_binding"]]) == 1
    projection = api_client.get(f"/api/v1/positions/{store}/{product}/projection")
    assert projection.status_code == 200, projection.text
    assert (
        projection.json()["projected_stockout_date"]
        == value["risk"]["projected_stockout_date"]
    )
    assert (
        len([p for p in projection.json()["points"] if p["kind"] == "projected"]) == 28
    )


def test_position_history_and_orders_actual_rows(api_client, db_tx):
    store, product = position_id(db_tx)
    history = api_client.get(f"/api/v1/positions/{store}/{product}/history?days=7")
    assert history.status_code == 200, history.text
    data = history.json()
    assert len(data["days"]) == 7 and len(data["forecast"]) == 28
    for day in data["days"]:
        assert (
            day["closing_on_hand_units"]
            == day["opening_on_hand_units"]
            + day["units_received"]
            - day["units_sold"]
            + day["net_adjustment_units"]
        )
    orders = api_client.get(
        f"/api/v1/positions/{store}/{product}/purchase-orders?recent_received_limit=0"
    )
    assert orders.status_code == 200, orders.text
    assert orders.json()["recent_received"] == []
    assert all(p["open_quantity"] > 0 for p in orders.json()["open"])


@pytest.mark.parametrize(
    "suffix",
    [
        "/history?days=6",
        "/projection?horizon_days=43",
        "/projection?history_days=57",
        "/purchase-orders?recent_received_limit=21",
    ],
)
def test_position_query_bounds(api_client, db_tx, suffix):
    store, product = position_id(db_tx)
    assert (
        api_client.get(f"/api/v1/positions/{store}/{product}{suffix}").status_code
        == 422
    )


def test_position_invalid_ids(api_client):
    response = api_client.get("/api/v1/positions/999999/1")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "STORE_NOT_FOUND"
    response = api_client.get("/api/v1/positions/1/999999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"
    assert api_client.get("/api/v1/positions/no/1").status_code == 422


def test_position_not_scored_and_history_dates(api_client, db_tx):
    store, product = position_id(db_tx)
    response = api_client.get(f"/api/v1/positions/{store}/{product}/history?days=14")
    assert response.status_code == 200, response.text
    body = response.json()
    assert [d["date"] for d in body["days"]] == sorted(d["date"] for d in body["days"])
    assert body["days"][-1]["date"] == response.headers["X-stocgain-As-Of"]
    assert all(d["date"] > body["days"][-1]["date"] for d in body["forecast"])
    db_tx.execute(
        sa.text(
            "DELETE FROM analytics.inventory_risk_snapshots WHERE store_id=:store AND product_id=:product"
        ),
        {"store": store, "product": product},
    )
    response = api_client.get(f"/api/v1/positions/{store}/{product}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "POSITION_NOT_FOUND"
