import os

os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-only-jwt-secret-that-is-at-least-32-bytes-long",
)

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
        conn.execute(text("DELETE FROM users"))
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
