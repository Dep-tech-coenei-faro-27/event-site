import pytest
from sqlalchemy import update

from app.core.security import ACCESS_COOKIE_NAME
from app.domains.auth import service
from app.domains.users.models import User
from tests.helpers import (
    LOGIN_URL,
    ME_URL,
    access_claims,
    encode_claims,
    register_and_verify,
    user_id_of,
)


def deactivate(db_session, email="ana@example.com"):
    db_session.execute(update(User).where(User.email == email).values(is_active=False))
    db_session.commit()


def test_unknown_email_still_runs_a_password_check(db_session, monkeypatch):
    checks = []
    monkeypatch.setattr(
        service, "verify_password", lambda *args: checks.append(args) or False
    )

    user = service.authenticate_user(db_session, "nobody@example.com", "Passw0rd!x")

    assert user is None
    assert checks == [("Passw0rd!x", service.DUMMY_PASSWORD_HASH)]


def test_wrong_password_runs_the_same_number_of_password_checks(
    db_session, monkeypatch, auth_client, email_sender
):
    register_and_verify(auth_client, email_sender)
    checks = []
    monkeypatch.setattr(
        service, "verify_password", lambda *args: checks.append(args) or False
    )

    service.authenticate_user(db_session, "ana@example.com", "Wrong-Passw0rd!")

    assert len(checks) == 1


def test_inactive_user_cannot_log_in(auth_client, email_sender, db_session):
    register_and_verify(auth_client, email_sender)
    deactivate(db_session)

    response = auth_client.post(
        LOGIN_URL, json={"email": "ana@example.com", "password": "Password123!"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_token_of_a_deactivated_user_is_rejected(auth_client, email_sender, db_session):
    register_and_verify(auth_client, email_sender)
    auth_client.post(
        LOGIN_URL, json={"email": "ana@example.com", "password": "Password123!"}
    )
    deactivate(db_session)

    response = auth_client.get(ME_URL)

    assert response.status_code == 401
    assert response.json()["detail"] == "Inactive user"


def test_valid_token_is_accepted(auth_client, email_sender, db_session):
    register_and_verify(auth_client, email_sender)
    claims = access_claims(user_id_of(db_session))
    auth_client.cookies.set(ACCESS_COOKIE_NAME, encode_claims(claims))

    assert auth_client.get(ME_URL).status_code == 200


@pytest.mark.parametrize("claim", ["exp", "sub", "type", "jti", "tv"])
def test_token_missing_a_required_claim_is_rejected(
    auth_client, email_sender, db_session, claim
):
    register_and_verify(auth_client, email_sender)
    claims = access_claims(user_id_of(db_session))
    del claims[claim]
    auth_client.cookies.set(ACCESS_COOKIE_NAME, encode_claims(claims))

    response = auth_client.get(ME_URL)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token."
