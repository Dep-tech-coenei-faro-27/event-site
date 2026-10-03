from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select

from app.core.config import settings
from app.core.security import (
    create_access_token,
    verify_password,
)
from app.domains.auth.dependencies import EMAIL_VERIFICATION_REQUIRED_MESSAGE
from app.domains.users.models import Role, User
from tests.helpers import (
    LOGIN_URL,
    ME_URL,
    REGISTER_URL,
    VERIFY_URL,
    extract_verification_token,
    register_and_verify,
    register_user,
)

FORGOT_PASSWORD_URL = "/api/auth/forgot-password"


def _access_token_for(email: str) -> str:
    return jwt.encode(
        {
            "sub": email,
            "role": Role.USER.value,
            "type": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


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
    assert body["is_verified"] is False
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


def test_me_requires_verified_account(auth_client, email_sender, db_session):
    register_user(auth_client, email_sender, email="pending@example.com")
    auth_client.cookies.set("access_token", _access_token_for("pending@example.com"))

    response = auth_client.get(ME_URL)
    assert response.status_code == 403
    assert response.json()["detail"] == EMAIL_VERIFICATION_REQUIRED_MESSAGE

    user = db_session.scalar(select(User).where(User.email == "pending@example.com"))
    assert user.is_verified is False


def test_login_success_after_verification(auth_client, email_sender):
    register_user(
        auth_client, email_sender, email="joao123@example.com", password="Password456!"
    )
    token = extract_verification_token(email_sender)
    auth_client.post(VERIFY_URL, json={"token": token})

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


def test_login_unverified_user_blocked(auth_client, email_sender, db_session):
    register_user(auth_client, email_sender, email="unverified@example.com")

    response = auth_client.post(
        LOGIN_URL,
        json={"email": "unverified@example.com", "password": "Password123!"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == EMAIL_VERIFICATION_REQUIRED_MESSAGE
    assert "set-cookie" not in response.headers

    user = db_session.scalar(select(User).where(User.email == "unverified@example.com"))
    assert user.is_verified is False


def test_login_wrong_password(auth_client, email_sender):
    register_user(
        auth_client,
        email_sender,
        email="johnny@example.com",
        password="Correct-password1!",
    )
    token = extract_verification_token(email_sender)
    auth_client.post(VERIFY_URL, json={"token": token})

    response = auth_client.post(
        LOGIN_URL,
        json={
            "email": "johnny@example.com",
            "password": "Wrong-password1!",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_wrong_password_returns_401(auth_client, email_sender):
    register_user(auth_client, email_sender, email="johnny@example.com")

    response = auth_client.post(
        LOGIN_URL,
        json={
            "email": "johnny@example.com",
            "password": "Wrong-password1!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_cookie_grants_access_to_protected_route(auth_client, email_sender):
    register_and_verify(auth_client, email_sender, email="protected@example.com")

    login_response = auth_client.post(
        LOGIN_URL,
        json={
            "email": "protected@example.com",
            "password": "Password123!",
        },
    )

    assert login_response.status_code == 200

    response = auth_client.get(ME_URL)

    assert response.status_code == 200
    assert response.json()["email"] == "protected@example.com"


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


def test_me_allows_verified_user_after_login(auth_client, email_sender, db_session):
    register_and_verify(auth_client, email_sender, email="authorized@example.com")
    login = auth_client.post(
        LOGIN_URL,
        json={"email": "authorized@example.com", "password": "Password123!"},
    )
    assert login.status_code == 200

    response = auth_client.get(ME_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "authorized@example.com"
    assert body["is_verified"] is True


def test_access_token_carries_access_type_claim():
    token = create_access_token(subject="carol@example.com", role=Role.USER.value)

    payload = jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    assert payload["type"] == "access"


def test_verification_token_cannot_be_used_as_access_token(auth_client, email_sender):
    register_user(auth_client, email_sender, email="verify-only@example.com")

    verification_token = extract_verification_token(email_sender)
    auth_client.cookies.set("access_token", verification_token)

    response = auth_client.get(ME_URL)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token."


def test_me_rejects_token_without_type_claim(auth_client, email_sender):
    register_user(auth_client, email_sender, email="no-type@example.com")

    token = jwt.encode(
        {
            "sub": "no-type@example.com",
            "role": Role.USER.value,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    auth_client.cookies.set("access_token", token)

    response = auth_client.get(ME_URL)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token."


def test_me_rejects_token_with_non_string_subject(auth_client):
    token = jwt.encode(
        {
            "sub": 12345,
            "type": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    auth_client.cookies.set("access_token", token)

    response = auth_client.get(ME_URL)

    assert response.status_code == 401
    # PyJWT rejects non-string `sub` claims at decode time (InvalidSubjectError),
    # so this surfaces through the generic invalid-token path.
    assert response.json()["detail"] == "Invalid token."


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


def test_login_remember_me_success(auth_client, email_sender):
    register_user(
        auth_client,
        email_sender,
        email="remember@example.com",
        password="Password123!",
    )
    token = extract_verification_token(email_sender)
    auth_client.post(VERIFY_URL, json={"token": token})

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


from app.core.email.templates import PASSWORD_RESET_SUBJECT


def test_forgot_password_sends_email_if_user_exists(
    auth_client, email_sender, db_session
):
    register_user(
        auth_client,
        email_sender,
        email="mock@example.com",
        password="Mock-password1!",
    )
    email_sender.sent.clear()

    response = auth_client.post(FORGOT_PASSWORD_URL, json={"email": "mock@example.com"})

    assert response.status_code == 200
    assert (
        response.json()["message"]
        == "If the email exists in our system, you will receive a password recovery link shortly."
    )
    assert len(email_sender.sent) == 1
    assert email_sender.sent[0]["to_email"] == "mock@example.com"
    assert email_sender.sent[0]["subject"] == PASSWORD_RESET_SUBJECT
    assert "reset-password?token=" in email_sender.sent[0]["html_body"]


def test_forgot_password_ignores_non_existent_user_securely(auth_client, email_sender):
    email_sender.sent.clear()

    response = auth_client.post(
        FORGOT_PASSWORD_URL, json={"email": "does-not-exist@example.com"}
    )

    assert response.status_code == 200
    assert (
        response.json()["message"]
        == "If the email exists in our system, you will receive a password recovery link shortly."
    )
    assert len(email_sender.sent) == 0
