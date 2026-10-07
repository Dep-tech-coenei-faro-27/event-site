import logging
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.email import EmailDeliveryError
from app.core.email.factory import get_email_sender
from app.core.email.templates import PASSWORD_CHANGED_SUBJECT
from app.domains.auth.models import ResetPasswordToken
from app.domains.auth.service import get_password_reset_token
from app.domains.users.cleanup import delete_expired_reset_tokens
from app.domains.users.models import User
from app.domains.users.service import (
    ResetTokenUsedError,
    get_user_by_email,
    reset_user_password,
)
from app.main import app
from tests.helpers import LOGIN_URL, TOKEN_QUERY, VERIFY_URL, register_and_verify
from tests.test_auth import FORGOT_PASSWORD_URL
from tests.test_password import CHANGE_PASSWORD_URL, RESET_PASSWORD_URL

EMAIL = "ana@example.com"


class FailingSender:
    def send_html(self, to_email, subject, html_body):
        raise EmailDeliveryError("smtp is down")


@pytest.fixture(autouse=True)
def no_rate_limits(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)


def reset_token_from(email_sender):
    return TOKEN_QUERY.search(email_sender.sent[-1]["html_body"]).group(1)


def request_reset_token(auth_client, email_sender):
    response = auth_client.post(FORGOT_PASSWORD_URL, json={"email": EMAIL})
    assert response.status_code == 200
    return reset_token_from(email_sender)


def reset(auth_client, token, password="NewPassword123!"):
    return auth_client.post(
        RESET_PASSWORD_URL, json={"token": token, "new_password": password}
    )


def test_a_reset_token_works_only_once(auth_client, email_sender):
    register_and_verify(auth_client, email_sender)
    token = request_reset_token(auth_client, email_sender)

    first = reset(auth_client, token)
    second = reset(auth_client, token, "Another123!Password")

    assert first.status_code == 200
    assert second.status_code == 400
    assert second.json()["detail"] == "Password reset token has already been used"


def test_two_requests_with_the_same_token_cannot_both_win(
    auth_client, email_sender, db_session
):
    register_and_verify(auth_client, email_sender)
    request_reset_token(auth_client, email_sender)
    user = get_user_by_email(db_session, EMAIL)
    token_row = db_session.scalar(select(ResetPasswordToken))
    stale_copy = get_password_reset_token(db_session, token_row.jti)

    reset_user_password(db_session, user, "NewPassword123!", token_row)

    with pytest.raises(ResetTokenUsedError):
        reset_user_password(db_session, user, "Another123!Password", stale_copy)
    login = auth_client.post(
        LOGIN_URL, json={"email": EMAIL, "password": "NewPassword123!"}
    )
    assert login.status_code == 200


def test_the_other_pending_reset_links_stop_working(auth_client, email_sender):
    register_and_verify(auth_client, email_sender)
    first_link = request_reset_token(auth_client, email_sender)
    second_link = request_reset_token(auth_client, email_sender)

    assert reset(auth_client, second_link).status_code == 200

    stale = reset(auth_client, first_link, "Another123!Password")
    assert stale.status_code == 400
    assert stale.json()["detail"] == "Password reset token has already been used"


def test_a_reset_token_belongs_to_the_user_that_asked(
    auth_client, email_sender, db_session
):
    register_and_verify(auth_client, email_sender)
    request_reset_token(auth_client, email_sender)

    token_row = db_session.scalar(select(ResetPasswordToken))

    assert token_row.user_id == get_user_by_email(db_session, EMAIL).id


def test_the_reset_token_has_a_maximum_length(auth_client):
    response = reset(auth_client, "a" * 2049)

    assert response.status_code == 422


def test_an_inactive_account_cannot_reset_its_password(
    auth_client, email_sender, db_session
):
    register_and_verify(auth_client, email_sender)
    token = request_reset_token(auth_client, email_sender)
    db_session.query(User).update({User.is_active: False})
    db_session.commit()

    response = reset(auth_client, token)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid password reset token"


def test_login_with_a_short_password_is_a_normal_401(auth_client):
    response = auth_client.post(LOGIN_URL, json={"email": EMAIL, "password": "abc"})

    assert response.status_code == 401


