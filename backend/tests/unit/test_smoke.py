from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from typer.testing import CliRunner

from stocgain.api.app import create_app
from stocgain.cli import app as cli
from stocgain.settings import Settings

pytestmark = pytest.mark.unit


@pytest.fixture
def client() -> Iterator[TestClient]:
    settings = Settings(_env_file=None)
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def test_health_unavailable_database_is_explicit(client: TestClient) -> None:
    with patch("stocgain.api.routers.health.check_database", return_value=False):
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "unavailable",
        "analytics_ready": False,
        "current_run_id": None,
        "version": "1.0.0",
    }
    assert response.headers["x-request-id"]


def test_request_id_is_preserved(client: TestClient) -> None:
    response = client.get("/missing", headers={"X-Request-ID": "test-request"})
    assert response.headers["x-request-id"] == "test-request"
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "NOT_FOUND", "message": "Not Found", "details": {}}
    }


def test_cors_preflight(client: TestClient) -> None:
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_database_connection_failure_is_not_reported_as_healthy() -> None:
    from stocgain.db.engine import check_database, create_db_engine

    engine = create_db_engine(Settings(_env_file=None))
    with patch.object(
        engine,
        "connect",
        side_effect=OperationalError("SELECT 1", {}, Exception("down")),
    ):
        assert check_database(engine) is False
    engine.dispose()


def test_settings_parse_comma_separated_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "API_CORS_ORIGINS", "http://localhost:3000, http://localhost:3001"
    )
    assert Settings(_env_file=None).cors_origins == [
        "http://localhost:3000",
        "http://localhost:3001",
    ]


@pytest.mark.parametrize("group", ["pipeline"])
def test_unimplemented_commands_do_not_succeed(group: str) -> None:
    result = CliRunner().invoke(cli, [group])
    assert result.exit_code == 2
    assert "not implemented" in result.output.lower()


def test_internal_errors_are_generic_and_have_request_ids() -> None:
    application = create_app(Settings(_env_file=None))

    @application.get("/test-error")
    def fail() -> None:
        raise RuntimeError("secret credential must not escape")

    with TestClient(application, raise_server_exceptions=False) as test_client:
        response = test_client.get(
            "/test-error", headers={"Origin": "http://localhost:3000"}
        )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "secret" not in response.text
    assert response.headers["x-request-id"]
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_validation_errors_use_the_envelope() -> None:
    application = create_app(Settings(_env_file=None))

    @application.get("/test-validation")
    def validate(value: int) -> int:
        return value

    with TestClient(application) as test_client:
        response = test_client.get("/test-validation?value=wrong")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("group", ["data", "db", "analytics"])
def test_implemented_command_groups_show_help(group: str) -> None:
    result = CliRunner().invoke(cli, [group, "--help"])
    assert result.exit_code == 0
    assert "Commands" in result.output
