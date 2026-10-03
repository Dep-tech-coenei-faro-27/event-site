from sqlalchemy import select

from app.core.security import verify_password
from app.domains.users.models import Role, User

REGISTER_URL = "/api/auth/register"
ME_URL = "/api/auth/me"
LOGIN_URL = "/api/auth/login"


def test_register_creates_user(auth_client):
    response = auth_client.post(
        REGISTER_URL,
        json={
            "name": "Ana Silva",
            "email": "ana@example.com",
            "password": "Password123!",
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
            "password": "S3cret-pass!",
        },
    )

    assert response.status_code == 201

    user = db_session.scalar(select(User).where(User.email == "joao@example.com"))
    assert user is not None
    assert user.password_hash.startswith("$2b$")
    assert user.password_hash != "S3cret-pass!"
    assert verify_password("S3cret-pass!", user.password_hash)


def test_register_duplicate_email_returns_409(auth_client, db_session):
    payload = {
        "name": "Duplicado",
        "email": "dupe@example.com",
        "password": "Password123!",
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
            "password": "Password123!",
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
            "password": "Password123!",
        },
    )

    assert response.status_code == 422


def test_register_short_password_returns_422(auth_client):
    response = auth_client.post(
        REGISTER_URL,
        json={
            "name": "Ana",
            "email": "ana2@example.com",
            "password": "@Short1",
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


def test_private_route_missing_cookie_returns_401(auth_client):
    response = auth_client.get(ME_URL)

    assert response.status_code == 401


def test_private_route_invalid_token_returns_401(auth_client):
    auth_client.cookies.set("access_token", "invalid.jwt.token")

    response = auth_client.get(ME_URL)

    assert response.status_code == 401


def test_login_success(auth_client):
    register_response = auth_client.post(
        REGISTER_URL,
        json={
            "name": "Joao",
            "email": "joao123@example.com",
            "password": "Password456!",
        },
    )

    assert register_response.status_code == 201

    response = auth_client.post(
        LOGIN_URL,
        json={
            "email": "joao123@example.com",
            "password": "Password456!",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Login successful"}

    set_cookie = response.headers["set-cookie"]

    assert "access_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=lax" in set_cookie


def test_login_wrong_password(auth_client):
    auth_client.post(
        REGISTER_URL,
        json={
            "name": "John Doe",
            "email": "johnny@example.com",
            "password": "Correct-password1!",
        },
    )

    response = auth_client.post(
        LOGIN_URL,
        json={
            "email": "johnny@example.com",
            "password": "Wrong-password1!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_nonexistent_user(auth_client):
    response = auth_client.post(
        LOGIN_URL,
        json={
            "email": "does-not-exist@example.com",
            "password": "Pass123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_register_missing_uppercase_returns_422(auth_client):
    response = auth_client.post(
        REGISTER_URL,
        json={
            "name": "Mock",
            "email": "mock_upper@example.com",
            "password": "password123!",
        },
    )
    assert response.status_code == 422
    assert "uppercase" in response.json()["detail"][0]["msg"]


def test_register_missing_number_returns_422(auth_client):
    response = auth_client.post(
        REGISTER_URL,
        json={
            "name": "Mock",
            "email": "mock_upper@example.com",
            "password": "Password!!!",
        },
    )
    assert response.status_code == 422
    assert "digit" in response.json()["detail"][0]["msg"]


def test_register_missing_symbol_returns_422(auth_client):
    response = auth_client.post(
        REGISTER_URL,
        json={
            "name": "Mock",
            "email": "mock_upper@example.com",
            "password": "Password123",
        },
    )
    assert response.status_code == 422
    assert "symbol" in response.json()["detail"][0]["msg"]
def test_login_remember_me_success(auth_client):
    auth_client.post(
        REGISTER_URL,
        json={
            "name": "Remember",
            "email": "remember@example.com",
            "password": "Password123!",
        },
    )

    response = auth_client.post(
        LOGIN_URL,
        json={
            "email": "remember@example.com",
            "password": "Password123!",
            "remember_me": True,
        },
    )

    assert response.status_code == 200
    set_cookie = response.headers.get("Set-Cookie")
    assert "access_token" in set_cookie
    assert "Max-Age=604800" in set_cookie