def test_a_failed_reset_email_is_logged_without_the_address(
    auth_client, email_sender, caplog
):
    register_and_verify(auth_client, email_sender)
    app.dependency_overrides[get_email_sender] = lambda: FailingSender()

    with caplog.at_level(logging.WARNING):
        response = auth_client.post(FORGOT_PASSWORD_URL, json={"email": EMAIL})

    assert response.status_code == 200
    assert "Failed to send password reset email to a***@example.com" in caplog.text
    assert EMAIL not in caplog.text


def test_email_links_use_the_configured_frontend_paths(
    auth_client, email_sender, monkeypatch
):
    monkeypatch.setattr(settings, "FRONTEND_VERIFY_PATH", "/verificar-conta")
    monkeypatch.setattr(settings, "FRONTEND_RESET_PATH", "/nova-password")

    register_and_verify(auth_client, email_sender)
    assert "/verificar-conta?token=" in email_sender.sent[0]["html_body"]

    auth_client.post(FORGOT_PASSWORD_URL, json={"email": EMAIL})
    assert "/nova-password?token=" in email_sender.sent[-1]["html_body"]


def test_expired_reset_tokens_are_deleted_and_current_ones_kept(
    auth_client, email_sender, db_session
):
    register_and_verify(auth_client, email_sender)
    user = get_user_by_email(db_session, EMAIL)
    now = datetime.now(UTC)
    db_session.add_all(
        [
            ResetPasswordToken(
                user_id=user.id, jti="old", expires_at=now - timedelta(days=3)
            ),
            ResetPasswordToken(
                user_id=user.id, jti="new", expires_at=now + timedelta(minutes=10)
            ),
        ]
    )
    db_session.commit()

    deleted = delete_expired_reset_tokens(db_session)

    assert deleted == 1
    assert db_session.scalar(select(ResetPasswordToken.jti)) == "new"


def test_changing_the_password_sends_a_notification(auth_client, email_sender):
    register_and_verify(auth_client, email_sender)
    auth_client.post(LOGIN_URL, json={"email": EMAIL, "password": "Password123!"})

    response = auth_client.put(
        CHANGE_PASSWORD_URL,
        json={"current_password": "Password123!", "new_password": "NewPassword123!"},
    )

    assert response.status_code == 200
    notice = email_sender.sent[-1]
    assert notice["to_email"] == EMAIL
    assert notice["subject"] == PASSWORD_CHANGED_SUBJECT
    assert "Ana Silva" in notice["html_body"]


def test_resetting_the_password_sends_a_notification(auth_client, email_sender):
    register_and_verify(auth_client, email_sender)
    token = request_reset_token(auth_client, email_sender)

    assert reset(auth_client, token).status_code == 200

    assert email_sender.sent[-1]["subject"] == PASSWORD_CHANGED_SUBJECT


def test_a_failed_notification_does_not_fail_the_change_and_hides_the_address(
    auth_client, email_sender, caplog
):
    register_and_verify(auth_client, email_sender)
    auth_client.post(LOGIN_URL, json={"email": EMAIL, "password": "Password123!"})
    app.dependency_overrides[get_email_sender] = lambda: FailingSender()

    with caplog.at_level(logging.WARNING):
        response = auth_client.put(
            CHANGE_PASSWORD_URL,
            json={
                "current_password": "Password123!",
                "new_password": "NewPassword123!",
            },
        )

    assert response.status_code == 200
    assert "Failed to send password changed email to a***@example.com" in caplog.text
    assert EMAIL not in caplog.text


def test_changing_the_password_is_rate_limited_per_user(
    auth_client, email_sender, monkeypatch
):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_PASSWORD_CHANGE_PER_15_MINUTES", 3)
    register_and_verify(auth_client, email_sender)
    auth_client.post(LOGIN_URL, json={"email": EMAIL, "password": "Password123!"})
    guess = {"current_password": "Wrong-Passw0rd!", "new_password": "NewPassword123!"}

    statuses = [
        auth_client.put(CHANGE_PASSWORD_URL, json=guess).status_code for _ in range(5)
    ]

    assert statuses == [401, 401, 401, 429, 429]


@pytest.mark.parametrize(
    ("url", "body"),
    [
        (VERIFY_URL, {"token": "not-a-token"}),
        (RESET_PASSWORD_URL, {"token": "not-a-token", "new_password": "NewPass123!"}),
    ],
)
def test_token_endpoints_are_limited_per_ip(auth_client, monkeypatch, url, body):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_TOKEN_PER_IP_PER_MINUTE", 3)

    statuses = [auth_client.post(url, json=body).status_code for _ in range(5)]

    assert statuses == [400, 400, 400, 429, 429]
