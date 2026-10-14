"""Real PostgreSQL supplier/evaluation contracts required by frontend slices."""

import pytest

pytestmark = pytest.mark.api


def test_supplier_list_matches_view(api_client, db_tx):
    from sqlalchemy import text

    response = api_client.get("/api/v1/suppliers")
    assert response.status_code == 200
    items = response.json()["items"]
    expected = {
        r["supplier_id"]: dict(r)
        for r in db_tx.execute(
            text("SELECT * FROM analytics.v_supplier_performance")
        ).mappings()
    }
    assert len(items) == len(expected)
    for row in items:
        original = expected[row["supplier_id"]]
        for field in (
            "on_time_rate",
            "in_full_rate",
            "margin_at_risk_usd",
            "at_risk_positions",
        ):
            assert row[field] == (
                float(original[field]) if original[field] is not None else None
            )
    detail = api_client.get(f"/api/v1/suppliers/{items[0]['supplier_id']}")
    assert detail.status_code == 200
    assert detail.json()["supplier"]["supplier_id"] == items[0]["supplier_id"]
    assert api_client.get("/api/v1/suppliers/999999").status_code == 404
    assert api_client.get("/api/v1/suppliers?store_id=999999").status_code == 422


def test_supplier_scope_and_evaluation(api_client):
    summary = api_client.get("/api/v1/suppliers/summary?store_id=1").json()
    rows = api_client.get("/api/v1/suppliers?store_id=1").json()["items"]
    assert summary["suppliers"] == len(rows)
    assert summary["overdue_open_pos"] == sum(r["overdue_open_pos"] for r in rows)
    assert (
        api_client.get("/api/v1/forecasts/evaluation?segment_type=overall").status_code
        == 200
    )
    assert (
        api_client.get("/api/v1/forecasts/evaluation?segment_type=bogus").status_code
        == 422
    )


def test_export_equals_scoped_rows_and_sensitivity_baseline(api_client):
    import csv
    import io

    rows = api_client.get("/api/v1/risk/positions?store_id=1&page_size=200").json()
    response = api_client.get("/api/v1/risk/positions/export.csv?store_id=1")
    assert response.status_code == 200
    lines = response.text.splitlines()
    assert lines[0].startswith("# stocgain simulated dataset · run ")
    exported = list(csv.DictReader(io.StringIO("\n".join(lines[1:]))))
    assert len(exported) == rows["total_items"]
    assert [int(r["product_id"]) for r in exported] == [
        r["product_id"] for r in rows["items"]
    ]
    first = rows["items"][0]
    sensitivity = api_client.get(
        f"/api/v1/positions/{first['store_id']}/{first['product_id']}/sensitivity"
    )
    assert sensitivity.status_code == 200
    assert len(sensitivity.json()["scenarios"]) == 4
    assert sensitivity.json()["baseline_probability"] == pytest.approx(
        first["stockout_probability"], abs=1e-4
    )


def test_supplier_future_receipts_cannot_change_historical_metrics(api_client, db_tx):
    from sqlalchemy import text

    baseline = api_client.get("/api/v1/suppliers").json()
    supplier = baseline["items"][0]["supplier_id"]
    detail = api_client.get(f"/api/v1/suppliers/{supplier}").json()
    db_tx.execute(
        text("""INSERT INTO ops.inventory_receipts (receipt_id,po_line_id,received_date,quantity_received)
      SELECT (SELECT MAX(receipt_id)+1 FROM ops.inventory_receipts),pol.po_line_id,
        (SELECT as_of_date+1 FROM analytics.v_current_run),1
      FROM ops.purchase_order_lines pol JOIN ops.purchase_orders po USING(purchase_order_id)
      WHERE po.supplier_id=:supplier ORDER BY pol.po_line_id LIMIT 1"""),
        {"supplier": supplier},
    )
    assert api_client.get("/api/v1/suppliers").json() == baseline
    assert api_client.get(f"/api/v1/suppliers/{supplier}").json() == detail


def test_detail_explanation_uses_shared_probability_format(api_client):
    from stocgain.analytics.formatting import format_number

    row = api_client.get(
        "/api/v1/risk/positions?sort_by=stockout_probability&sort_dir=desc&page_size=1"
    ).json()["items"][0]
    detail = api_client.get(
        f"/api/v1/positions/{row['store_id']}/{row['product_id']}"
    ).json()
    probability = detail["risk"]["stockout_probability"]
    assert (
        f"replenishment: {format_number('probability', probability)}"
        in detail["risk"]["explanation"]
    )
