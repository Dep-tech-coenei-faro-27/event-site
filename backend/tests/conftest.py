import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def build_test_engine():
    if TEST_DATABASE_URL:
        return create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    return create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def client():
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
def auth_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
