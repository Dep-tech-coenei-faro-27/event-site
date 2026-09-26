from sqlalchemy import select

from app.core.security import verify_password
from app.domains.users.models import Role, User

REGISTER_URL = "/api/auth/register"


def test_register_creates_user(auth_client):
    response = auth_client.post(
        REGISTER_URL,
        json={
            "name": "Ana Silva",
            "email": "ana@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ana Silva"
    assert body["email"] == "ana@example.com"
    assert body["role"] == Role.USER.value
    assert "password" not in body
    assert "password_hash" not in body


def test_register_stores_bcrypt_hash_in_db(auth_client, db_session):
    response = auth_client.post(
        REGISTER_URL,
        json={
            "name": "João Mendes",
            "email": "joao@example.com",
            "password": "s3cret-pass!",
        },
    )

    assert response.status_code == 201

    user = db_session.scalar(select(User).where(User.email == "joao@example.com"))
    assert user is not None
    assert user.password_hash.startswith("$2b$")
    assert user.password_hash != "s3cret-pass!"
    assert verify_password("s3cret-pass!", user.password_hash)


def test_register_duplicate_email_returns_409(auth_client, db_session):
    payload = {
        "name": "Duplicado",
        "email": "dupe@example.com",
        "password": "password123",
    }
    first = auth_client.post(REGISTER_URL, json=payload)
    assert first.status_code == 201

    second = auth_client.post(REGISTER_URL, json=payload)
    assert second.status_code == 409

    users = db_session.scalars(
        select(User).where(User.email == "dupe@example.com")
    ).all()
    assert len(users) == 1


def test_register_normalizes_email(auth_client, db_session):
    response = auth_client.post(
        REGISTER_URL,
        json={
            "name": "Case",
            "email": "  MixedCASE@Example.COM ",
            "password": "password123",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "mixedcase@example.com"

    user = db_session.scalar(select(User).where(User.email == "mixedcase@example.com"))
    assert user is not None


def test_register_invalid_email_returns_422(auth_client):
    response = auth_client.post(
        REGISTER_URL,
        json={
            "name": "Ana",
            "email": "not-an-email",
            "password": "password123",
        },
    )

    assert response.status_code == 422


def test_register_short_password_returns_422(auth_client):
    response = auth_client.post(
        REGISTER_URL,
        json={
            "name": "Ana",
            "email": "ana2@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 422


def test_register_overlong_password_returns_422(auth_client):
    response = auth_client.post(
        REGISTER_URL,
        json={
            "name": "Ana",
            "email": "ana3@example.com",
            "password": "x" * 100,
        },
    )

    assert response.status_code == 422
