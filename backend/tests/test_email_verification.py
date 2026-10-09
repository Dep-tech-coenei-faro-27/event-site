from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.email.base import EmailDeliveryError
from app.core.email.templates import VERIFICATION_EMAIL_SUBJECT
from app.domains.auth.router import EMAIL_VERIFICATION_SENT_MESSAGE
from app.domains.users.models import User
from tests.helpers import (
    REGISTER_URL,
    VERIFY_URL,
    extract_verification_token,
    register_user,
)

RESEND_URL = "/api/auth/resend-verification-email"


@pytest.fixture(autouse=True)
def no_rate_limits(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)


def test_register_sends_verification_email(auth_client, email_sender):
    register_user(auth_client, email_sender, email="ana@example.com")

    assert len(email_sender.sent) == 1
    sent = email_sender.sent[0]
    assert sent["to_email"] == "ana@example.com"
    assert sent["subject"] == VERIFICATION_EMAIL_SUBJECT
    assert sent["html_body"].startswith("<html")
    assert "conta/verificar?token=" in sent["html_body"]


def test_register_verification_token_contains_user_email(auth_client, email_sender):
    register_user(auth_client, email_sender, email="token-user@example.com")

    token = extract_verification_token(email_sender)
    payload = jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )

    assert payload["sub"] == "token-user@example.com"
    assert payload["type"] == "email_verification"


def test_register_creates_user_unverified(auth_client, email_sender, db_session):
    register_user(auth_client, email_sender, email="unverified@example.com")

    user = db_session.query(User).filter(User.email == "unverified@example.com").one()
    assert user.is_verified is False
    assert user.email_verified_at is None


def test_verify_email_success(auth_client, email_sender, db_session):
    register_user(auth_client, email_sender, email="verify-me@example.com")
    token = extract_verification_token(email_sender)

    response = auth_client.post(VERIFY_URL, json={"token": token})

    assert response.status_code == 200
    assert response.json() == {"message": "Email verified successfully"}

    user = db_session.query(User).filter(User.email == "verify-me@example.com").one()
    assert user.is_verified is True
    assert user.email_verified_at is not None
    verified_at = user.email_verified_at
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=UTC)
    assert verified_at <= datetime.now(UTC)


def test_verify_email_is_idempotent_when_already_verified(
    auth_client, email_sender, db_session
):
    register_user(auth_client, email_sender, email="twice@example.com")
    token = extract_verification_token(email_sender)

    first = auth_client.post(VERIFY_URL, json={"token": token})
    second = auth_client.post(VERIFY_URL, json={"token": token})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == {"message": "Email verified successfully"}

    user = db_session.query(User).filter(User.email == "twice@example.com").one()
    assert user.is_verified is True


