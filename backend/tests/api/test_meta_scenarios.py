"""Actual-database metadata and stateless scenario HTTP contracts."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.api


def test_metadata_and_dimensions(api_client, actual_model_run):
    response = api_client.get("/api/v1/meta")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["dataset"]["counts"]["stores"] == 3
    assert data["dataset"]["row_counts"]["daily_sales"] == 21600
    assert data["run"]["run_id"] == actual_model_run
    filters = api_client.get("/api/v1/filters").json()
    assert len(filters["stores"]) == 3
    assert filters["categories"] == sorted(
        filters["categories"], key=lambda r: r["category_code"]
    )


def test_scenario_neutral_and_service_policy(api_client, actual_model_run, db_tx):
    before = db_tx.scalar(text("SELECT count(*) FROM analytics.analytics_runs"))
    baseline = api_client.post("/api/v1/scenarios/evaluate", json={})
    assert baseline.status_code == 200, baseline.text
    data = baseline.json()
    assert data["run_id"] == actual_model_run
    assert data["baseline"] == data["scenario"]
    assert all(value == 0 for value in data["delta"]["absolute"].values())
    assert data["positions_in_scope"] == 180
    assert sum(map(sum, data["tier_transitions"]["matrix"])) == 180
    raised = api_client.post(
        "/api/v1/scenarios/evaluate", json={"assumptions": {"service_level": 0.98}}
    )
    assert raised.status_code == 200, raised.text
    result = raised.json()
    assert result["delta"]["absolute"]["margin_at_risk_usd"] == 0
    assert result["delta"]["absolute"]["safety_stock_value_usd"] > 0
    assert result["delta"]["absolute"]["annual_expected_shortfall_margin_usd"] < 0
    assert db_tx.scalar(text("SELECT count(*) FROM analytics.analytics_runs")) == before


@pytest.mark.parametrize(
    "payload",
    [
        {"assumptions": {"lead_time_change_days": 1.5}},
        {"assumptions": {"lead_time_change_days": 15}},
        {"assumptions": {"service_level": 1.0}},
        {"assumptions": {"demand_change_rate": -0.6}},
        {"assumptions": {"safety_stock_buffer_rate": 2}},
        {"extra": 1},
    ],
)
def test_scenario_invalid(api_client, payload):
    response = api_client.post("/api/v1/scenarios/evaluate", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"]["errors"]


def test_scenario_scope(api_client):
    unknown = api_client.post(
        "/api/v1/scenarios/evaluate", json={"scope": {"supplier_ids": [99999]}}
    )
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "UNKNOWN_FILTER_VALUE"
    empty = api_client.post(
        "/api/v1/scenarios/evaluate", json={"scope": {"store_ids": []}}
    )
    assert empty.status_code == 200, empty.text
    assert empty.json()["positions_in_scope"] == 0
    assert empty.json()["top_changes"] == []
    scoped = api_client.post(
        "/api/v1/scenarios/evaluate", json={"scope": {"store_ids": [1]}}
    )
    assert scoped.status_code == 200, scoped.text
    assert scoped.json()["positions_in_scope"] == 60


def test_no_run_metadata_and_error(db_tx):
    from fastapi.testclient import TestClient

    from stocgain.api.app import create_app
    from stocgain.api.dependencies import get_connection

    app = create_app()
    app.dependency_overrides[get_connection] = lambda: db_tx
    with TestClient(app) as client:
        response = client.get("/api/v1/meta")
        assert response.status_code == 200, response.text
        assert response.json()["run"] is None
        response = client.post("/api/v1/scenarios/evaluate", json={})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "ANALYTICS_NOT_READY"
