from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select, update

from app.core.config import settings
from app.core.security import (
    create_email_verification_token,
    password_fingerprint,
    validate_password,
)
from app.core.validators import validate_name
from app.domains.auth.models import ResetPasswordToken
from app.domains.users.cleanup import delete_unverified_users
from app.domains.users.models import User
from tests.helpers import (
    LOGIN_URL,
    REGISTER_URL,
    TOKEN_QUERY,
    VERIFY_URL,
    extract_verification_token,
)
from tests.test_auth import FORGOT_PASSWORD_URL
from tests.test_password import RESET_PASSWORD_URL

EMAIL = "ana@example.com"
RESEND_URL = "/api/auth/resend-verification-email"


@pytest.fixture(autouse=True)
def no_rate_limits(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)


def register(client, name="Ana Silva", email=EMAIL, password="Password123!"):
    return client.post(
        REGISTER_URL, json={"name": name, "email": email, "password": password}
    )


def verify(client, token):
    return client.post(VERIFY_URL, json={"token": token})


def login(client, password):
    return client.post(LOGIN_URL, json={"email": EMAIL, "password": password})


# --- names


@pytest.mark.parametrize(
    "name",
    ["Ana Silva", "José Çalves", "李 小龙", "O'Brien-Smith", "Ana", "Maria João"],
)
def test_real_names_are_accepted(name):
    assert validate_name(name) == name


def test_names_are_trimmed():
    assert validate_name("  Ana Silva \t") == "Ana Silva"


@pytest.mark.parametrize(
    ("name", "rules"),
    [
        ("   ", ["blank"]),
        ("​​", ["invalid_characters", "no_letter"]),
        ("Ana\u0000", ["invalid_characters"]),
        ("Ana\nSilva", ["invalid_characters"]),
        ("Ana‮Silva", ["invalid_characters"]),
        ("<b>Ana</b>", ["invalid_characters"]),
        ("12345", ["no_letter"]),
        ("😀", ["no_letter"]),
    ],
)
def test_bad_names_are_rejected_with_the_reason(auth_client, name, rules):
    response = register(auth_client, name=name, email="bad@example.com")

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["type"] == "name_invalid"
    assert error["loc"] == ["body", "name"]
    assert error["ctx"]["rules"] == rules


def test_a_name_with_a_null_character_is_a_422_and_not_a_500(auth_client):
    assert register(auth_client, name="Ana\u0000").status_code == 422


def test_the_name_is_stored_trimmed(auth_client, db_session):
    register(auth_client, name="  Ana Silva  ")

    assert db_session.scalar(select(User.name)) == "Ana Silva"


# --- passwords


def test_every_failed_password_rule_is_reported_at_once(auth_client):
    response = register(auth_client, password="abcdefgh")

    error = response.json()["detail"][0]
    assert response.status_code == 422
    assert error["type"] == "password_invalid"
    assert error["ctx"]["rules"] == [
        "missing_uppercase",
        "missing_digit",
        "missing_symbol",
    ]


def test_a_password_that_is_too_long_for_bcrypt_is_reported(auth_client):
    response = register(auth_client, password="Aa1!" + "x" * 80)

    assert response.json()["detail"][0]["ctx"]["rules"] == ["too_long"]


def test_a_valid_password_passes():
    assert validate_password("Password123!") == "Password123!"


def test_the_error_never_repeats_the_password(auth_client):
    response = register(auth_client, password="secretpassword")

    assert "secretpassword" not in response.text


# --- emails


@pytest.mark.parametrize("email", ["ＣＡＳＥ@example.com", "josé@example.com"])
def test_registering_with_a_non_ascii_email_is_refused(auth_client, email):
    response = register(auth_client, email=email)

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "email_not_ascii"


@pytest.mark.parametrize(
    ("url", "body"),
    [
        (LOGIN_URL, {"email": "ＣＡＳＥ@example.com", "password": "Password123!"}),
        (RESEND_URL, {"email": "ＣＡＳＥ@example.com"}),
        (FORGOT_PASSWORD_URL, {"email": "ＣＡＳＥ@example.com"}),
    ],
)
def test_the_other_endpoints_refuse_non_ascii_emails_too(auth_client, url, body):
    assert auth_client.post(url, json=body).status_code == 422


