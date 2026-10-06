import pytest
from sqlalchemy.exc import OperationalError

from app.main import app

LOGIN_URL = "/api/auth/login"
ALLOWED_ORIGIN = "http://localhost:3000"


@pytest.fixture
def failing_routes():
    async def boom():
        raise RuntimeError("boom")

    async def database_down():
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    app.add_api_route("/api/test-boom", boom)
    app.add_api_route("/api/test-database-down", database_down)
    yield
    app.router.routes = [
        route
        for route in app.router.routes
        if not getattr(route, "path", "").startswith("/api/test-")
    ]


def test_unhandled_error_returns_json_500(client, failing_routes):
    response = client.get("/api/test-boom")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
    assert "Traceback" not in response.text


def test_unhandled_error_keeps_cors_headers(client, failing_routes):
    response = client.get("/api/test-boom", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


def test_unhandled_error_has_security_headers(client, failing_routes):
    response = client.get("/api/test-boom")

    assert response.headers["x-content-type-options"] == "nosniff"


def test_database_outage_returns_503_with_cors_headers(client, failing_routes):
    response = client.get("/api/test-database-down", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 503
    assert response.json() == {"detail": "Service temporarily unavailable"}
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_validation_error_does_not_echo_the_submitted_password(client):
    response = client.post(LOGIN_URL, json={"password": "Sup3r-Secret!"})

    assert response.status_code == 422
    assert "Sup3r-Secret!" not in response.text


def test_validation_error_keeps_location_and_message(client):
    response = client.post(LOGIN_URL, json={"password": "Sup3r-Secret!"})

    error = response.json()["detail"][0]
    assert error["loc"] == ["body", "email"]
    assert error["type"] == "missing"
    assert error["msg"]
    assert set(error) == {"type", "loc", "msg"}


def test_security_headers_are_added_to_every_response(client):
    response = client.get("/api/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "cache-control" not in response.headers


def test_auth_responses_are_not_cacheable(auth_client):
    response = auth_client.post(
        LOGIN_URL, json={"email": "nobody@example.com", "password": "Passw0rd!x"}
    )

    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"


def test_database_errors_do_not_expose_the_values_that_were_sent():
    from app.db.session import engine

    assert engine.hide_parameters is True
