import re
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings
from app.core.email.base import EmailDeliveryError
from app.core.email.templates import VERIFICATION_EMAIL_SUBJECT
from app.domains.users.models import User

REGISTER_URL = "/api/auth/register"
VERIFY_URL = "/api/auth/verify-email"

_TOKEN_QUERY = re.compile(r"[?&]token=([A-Za-z0-9._\-]+)")


def _register(
    auth_client,
    email_sender,
    name="Ana Silva",
    email="ana@example.com",
    password="password123",
):
    response = auth_client.post(
        REGISTER_URL,
        json={"name": name, "email": email, "password": password},
    )
    assert response.status_code == 201
    return response


def _extract_token(email_sender) -> str:
    assert len(email_sender.sent) == 1
    link = _TOKEN_QUERY.search(email_sender.sent[0]["html_body"])
    assert link is not None
    return link.group(1)


def test_register_sends_verification_email(auth_client, email_sender):
    _register(auth_client, email_sender, email="ana@example.com")

    assert len(email_sender.sent) == 1
    sent = email_sender.sent[0]
    assert sent["to_email"] == "ana@example.com"
    assert sent["subject"] == VERIFICATION_EMAIL_SUBJECT
    assert sent["html_body"].startswith("<html")
    assert "verify-email?token=" in sent["html_body"]


def test_register_verification_token_contains_user_email(auth_client, email_sender):
    _register(auth_client, email_sender, email="token-user@example.com")

    token = _extract_token(email_sender)
    payload = jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )

    assert payload["sub"] == "token-user@example.com"
    assert payload["type"] == "email_verification"


def test_register_creates_user_unverified(auth_client, email_sender, db_session):
    _register(auth_client, email_sender, email="unverified@example.com")

    user = db_session.query(User).filter(User.email == "unverified@example.com").one()
    assert user.is_verified is False
    assert user.email_verified_at is None


def test_verify_email_success(auth_client, email_sender, db_session):
    _register(auth_client, email_sender, email="verify-me@example.com")
    token = _extract_token(email_sender)

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
    _register(auth_client, email_sender, email="twice@example.com")
    token = _extract_token(email_sender)

    first = auth_client.post(VERIFY_URL, json={"token": token})
    second = auth_client.post(VERIFY_URL, json={"token": token})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == {"message": "Email verified successfully"}

    user = db_session.query(User).filter(User.email == "twice@example.com").one()
    assert user.is_verified is True


def test_verify_email_rejects_invalid_token(auth_client, email_sender, db_session):
    _register(auth_client, email_sender, email="invalid-token@example.com")

    response = auth_client.post(VERIFY_URL, json={"token": "not-a-real-token"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid verification token"

    user = (
        db_session.query(User).filter(User.email == "invalid-token@example.com").one()
    )
    assert user.is_verified is False


def test_verify_email_rejects_expired_token(auth_client, email_sender, db_session):
    _register(auth_client, email_sender, email="expired@example.com")

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
    _register(auth_client, email_sender, email="tampered@example.com")

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
    _register(auth_client, email_sender, email="wrong-type@example.com")

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


def test_verify_email_rejects_token_for_unknown_user(
    auth_client, email_sender, db_session
):
    _register(auth_client, email_sender, email="someone-else@example.com")
    _extract_token(email_sender)

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
    _register(auth_client, email_sender, email="missing-token@example.com")

    response = auth_client.post(VERIFY_URL, json={})

    assert response.status_code == 422


def test_register_duplicate_does_not_send_verification_email(
    auth_client, email_sender, db_session
):
    payload = {
        "name": "Dupe",
        "email": "dupe@example.com",
        "password": "password123",
    }

    first = auth_client.post(REGISTER_URL, json=payload)
    assert first.status_code == 201
    assert len(email_sender.sent) == 1

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
                    "password": "password123",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    user = db_session.query(User).filter(User.email == "resilient@example.com").one()
    assert user is not None


def test_verification_email_escapes_html_in_registered_name(auth_client, email_sender):
    _register(auth_client, email_sender, name="<script>alert(1)</script>")

    html_body = email_sender.sent[0]["html_body"]
    assert "<script>" not in html_body
    assert "&lt;script&gt;" in html_body
