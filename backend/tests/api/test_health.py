import pytest
from fastapi.testclient import TestClient

from stocgain.api.app import create_app
from stocgain.settings import Settings

pytestmark = pytest.mark.api


def test_health_against_real_postgres() -> None:
    settings = Settings()
    settings = settings.model_copy(update={"database_url": settings.test_database_url})
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["database"] == "ok", "Start PostgreSQL with make db-up"