def test_verify_email_rejects_invalid_token(auth_client, email_sender, db_session):
    register_user(auth_client, email_sender, email="invalid-token@example.com")

    response = auth_client.post(VERIFY_URL, json={"token": "not-a-real-token"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid verification token"

    user = (
        db_session.query(User).filter(User.email == "invalid-token@example.com").one()
    )
    assert user.is_verified is False


def test_verify_email_rejects_expired_token(auth_client, email_sender, db_session):
    register_user(auth_client, email_sender, email="expired@example.com")

    expired = jwt.encode(
        {
            "sub": "expired@example.com",
            "type": "email_verification",
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "exp": datetime.now(UTC) - timedelta(minutes=5),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = auth_client.post(VERIFY_URL, json={"token": expired})

    assert response.status_code == 400
    assert response.json()["detail"] == "Verification token has expired"

    user = db_session.query(User).filter(User.email == "expired@example.com").one()
    assert user.is_verified is False


def test_verify_email_rejects_token_signed_with_other_secret(
    auth_client, email_sender, db_session
):
    register_user(auth_client, email_sender, email="tampered@example.com")

    tampered = jwt.encode(
        {
            "sub": "tampered@example.com",
            "type": "email_verification",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        "some-other-secret-key-that-is-not-mine",
        algorithm=settings.JWT_ALGORITHM,
    )

    response = auth_client.post(VERIFY_URL, json={"token": tampered})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid verification token"

    user = db_session.query(User).filter(User.email == "tampered@example.com").one()
    assert user.is_verified is False


def test_verify_email_rejects_access_token(auth_client, email_sender, db_session):
    register_user(auth_client, email_sender, email="wrong-type@example.com")

    access_token = jwt.encode(
        {
            "sub": "wrong-type@example.com",
            "role": "user",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = auth_client.post(VERIFY_URL, json={"token": access_token})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid verification token"


def test_verify_email_rejects_token_with_non_string_subject(auth_client):
    non_string = jwt.encode(
        {
            "sub": 123456,
            "type": "email_verification",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = auth_client.post(VERIFY_URL, json={"token": non_string})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid verification token"


def test_verify_email_rejects_token_for_unknown_user(
    auth_client, email_sender, db_session
):
    register_user(auth_client, email_sender, email="someone-else@example.com")
    extract_verification_token(email_sender)

    unknown = jwt.encode(
        {
            "sub": "ghost@example.com",
            "type": "email_verification",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = auth_client.post(VERIFY_URL, json={"token": unknown})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid verification token"


def test_verify_email_missing_token_is_rejected_by_validation(
    auth_client, email_sender, db_session
):
    register_user(auth_client, email_sender, email="missing-token@example.com")

    response = auth_client.post(VERIFY_URL, json={})

    assert response.status_code == 422


def test_register_duplicate_does_not_send_verification_email(
    auth_client, email_sender, db_session
):
    payload = {
        "name": "Dupe",
        "email": "dupe@example.com",
        "password": "Password123!",
        "accept_terms": True,
    }

    first = auth_client.post(REGISTER_URL, json=payload)
    assert first.status_code == 201
    assert len(email_sender.sent) == 1
    db_session.query(User).update({User.is_verified: True})
    db_session.commit()

    second = auth_client.post(REGISTER_URL, json=payload)
    assert second.status_code == 409
    assert len(email_sender.sent) == 1


def test_register_still_succeeds_when_email_delivery_fails(db_session):
    class FailingSender:
        def send_html(self, to_email, subject, html_body):
            raise EmailDeliveryError("smtp is down")

    from fastapi.testclient import TestClient

    from app.core.email.factory import get_email_sender
    from app.db.session import get_db
    from app.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_sender] = lambda: FailingSender()

    try:
        with TestClient(app) as client:
            response = client.post(
                REGISTER_URL,
                json={
                    "name": "Resilient",
                    "email": "resilient@example.com",
                    "password": "Password123!",
                    "accept_terms": True,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    user = db_session.query(User).filter(User.email == "resilient@example.com").one()
    assert user is not None


def test_verification_email_escapes_html_in_registered_name(auth_client, email_sender):
    register_user(auth_client, email_sender, name='Ana "Q" & Co')

    html_body = email_sender.sent[0]["html_body"]
    assert 'Ana "Q" & Co' not in html_body
    assert "Ana &quot;Q&quot; &amp; Co" in html_body


def test_resend_verification_email_sends_fresh_email(auth_client, email_sender):
    register_user(auth_client, email_sender, email="resend-me@example.com")
    first_token = extract_verification_token(email_sender)

    response = auth_client.post(RESEND_URL, json={"email": "resend-me@example.com"})

    assert response.status_code == 200
    assert response.json() == {"message": EMAIL_VERIFICATION_SENT_MESSAGE}

    assert len(email_sender.sent) == 2
    sent = email_sender.sent[1]
    assert sent["to_email"] == "resend-me@example.com"
    assert sent["subject"] == VERIFICATION_EMAIL_SUBJECT
    assert "conta/verificar?token=" in sent["html_body"]

    second_token = extract_verification_token(email_sender)
    first_payload = jwt.decode(
        first_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    second_payload = jwt.decode(
        second_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    assert second_payload["sub"] == "resend-me@example.com"
    assert second_payload["type"] == "email_verification"
    assert second_payload["iat"] >= first_payload["iat"]


def test_resend_token_completes_verification(auth_client, email_sender, db_session):
    register_user(auth_client, email_sender, email="late-link@example.com")
    extract_verification_token(email_sender)

    response = auth_client.post(RESEND_URL, json={"email": "late-link@example.com"})
    assert response.status_code == 200

    fresh_token = extract_verification_token(email_sender)
    verify = auth_client.post(VERIFY_URL, json={"token": fresh_token})

    assert verify.status_code == 200
    assert verify.json() == {"message": "Email verified successfully"}

    user = db_session.query(User).filter(User.email == "late-link@example.com").one()
    assert user.is_verified is True


def test_resend_does_not_send_for_unknown_email(auth_client, email_sender):
    response = auth_client.post(RESEND_URL, json={"email": "ghost@example.com"})

    assert response.status_code == 200
    assert response.json() == {"message": EMAIL_VERIFICATION_SENT_MESSAGE}
    assert email_sender.sent == []


def test_resend_does_not_send_for_verified_user(auth_client, email_sender, db_session):
    register_user(auth_client, email_sender, email="already-verified@example.com")
    token = extract_verification_token(email_sender)
    auth_client.post(VERIFY_URL, json={"token": token})
    assert len(email_sender.sent) == 1

    response = auth_client.post(
        RESEND_URL, json={"email": "already-verified@example.com"}
    )

    assert response.status_code == 200
    assert response.json() == {"message": EMAIL_VERIFICATION_SENT_MESSAGE}
    assert len(email_sender.sent) == 1


def test_resend_normalizes_email(auth_client, email_sender):
    register_user(auth_client, email_sender, email="mixed@example.com")
    extract_verification_token(email_sender)

    response = auth_client.post(RESEND_URL, json={"email": "  MIXED@EXAMPLE.COM "})

    assert response.status_code == 200
    assert len(email_sender.sent) == 2
    assert email_sender.sent[1]["to_email"] == "mixed@example.com"


def test_resend_verification_email_missing_email_rejected(auth_client, email_sender):
    response = auth_client.post(RESEND_URL, json={})

    assert response.status_code == 422


def test_verification_token_ttl_matches_setting(auth_client, email_sender):
    register_user(auth_client, email_sender, email="ttl-check@example.com")

    token = extract_verification_token(email_sender)
    payload = jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )

    lifetime = payload["exp"] - payload["iat"]
    assert lifetime == settings.JWT_EMAIL_VERIFICATION_EXPIRE_MINUTES * 60


def test_verify_expired_token_requires_resend(auth_client, email_sender, db_session):
    register_user(auth_client, email_sender, email="needs-resend@example.com")

    expired = jwt.encode(
        {
            "sub": "needs-resend@example.com",
            "type": "email_verification",
            "iat": datetime.now(UTC) - timedelta(minutes=31),
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    rejected = auth_client.post(VERIFY_URL, json={"token": expired})
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "Verification token has expired"

    resent = auth_client.post(RESEND_URL, json={"email": "needs-resend@example.com"})
    assert resent.status_code == 200

    fresh_token = extract_verification_token(email_sender)
    accepted = auth_client.post(VERIFY_URL, json={"token": fresh_token})

    assert accepted.status_code == 200
    assert accepted.json() == {"message": "Email verified successfully"}

    user = db_session.query(User).filter(User.email == "needs-resend@example.com").one()
    assert user.is_verified is True
