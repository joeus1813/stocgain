"""Risk list filtering, pagination and stable sorting against actual model rows."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.api
SORTS = [
    "priority",
    "product_name",
    "store_code",
    "category_name",
    "on_hand_units",
    "avg_daily_demand_units",
    "days_of_cover",
    "next_receipt_date",
    "stockout_probability",
    "risk_tier",
    "margin_at_risk_usd",
]


def test_pagination_totals_and_summary(api_client, db_tx, actual_model_run):
    response = api_client.get("/api/v1/risk/positions?page_size=7")
    assert response.status_code == 200, response.text
    first = response.json()
    total = db_tx.scalar(
        text(
            "SELECT count(*) FROM analytics.inventory_risk_snapshots WHERE run_id=:run"
        ),
        {"run": actual_model_run},
    )
    assert first["total_items"] == first["summary"]["positions"] == total
    assert first["total_pages"] == (total + 6) // 7
    second = api_client.get("/api/v1/risk/positions?page_size=7&page=2").json()
    assert not (
        {(r["store_id"], r["product_id"]) for r in first["items"]}
        & {(r["store_id"], r["product_id"]) for r in second["items"]}
    )
    beyond = api_client.get("/api/v1/risk/positions?page_size=7&page=99999").json()
    assert beyond["items"] == []
    assert beyond["summary"] == first["summary"]
    assert beyond["total_items"] == total


@pytest.mark.parametrize("sort", SORTS)
def test_each_sort_both_directions_stable(api_client, db_tx, actual_model_run, sort):
    raw_demand = {
        (r.store_id, r.product_id): r.avg_daily_demand_units
        for r in db_tx.execute(
            text(
                "SELECT store_id,product_id,avg_daily_demand_units FROM analytics.inventory_risk_snapshots WHERE run_id=:run"
            ),
            {"run": actual_model_run},
        )
    }
    for direction in ("asc", "desc"):
        params = {"sort_by": sort, "sort_dir": direction, "page_size": 200}
        response = api_client.get("/api/v1/risk/positions", params=params)
        assert response.status_code == 200, response.text
        rows = response.json()["items"]
        assert (
            rows
            == api_client.get("/api/v1/risk/positions", params=params).json()["items"]
        )
        key = "priority_rank" if sort == "priority" else sort
        values = [r[key] for r in rows if r[key] is not None]
        if sort == "risk_tier":
            values = [
                {"critical": 4, "high": 3, "moderate": 2, "low": 1}[v] for v in values
            ]
        assert values == sorted(values, reverse=direction == "desc")
        if sort != "priority":
            for left, right in zip(rows, rows[1:], strict=False):
                # Sorting uses stored precision; response demand is rounded to 2 decimals.
                left_value = (
                    raw_demand[left["store_id"], left["product_id"]]
                    if key == "avg_daily_demand_units"
                    else left[key]
                )
                right_value = (
                    raw_demand[right["store_id"], right["product_id"]]
                    if key == "avg_daily_demand_units"
                    else right[key]
                )
                if left_value == right_value:
                    assert (left["store_id"], left["product_id"]) < (
                        right["store_id"],
                        right["product_id"],
                    )


@pytest.mark.parametrize(
    "params",
    [
        {"page_size": 0},
        {"page_size": 201},
        {"page": 0},
        {"sort_by": "drop table"},
        {"sort_dir": "other"},
        {"q": ""},
        {"q": "x" * 65},
        {"risk_tier": "unknown"},
        {"action_type": "unknown"},
    ],
)
def test_invalid_parameters(api_client, params):
    response = api_client.get("/api/v1/risk/positions", params=params)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_filters_search_and_empty(api_client, db_tx, actual_model_run):
    base = api_client.get("/api/v1/risk/positions?page_size=200").json()["items"]
    row = base[0]
    params = {
        "store_id": row["store_id"],
        "category_id": row["category_id"],
        "risk_tier": row["risk_tier"],
        "action_type": row["action_type"],
        "q": row["sku"].lower(),
        "below_reorder_point": str(row["below_reorder_point"]).lower(),
    }
    response = api_client.get("/api/v1/risk/positions", params=params)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["total_items"] == 1
    assert result["items"][0] == row
    empty = api_client.get(
        "/api/v1/risk/positions?q=nonexistent-literal-product"
    ).json()
    assert empty["items"] == [] and empty["total_items"] == empty["total_pages"] == 0
    assert empty["summary"]["margin_at_risk_usd"] == 0
    # Percent and underscore are literal search characters, never wildcard scope.
    assert api_client.get("/api/v1/risk/positions?q=%25_%25").json()["total_items"] == 0
    filtered = api_client.get(
        "/api/v1/risk/positions",
        params={"store_id": row["store_id"], "supplier_id": row["supplier_id"]},
    ).json()
    expected = db_tx.scalar(
        text(
            "SELECT count(*) FROM analytics.inventory_risk_snapshots WHERE run_id=:run AND store_id=:store AND supplier_id=:supplier"
        ),
        {
            "run": actual_model_run,
            "store": row["store_id"],
            "supplier": row["supplier_id"],
        },
    )
    assert filtered["total_items"] == expected
