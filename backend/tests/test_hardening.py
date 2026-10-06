import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.main import create_app


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
