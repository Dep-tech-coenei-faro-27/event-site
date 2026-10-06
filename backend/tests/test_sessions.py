from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import ACCESS_COOKIE_NAME
from app.domains.auth.models import RevokedToken
from app.domains.users.cleanup import delete_expired_revoked_tokens
from app.domains.users.models import User
from app.main import app
from tests.helpers import (
    LOGIN_URL,
    ME_URL,
    TOKEN_QUERY,
    access_claims,
    encode_claims,
    register_and_verify,
    user_id_of,
)
from tests.test_auth import FORGOT_PASSWORD_URL
from tests.test_password import CHANGE_PASSWORD_URL, RESET_PASSWORD_URL

LOGOUT_URL = "/api/auth/logout"
EMAIL = "ana@example.com"
PASSWORD = "Password123!"


def login(client, remember_me=False):
    return client.post(
        LOGIN_URL,
        json={"email": EMAIL, "password": PASSWORD, "remember_me": remember_me},
    )


def claims_of(client):
    return jwt.decode(
        client.cookies.get(ACCESS_COOKIE_NAME),
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


def second_client():
    return TestClient(app, base_url="https://testserver")


def test_the_token_identifies_the_user_by_id_and_carries_a_version_and_an_id(
    auth_client, email_sender, db_session
):
    register_and_verify(auth_client, email_sender)

    login(auth_client)

    claims = claims_of(auth_client)
    assert claims["sub"] == str(user_id_of(db_session))
    assert claims["tv"] == 0
    assert len(claims["jti"]) == 36
    assert claims["type"] == "access"
    assert EMAIL not in str(claims)
    assert "role" not in claims


def test_every_login_gets_its_own_token_id(auth_client, email_sender):
    register_and_verify(auth_client, email_sender)

    login(auth_client)
    first = claims_of(auth_client)["jti"]
    login(auth_client)

    assert claims_of(auth_client)["jti"] != first


def test_the_session_cookie_is_a_host_cookie(auth_client, email_sender):
    register_and_verify(auth_client, email_sender)

    set_cookie = login(auth_client).headers["set-cookie"]

    assert set_cookie.startswith("__Host-access_token=")
    assert "Secure" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Path=/" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Domain" not in set_cookie


def test_a_token_that_uses_the_email_as_subject_is_refused(auth_client, email_sender):
    register_and_verify(auth_client, email_sender)
    claims = access_claims(1)
    claims["sub"] = EMAIL
    auth_client.cookies.set(ACCESS_COOKIE_NAME, encode_claims(claims))

    response = auth_client.get(ME_URL)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token payload."


def test_a_token_for_a_deleted_user_is_refused(auth_client, email_sender, db_session):
    register_and_verify(auth_client, email_sender)
    auth_client.cookies.set(ACCESS_COOKIE_NAME, encode_claims(access_claims(999999)))

    response = auth_client.get(ME_URL)

    assert response.status_code == 401
    assert response.json()["detail"] == "User not found"


def test_a_token_with_an_old_version_is_revoked(auth_client, email_sender, db_session):
    register_and_verify(auth_client, email_sender)
    login(auth_client)
    db_session.query(User).update({User.token_version: User.token_version + 1})
    db_session.commit()

    response = auth_client.get(ME_URL)

    assert response.status_code == 401
    assert response.json()["detail"] == "Token has been revoked."


def test_logout_revokes_the_token_for_good(auth_client, email_sender):
    register_and_verify(auth_client, email_sender)
    login(auth_client)
    stolen = auth_client.cookies.get(ACCESS_COOKIE_NAME)
    assert auth_client.get(ME_URL).status_code == 200

    auth_client.post(LOGOUT_URL)
    auth_client.cookies.set(ACCESS_COOKIE_NAME, stolen)

    response = auth_client.get(ME_URL)
    assert response.status_code == 401
    assert response.json()["detail"] == "Token has been revoked."


def test_logout_only_ends_the_session_that_asked(auth_client, email_sender):
    register_and_verify(auth_client, email_sender)
    login(auth_client)
    other = second_client()
    login(other)

    auth_client.post(LOGOUT_URL)

    assert other.get(ME_URL).status_code == 200


def test_logging_out_twice_or_with_a_bad_cookie_is_harmless(
    auth_client, email_sender, db_session
):
    register_and_verify(auth_client, email_sender)
    login(auth_client)
    auth_client.post(LOGOUT_URL)
    auth_client.cookies.set(ACCESS_COOKIE_NAME, "invalid.jwt.token")

    assert auth_client.post(LOGOUT_URL).status_code == 200
    assert len(db_session.scalars(select(RevokedToken)).all()) == 1


def test_changing_the_password_closes_the_other_sessions_but_not_this_one(
    auth_client, email_sender
):
    register_and_verify(auth_client, email_sender)
    login(auth_client)
    other = second_client()
    login(other)

    response = auth_client.put(
        CHANGE_PASSWORD_URL,
        json={"current_password": PASSWORD, "new_password": "NewPassword123!"},
    )

    assert response.status_code == 200
    assert auth_client.get(ME_URL).status_code == 200
    assert claims_of(auth_client)["tv"] == 1
    assert other.get(ME_URL).status_code == 401


def test_the_new_session_keeps_the_lifetime_of_the_old_one(auth_client, email_sender):
    register_and_verify(auth_client, email_sender)
    login(auth_client, remember_me=True)
    before = claims_of(auth_client)["exp"]

    auth_client.put(
        CHANGE_PASSWORD_URL,
        json={"current_password": PASSWORD, "new_password": "NewPassword123!"},
    )

    after = claims_of(auth_client)["exp"]
    assert abs(after - before) < 5
    assert after - datetime.now(UTC).timestamp() > timedelta(days=6).total_seconds()


def test_a_wrong_current_password_keeps_the_session_and_the_version(
    auth_client, email_sender
):
    register_and_verify(auth_client, email_sender)
    login(auth_client)

    response = auth_client.put(
        CHANGE_PASSWORD_URL,
        json={"current_password": "Wrong-Passw0rd!", "new_password": "NewPassword123!"},
    )

    assert response.status_code == 401
    assert auth_client.get(ME_URL).status_code == 200
    assert claims_of(auth_client)["tv"] == 0


def test_resetting_the_password_closes_every_session(auth_client, email_sender):
    register_and_verify(auth_client, email_sender)
    login(auth_client)
    auth_client.post(FORGOT_PASSWORD_URL, json={"email": EMAIL})
    token = TOKEN_QUERY.search(email_sender.sent[-1]["html_body"]).group(1)

    reset = auth_client.post(
        RESET_PASSWORD_URL, json={"token": token, "new_password": "NewPassword123!"}
    )

    assert reset.status_code == 200
    assert auth_client.get(ME_URL).status_code == 401


def test_expired_revoked_tokens_are_cleaned_up(auth_client, email_sender, db_session):
    now = datetime.now(UTC)
    db_session.add_all(
        [
            RevokedToken(jti="a" * 36, expires_at=now - timedelta(hours=1)),
            RevokedToken(jti="b" * 36, expires_at=now + timedelta(hours=1)),
        ]
    )
    db_session.commit()

    deleted = delete_expired_revoked_tokens(db_session)

    assert deleted == 1
    assert db_session.scalar(select(RevokedToken.jti)) == "b" * 36


def test_a_token_of_another_type_is_refused_even_with_all_the_claims(
    auth_client, email_sender, db_session
):
    register_and_verify(auth_client, email_sender)
    claims = access_claims(user_id_of(db_session))
    claims["type"] = "email_verification"
    auth_client.cookies.set(ACCESS_COOKIE_NAME, encode_claims(claims))

    assert auth_client.get(ME_URL).status_code == 401


def test_logging_out_twice_with_the_same_token_is_harmless(
    auth_client, email_sender, db_session
):
    register_and_verify(auth_client, email_sender)
    login(auth_client)
    token = auth_client.cookies.get(ACCESS_COOKIE_NAME)

    first = auth_client.post(LOGOUT_URL)
    auth_client.cookies.set(ACCESS_COOKIE_NAME, token)
    second = auth_client.post(LOGOUT_URL)

    assert first.status_code == second.status_code == 200
    assert len(db_session.scalars(select(RevokedToken)).all()) == 1
