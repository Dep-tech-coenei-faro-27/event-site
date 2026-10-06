from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings
from app.core.security import ACCESS_COOKIE_NAME
from tests.helpers import LOGIN_URL, ME_URL, register_and_verify

LOGOUT_URL = "/api/auth/logout"


def register_and_login(
    auth_client, email_sender, email="user@example.com", password="Password123!"
):
    register_and_verify(
        auth_client, email_sender, name="Test User", email=email, password=password
    )
    auth_client.post(
        LOGIN_URL,
        json={"email": email, "password": password},
    )


def test_logout_clears_access_token_cookie(auth_client, email_sender):
    register_and_login(auth_client, email_sender)

    response = auth_client.post(LOGOUT_URL)

    assert response.status_code == 200
    assert response.json() == {"message": "Logout successful"}

    set_cookie = response.headers["set-cookie"]
    assert "access_token=" in set_cookie
    assert "Max-Age=0" in set_cookie


def test_logout_removes_cookie_from_client(auth_client, email_sender):
    register_and_login(auth_client, email_sender)
    assert auth_client.cookies.get(ACCESS_COOKIE_NAME) is not None

    response = auth_client.post(LOGOUT_URL)

    assert response.status_code == 200
    assert auth_client.cookies.get(ACCESS_COOKIE_NAME) is None


def test_protected_route_blocked_after_logout(auth_client, email_sender):
    register_and_login(auth_client, email_sender)

    protected_before = auth_client.get(ME_URL)
    assert protected_before.status_code == 200

    logout_response = auth_client.post(LOGOUT_URL)
    assert logout_response.status_code == 200

    protected_after = auth_client.get(ME_URL)
    assert protected_after.status_code == 401


def test_logout_without_login_is_idempotent(auth_client):
    first = auth_client.post(LOGOUT_URL)
    second = auth_client.post(LOGOUT_URL)

    assert first.status_code == 200
    assert second.status_code == 200


def test_logout_with_invalid_token_clears_cookie(auth_client):
    auth_client.cookies.set(
        ACCESS_COOKIE_NAME, "invalid.jwt.token", domain="testserver"
    )

    response = auth_client.post(LOGOUT_URL)

    assert response.status_code == 200

    set_cookie = response.headers["set-cookie"]
    assert "access_token=" in set_cookie
    assert "Max-Age=0" in set_cookie


def test_logout_with_expired_token_clears_cookie(auth_client):
    expired_token = jwt.encode(
        {
            "sub": "expired@example.com",
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "exp": datetime.now(UTC) - timedelta(minutes=10),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    auth_client.cookies.set(ACCESS_COOKIE_NAME, expired_token, domain="testserver")

    response = auth_client.post(LOGOUT_URL)

    assert response.status_code == 200

    set_cookie = response.headers["set-cookie"]
    assert "access_token=" in set_cookie
    assert "Max-Age=0" in set_cookie


def test_logout_sets_session_clearing_attributes(auth_client, email_sender):
    register_and_login(auth_client, email_sender)

    response = auth_client.post(LOGOUT_URL)

    set_cookie = response.headers["set-cookie"]
    assert "access_token=" in set_cookie
    assert "Max-Age=0" in set_cookie
    assert "Path=/" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=lax" in set_cookie


def test_login_after_logout_creates_working_session(auth_client, email_sender):
    register_and_login(auth_client, email_sender)
    auth_client.post(LOGOUT_URL)

    login_response = auth_client.post(
        LOGIN_URL,
        json={"email": "user@example.com", "password": "Password123!"},
    )
    assert login_response.status_code == 200

    me_response = auth_client.get(ME_URL)
    assert me_response.status_code == 200
