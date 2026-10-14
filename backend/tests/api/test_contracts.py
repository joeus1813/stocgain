"""OpenAPI metadata, explicit database errors and run-keyed cache contracts."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from stocgain.api.app import create_app

pytestmark = pytest.mark.api


def test_response_models_have_documented_numeric_units():
    app = create_app()
    schema = app.openapi()
    for route in app.routes:
        if getattr(route, "path", "").startswith("/api/v1"):
            assert route.response_model is not None
    for name, model in schema["components"]["schemas"].items():
        if name in ("HTTPValidationError", "ValidationError"):
            continue
        for field, spec in model.get("properties", {}).items():
            assert spec.get("description"), (name, field)
            if spec.get("type") in ("integer", "number"):
                assert "x-unit" in spec, (name, field)


def test_database_error_envelope():
    with TestClient(create_app()) as client:
        with patch.object(
            client.app.state.engine,
            "connect",
            side_effect=OperationalError("connect", {}, Exception("secret")),
        ):
            response = client.get("/api/v1/meta")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
        assert "secret" not in response.text


def test_run_cache_changes_with_run_identity(api_client, db_tx, actual_model_run):
    original = api_client.post(
        "/api/v1/scenarios/evaluate", json={"scope": {"store_ids": []}}
    )
    assert original.status_code == 200, original.text
    from stocgain.db.models import Base

    table = Base.metadata.tables["analytics.analytics_runs"]
    values = dict(
        db_tx.execute(table.select().where(table.c.run_id == actual_model_run))
        .mappings()
        .one()
    )
    values.pop("run_id")
    values["completed_at"] = db_tx.scalar(text("SELECT now()+interval '1 minute'"))
    values["config"] = {**values["config"], "service_level": 0.98}
    new_id = db_tx.execute(
        table.insert().values(**values).returning(table.c.run_id)
    ).scalar_one()
    changed = api_client.post(
        "/api/v1/scenarios/evaluate", json={"scope": {"store_ids": []}}
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["run_id"] == new_id
    assert changed.json()["assumptions_applied"]["service_level"] == 0.98
