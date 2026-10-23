import os

os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-only-jwt-secret-that-is-at-least-32-bytes-long",
)
os.environ.setdefault("PAYMENTS_MODE", "simulated")
os.environ.setdefault("EMAIL_OUTBOX_WORKER", "0")
# Tests never send email: no SMTP server is configured, even if the developer's own
# backend/.env has one (the environment wins over that file).
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_USER"] = ""
os.environ["SMTP_PASSWORD"] = ""
os.environ["EMAIL_SENDER"] = ""
# Tests ask the provider every time; the throttle has its own tests.
os.environ.setdefault("PAYMENT_PROVIDER_MIN_INTERVAL_SECONDS", "0")

import smtplib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.email import EmailSender, get_email_sender
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


class FakeEmailSender(EmailSender):
    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send_html(self, to_email: str, subject: str, html_body: str) -> None:
        self.sent.append(
            {"to_email": to_email, "subject": subject, "html_body": html_body}
        )


def build_test_engine():
    if TEST_DATABASE_URL:
        return create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    return create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture(autouse=True)
def no_smtp_connection(monkeypatch):
    """A tripwire: no test may open a connection to an SMTP server.

    The tests of the SMTP sender replace these two with their own fakes (their
    ``monkeypatch.setattr`` runs after this one), so only a real attempt trips it.
    """

    def refuse(*args, **kwargs):
        raise AssertionError("a test tried to connect to an SMTP server")

    monkeypatch.setattr(smtplib, "SMTP", refuse)
    monkeypatch.setattr(smtplib, "SMTP_SSL", refuse)


@pytest.fixture
def email_sender():
    sender = FakeEmailSender()
    app.dependency_overrides[get_email_sender] = lambda: sender
    yield sender
    app.dependency_overrides.clear()


@pytest.fixture
def client(email_sender):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def test_engine():
    engine = build_test_engine()
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    with test_engine.begin() as conn:
        conn.execute(text("DELETE FROM email_outbox"))
        conn.execute(text("DELETE FROM student_proof_events"))
        conn.execute(text("DELETE FROM institution_nipcs"))
        conn.execute(text("DELETE FROM student_proofs"))
        conn.execute(text("DELETE FROM transactions"))
        conn.execute(text("DELETE FROM tickets"))
        conn.execute(text("DELETE FROM ticket_tiers"))
        conn.execute(text("DELETE FROM reset_password_tokens"))
        conn.execute(text("DELETE FROM revoked_tokens"))
        conn.execute(text("DELETE FROM users"))
        conn.execute(text("DELETE FROM rate_limits"))
    session = Session(bind=test_engine)
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def auth_client(db_session, email_sender):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()
