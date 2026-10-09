import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import ACCESS_COOKIE_NAME
from app.domains.users.models import StudentVerificationStatus, User
from tests.helpers import (
    ME_URL,
    access_claims,
    encode_claims,
    register_and_verify,
    register_user,
)

INSTITUTIONAL_DOMAIN = "student.ualg.pt"
INSTITUTIONAL_EMAIL = f"ana@{INSTITUTIONAL_DOMAIN}"


@pytest.fixture
def institutional_domains(monkeypatch):
    monkeypatch.setattr(
        settings, "STUDENT_EMAIL_DOMAINS", [INSTITUTIONAL_DOMAIN, "ualg.pt"]
    )


def _user(db_session, email: str) -> User:
    return db_session.scalar(select(User).where(User.email == email))


def test_institutional_email_is_auto_verified(
    auth_client, db_session, institutional_domains
):
    register_user(auth_client, None, email=INSTITUTIONAL_EMAIL)

    user = _user(db_session, INSTITUTIONAL_EMAIL)
    assert user.student_verification_status is StudentVerificationStatus.VERIFIED
    assert user.student_verified_at is not None


def test_non_institutional_email_stays_pending(
    auth_client, db_session, institutional_domains
):
    register_user(auth_client, None, email="ana@gmail.com")

    user = _user(db_session, "ana@gmail.com")
    assert user.student_verification_status is StudentVerificationStatus.PENDING
    assert user.student_verified_at is None


def test_without_configured_domains_everyone_stays_pending(
    auth_client, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "STUDENT_EMAIL_DOMAINS", [])
    register_user(auth_client, None, email=INSTITUTIONAL_EMAIL)

    user = _user(db_session, INSTITUTIONAL_EMAIL)
    assert user.student_verification_status is StudentVerificationStatus.PENDING


def test_me_exposes_student_status(
    auth_client, email_sender, db_session, institutional_domains
):
    register_and_verify(auth_client, email_sender, email=INSTITUTIONAL_EMAIL)
    user = _user(db_session, INSTITUTIONAL_EMAIL)
    auth_client.cookies.set(
        ACCESS_COOKIE_NAME,
        encode_claims(access_claims(user.id, user.token_version)),
    )

    body = auth_client.get(ME_URL).json()

    assert body["student_verification_status"] == "verified"
