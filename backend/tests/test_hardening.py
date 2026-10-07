import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.main import create_app

REGISTER_URL = "/api/auth/register"


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_docs_are_available_in_dev(monkeypatch, path):
    monkeypatch.setattr(settings, "ENVIRONMENT", "dev")

    assert TestClient(create_app()).get(path).status_code == 200


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_docs_are_not_served_in_prod(monkeypatch, path):
    monkeypatch.setattr(settings, "ENVIRONMENT", "prod")

    assert TestClient(create_app()).get(path).status_code == 404


def test_environment_defaults_to_prod(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    with pytest.raises(ValueError, match="ENVIRONMENT=prod"):
        Settings(
            _env_file=None,
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="password",
            POSTGRES_DB="db",
            POSTGRES_HOST="localhost",
            POSTGRES_PORT=5432,
            JWT_SECRET_KEY="k" * 40,
        )


def test_prod_rejects_the_example_database_password():
    with pytest.raises(ValueError, match="POSTGRES_PASSWORD"):
        Settings(
            _env_file=None,
            ENVIRONMENT="prod",
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="postgres",
            POSTGRES_DB="db",
            POSTGRES_HOST="localhost",
            POSTGRES_PORT=5432,
            JWT_SECRET_KEY="p" * 48,
            SMTP_HOST="smtp.example.com",
            EMAIL_SENDER="noreply@example.com",
            FRONTEND_URL="https://app.example.com",
            CORS_ALLOW_ORIGINS=["https://app.example.com"],
        )


def test_a_body_over_the_limit_is_refused_with_413(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "MAX_REQUEST_BYTES", 200)

    response = auth_client.post(
        REGISTER_URL,
        json={
            "name": "A" * 500,
            "email": "ana@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "Request body too large"}


def test_the_413_carries_the_cors_and_security_headers(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "MAX_REQUEST_BYTES", 200)

    response = auth_client.post(
        REGISTER_URL,
        json={
            "name": "A" * 500,
            "email": "ana@example.com",
            "password": "Password123!",
        },
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_a_chunked_body_over_the_limit_is_refused_too(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "MAX_REQUEST_BYTES", 200)

    def chunks():
        for _ in range(10):
            yield b"x" * 100

    response = auth_client.post(
        REGISTER_URL, content=chunks(), headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 413


def test_a_normal_request_is_not_affected_by_the_limit(auth_client):
    response = auth_client.post(
        REGISTER_URL,
        json={
            "name": "Ana Silva",
            "email": "ana@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code == 201
