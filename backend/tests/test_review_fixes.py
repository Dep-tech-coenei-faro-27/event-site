import logging
import re
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    ACCESS_COOKIE_NAME,
    create_password_reset_token,
    verify_password,
)
from app.domains.auth.models import ResetPasswordToken
from app.domains.auth.service import register_reset_token
from app.domains.users.models import User
from app.domains.users.service import (
    VerificationLinkOutdatedError,
    get_user_by_email,
    mark_user_verified,
)
from app.main import create_app
from tests.helpers import (
    LOGIN_URL,
    REGISTER_URL,
    access_claims,
    encode_claims,
    register_and_verify,
    register_user,
    user_id_of,
)

FORGOT_URL = "/api/auth/forgot-password"
RESET_URL = "/api/auth/reset-password"
CHANGE_URL = "/api/auth/password"


@pytest.fixture(autouse=True)
def no_rate_limits(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)


def reset_token_from(email_sender) -> str:
    return re.search(r"token=([A-Za-z0-9._\-]+)", email_sender.sent[-1]["html_body"])[1]


def test_replacing_an_account_never_overwrites_one_verified_in_the_meantime(
    auth_client, email_sender, db_session, monkeypatch
):
    register_user(auth_client, email_sender, name="Original", password="Original123!")
    real_hash = __import__("app.domains.users.service", fromlist=["x"]).hash_password

    def verify_while_hashing(password):
        db_session.execute(
            update(User).where(User.email == "ana@example.com").values(is_verified=True)
        )
        db_session.commit()
        return real_hash(password)

    monkeypatch.setattr("app.domains.users.service.hash_password", verify_while_hashing)

    response = auth_client.post(
        REGISTER_URL,
        json={
            "name": "Intruso",
            "email": "ana@example.com",
            "password": "Intruso123!x",
        },
    )

    db_session.expire_all()
    user = db_session.scalar(select(User).where(User.email == "ana@example.com"))
    assert response.status_code == 409
    assert user.name == "Original"
    assert verify_password("Original123!", user.password_hash)


def test_resetting_the_password_also_confirms_the_email(
    auth_client, email_sender, db_session
):
    register_user(auth_client, email_sender)
    auth_client.post(FORGOT_URL, json={"email": "ana@example.com"})

    reset = auth_client.post(
        RESET_URL,
        json={"token": reset_token_from(email_sender), "new_password": "Brand-New123!"},
    )
    login = auth_client.post(
        LOGIN_URL, json={"email": "ana@example.com", "password": "Brand-New123!"}
    )

    db_session.expire_all()
    user = db_session.scalar(select(User).where(User.email == "ana@example.com"))
    assert reset.status_code == 200
    assert login.status_code == 200
    assert user.is_verified is True
    assert user.email_verified_at is not None


def test_a_reset_token_that_belongs_to_another_user_is_refused(
    auth_client, email_sender, db_session
):
    register_and_verify(auth_client, email_sender, email="ana@example.com")
    register_and_verify(auth_client, email_sender, email="joao@example.com")
    token, jti, expires = create_password_reset_token("joao@example.com")
    register_reset_token(
        db_session, user_id_of(db_session, "ana@example.com"), jti, expires
    )

    response = auth_client.post(
        RESET_URL, json={"token": token, "new_password": "Brand-New123!"}
    )

    row = db_session.scalar(
        select(ResetPasswordToken).where(ResetPasswordToken.jti == jti)
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid password reset token"
    assert row.used_at is None


def test_link_paths_must_start_with_a_single_slash():
    import pytest
    from pydantic import ValidationError

    from app.core.config import Settings

    values = {
        "ENVIRONMENT": "dev",
        "POSTGRES_USER": "u",
        "POSTGRES_PASSWORD": "p",
        "POSTGRES_DB": "d",
        "POSTGRES_HOST": "h",
        "POSTGRES_PORT": 5432,
        "JWT_SECRET_KEY": "k" * 40,
    }
    for bad in ["conta/verificar", "//evil.example/x", ""]:
        with pytest.raises(ValidationError):
            Settings(_env_file=None, FRONTEND_VERIFY_PATH=bad, **values)
    assert (
        Settings(
            _env_file=None, FRONTEND_RESET_PATH="/a/b", **values
        ).FRONTEND_RESET_PATH
        == "/a/b"
    )


def test_an_account_replaced_while_it_was_being_verified_is_not_verified(
    auth_client, email_sender, db_session, test_engine
):
    register_user(auth_client, email_sender)
    user = get_user_by_email(db_session, "ana@example.com")

    with Session(bind=test_engine) as other:
        other.execute(
            update(User).where(User.id == user.id).values(password_hash="replaced")
        )
        other.commit()

    with pytest.raises(VerificationLinkOutdatedError):
        mark_user_verified(db_session, user)
    assert (
        db_session.scalar(select(User.is_verified).where(User.id == user.id)) is False
    )


def test_verifying_twice_at_the_same_time_is_not_an_error(
    auth_client, email_sender, db_session
):
    register_user(auth_client, email_sender)
    user = get_user_by_email(db_session, "ana@example.com")
    stale = get_user_by_email(db_session, "ana@example.com")

    mark_user_verified(db_session, user)

    assert mark_user_verified(db_session, stale).is_verified is True


def test_changing_the_password_keeps_the_session_alive_even_when_it_is_about_to_expire(
    auth_client, email_sender, db_session
):
    register_and_verify(auth_client, email_sender)
    claims = access_claims(user_id_of(db_session))
    claims["exp"] = datetime.now(UTC) + timedelta(seconds=1)
    auth_client.cookies.set(ACCESS_COOKIE_NAME, encode_claims(claims))

    response = auth_client.put(
        CHANGE_URL,
        json={"current_password": "Password123!", "new_password": "Brand-New123!"},
    )

    assert response.status_code == 200
    max_age = int(re.search(r"Max-Age=(\d+)", response.headers["set-cookie"])[1])
    assert max_age >= 60


def test_a_warning_is_logged_in_prod_when_the_proxy_ips_are_not_set(
    monkeypatch, caplog
):
    monkeypatch.setattr(settings, "ENVIRONMENT", "prod")
    monkeypatch.delenv("FORWARDED_ALLOW_IPS", raising=False)

    with caplog.at_level(logging.WARNING):
        create_app()

    assert "FORWARDED_ALLOW_IPS" in caplog.text


def test_no_proxy_warning_when_the_proxy_ips_are_set_or_in_dev(monkeypatch, caplog):
    monkeypatch.setattr(settings, "ENVIRONMENT", "prod")
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "10.0.0.5")
    with caplog.at_level(logging.WARNING):
        create_app()
    monkeypatch.setattr(settings, "ENVIRONMENT", "dev")
    monkeypatch.delenv("FORWARDED_ALLOW_IPS", raising=False)
    with caplog.at_level(logging.WARNING):
        create_app()

    assert "FORWARDED_ALLOW_IPS" not in caplog.text


def test_a_warning_is_logged_when_only_localhost_is_trusted(monkeypatch, caplog):
    monkeypatch.setattr(settings, "ENVIRONMENT", "prod")
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "127.0.0.1")

    with caplog.at_level(logging.WARNING):
        create_app()

    assert "only trusts localhost" in caplog.text


def test_no_warning_when_a_docker_network_is_trusted(monkeypatch, caplog):
    monkeypatch.setattr(settings, "ENVIRONMENT", "prod")
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "172.16.0.0/12")

    with caplog.at_level(logging.WARNING):
        create_app()

    assert "FORWARDED_ALLOW_IPS" not in caplog.text