def test_an_ordinary_email_still_works(auth_client):
    assert register(auth_client, email="Ana.Silva+enei@Example.com").status_code == 201


# --- verification tied to the password


def test_a_verification_token_carries_a_fingerprint_of_the_password(
    auth_client, email_sender, db_session
):
    register(auth_client)
    token = extract_verification_token(email_sender)

    claims = jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    user = db_session.scalar(select(User))
    assert claims["pwh"] == password_fingerprint(user.password_hash)
    assert user.password_hash not in token


def test_a_verification_token_without_the_fingerprint_is_refused(
    auth_client, email_sender
):
    register(auth_client)
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": EMAIL,
            "type": "email_verification",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    assert verify(auth_client, token).status_code == 400


def test_a_token_made_for_another_password_is_refused(auth_client, email_sender):
    register(auth_client)
    token = create_email_verification_token(EMAIL, "another-hash")

    response = verify(auth_client, token)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid verification token"


def test_the_link_stops_working_when_the_password_changes(auth_client, email_sender):
    register(auth_client)
    old_link = extract_verification_token(email_sender)
    auth_client.post(FORGOT_PASSWORD_URL, json={"email": EMAIL})
    reset_token = TOKEN_QUERY.search(email_sender.sent[-1]["html_body"]).group(1)
    auth_client.post(
        RESET_PASSWORD_URL, json={"token": reset_token, "new_password": "Other123!x"}
    )

    assert verify(auth_client, old_link).status_code == 400


# --- registering an email that was never verified


def test_someone_who_registers_first_cannot_keep_an_email_blocked(
    auth_client, email_sender, db_session
):
    register(auth_client, name="Attacker", password="Attacker123!")
    attacker_link = extract_verification_token(email_sender)
    attacker_id = db_session.scalar(select(User.id))

    owner = register(auth_client, name="Real Owner", password="Owner123!x")

    assert owner.status_code == 201
    assert owner.json()["id"] == attacker_id
    assert owner.json()["name"] == "Real Owner"
    assert verify(auth_client, attacker_link).status_code == 400

    assert (
        verify(auth_client, extract_verification_token(email_sender)).status_code == 200
    )
    assert login(auth_client, "Owner123!x").status_code == 200
    assert login(auth_client, "Attacker123!").status_code == 401


def test_registering_twice_sends_a_fresh_email_each_time(
    auth_client, email_sender, db_session
):
    register(auth_client)
    register(auth_client, password="Another123!x")

    assert len(email_sender.sent) == 2
    assert len(db_session.scalars(select(User)).all()) == 1


def test_a_verified_account_is_never_replaced(auth_client, email_sender, db_session):
    register(auth_client)
    verify(auth_client, extract_verification_token(email_sender))

    second = register(auth_client, name="Intruder", password="Intruder123!")

    assert second.status_code == 409
    assert login(auth_client, "Password123!").status_code == 200
    assert login(auth_client, "Intruder123!").status_code == 401
    assert db_session.scalar(select(User.name)) == "Ana Silva"


def test_replacing_an_account_closes_the_pending_reset_links(
    auth_client, email_sender, db_session
):
    register(auth_client)
    auth_client.post(FORGOT_PASSWORD_URL, json={"email": EMAIL})
    reset_link = TOKEN_QUERY.search(email_sender.sent[-1]["html_body"]).group(1)

    register(auth_client, name="Real Owner", password="Owner123!x")

    response = auth_client.post(
        RESET_PASSWORD_URL, json={"token": reset_link, "new_password": "Other123!x"}
    )
    assert response.status_code == 400
    assert db_session.scalar(select(ResetPasswordToken.used_at)) is not None


def test_replacing_an_account_restarts_the_cleanup_clock(auth_client, db_session):
    register(auth_client)
    long_ago = datetime.now(UTC) - timedelta(days=30)
    db_session.execute(update(User).values(created_at=long_ago))
    db_session.commit()

    register(auth_client, password="Another123!x")

    assert delete_unverified_users(db_session, 7) == 0
