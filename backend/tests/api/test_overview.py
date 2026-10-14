"""Overview HTTP contracts checked against actual PostgreSQL model output."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.api


def test_summary_and_distribution(api_client, db_tx, actual_model_run):
    response = api_client.get("/api/v1/overview/summary")
    assert response.status_code == 200, response.text
    data = response.json()
    expected = (
        db_tx.execute(
            text("""SELECT count(*) AS positions,
        count(*) FILTER(WHERE risk_tier IN ('critical','high')) AS at_risk,
        coalesce(sum(margin_at_risk_usd),0) AS margin
        FROM analytics.inventory_risk_snapshots WHERE run_id=:run"""),
            {"run": actual_model_run},
        )
        .mappings()
        .one()
    )
    assert data["active_positions"] == expected["positions"]
    assert data["at_risk_positions"] == expected["at_risk"]
    assert data["gross_margin_at_risk_usd"] == float(expected["margin"])
    assert data["prior_at_risk_positions"] is None
    assert data["at_risk_positions_change"] is None
    assert response.headers["X-stocgain-Run-Id"] == str(actual_model_run)
    distribution = api_client.get("/api/v1/overview/risk-distribution").json()
    assert [r["risk_tier"] for r in distribution["tiers"]] == [
        "critical",
        "high",
        "moderate",
        "low",
    ]
    assert (
        sum(r["positions"] for r in distribution["tiers"]) == data["active_positions"]
    )
    assert sum(r["margin_at_risk_usd"] for r in distribution["tiers"]) == pytest.approx(
        data["gross_margin_at_risk_usd"]
    )


@pytest.mark.parametrize(
    "filters",
    [
        {"store_id": 1},
        {"region_id": 1},
        {"category_id": 1},
        {"store_id": 1, "category_id": 1},
        [("store_id", 1), ("store_id", 7)],
    ],
)
def test_overview_filter_consistency(api_client, filters):
    summary = api_client.get("/api/v1/overview/summary", params=filters)
    risk = api_client.get("/api/v1/risk/positions", params=filters)
    assert summary.status_code == risk.status_code == 200
    assert summary.json()["active_positions"] == risk.json()["total_items"]
    assert (
        summary.json()["gross_margin_at_risk_usd"]
        == risk.json()["summary"]["margin_at_risk_usd"]
    )


def test_empty_scope_and_unknown_id(api_client, db_tx):
    store = (
        db_tx.execute(
            text("SELECT store_id,region_id FROM ops.stores ORDER BY store_id LIMIT 1")
        )
        .mappings()
        .one()
    )
    other_region = db_tx.scalar(
        text("SELECT region_id FROM ops.regions WHERE region_id<>:id LIMIT 1"),
        {"id": store["region_id"]},
    )
    params = {"store_id": store["store_id"], "region_id": other_region}
    summary = api_client.get("/api/v1/overview/summary", params=params).json()
    assert summary["active_positions"] == summary["gross_margin_at_risk_usd"] == 0
    tiers = api_client.get("/api/v1/overview/risk-distribution", params=params).json()[
        "tiers"
    ]
    assert len(tiers) == 4 and all(r["positions"] == 0 for r in tiers)
    response = api_client.get("/api/v1/overview/summary?store_id=99999")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNKNOWN_FILTER_VALUE"


def test_trend_heatmap_stores_and_top_products(api_client, db_tx):
    response = api_client.get("/api/v1/overview/risk-trend")
    assert response.status_code == 200, response.text
    points = response.json()["points"]
    assert points and len({r["as_of_date"] for r in points}) == len(points)
    assert [r["as_of_date"] for r in points] == sorted(r["as_of_date"] for r in points)
    response = api_client.get("/api/v1/overview/category-heatmap")
    assert response.status_code == 200, response.text
    grid = response.json()
    assert len(grid["cells"]) == len(grid["stores"]) * len(grid["categories"])
    assert len({(r["store_id"], r["category_id"]) for r in grid["cells"]}) == len(
        grid["cells"]
    )
    unfiltered = api_client.get("/api/v1/overview/store-comparison")
    filtered = api_client.get("/api/v1/overview/store-comparison?store_id=1")
    assert unfiltered.status_code == filtered.status_code == 200
    assert unfiltered.json() == filtered.json()
    stores = unfiltered.json()["stores"]
    assert [s["margin_at_risk_usd"] for s in stores] == sorted(
        (s["margin_at_risk_usd"] for s in stores), reverse=True
    )
    response = api_client.get("/api/v1/overview/top-products?limit=3")
    assert response.status_code == 200, response.text
    products = response.json()["items"]
    assert len(products) <= 3
    assert all(p["at_risk_stores"] >= 1 for p in products)
    assert [
        (-p["margin_at_risk_usd"], -p["at_risk_stores"]) for p in products
    ] == sorted((-p["margin_at_risk_usd"], -p["at_risk_stores"]) for p in products)


def test_recommendations_order_filter_and_bounds(api_client):
    response = api_client.get("/api/v1/recommendations?limit=100")
    assert response.status_code == 200, response.text
    rows = response.json()["items"]
    assert rows and [r["priority_rank"] for r in rows] == sorted(
        r["priority_rank"] for r in rows
    )
    response = api_client.get("/api/v1/recommendations?action_type=reorder&limit=100")
    assert response.status_code == 200, response.text
    assert all(r["action_type"] == "reorder" for r in response.json()["items"])
    by_key = {(r["store_id"], r["product_id"]): r for r in rows}
    for row in response.json()["items"]:
        if (row["store_id"], row["product_id"]) in by_key:
            assert (
                row["priority_rank"]
                == by_key[row["store_id"], row["product_id"]]["priority_rank"]
            )
    for path in (
        "/recommendations?limit=0",
        "/recommendations?limit=101",
        "/recommendations?action_type=no_action",
        "/overview/risk-trend?weeks=27",
        "/overview/top-products?limit=51",
    ):
        assert api_client.get("/api/v1" + path).status_code == 422
