import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import app

TEST_DATABASE_NAME = os.environ.get("TEST_POSTGRES_DB", "event_site_test")
TEST_POSTGRES_HOST = os.environ.get("TEST_POSTGRES_HOST", "localhost")


def test_database_url() -> str:
    return (
        f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{TEST_POSTGRES_HOST}:{settings.POSTGRES_PORT}/{TEST_DATABASE_NAME}"
    )


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(test_database_url())
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    with test_engine.begin() as conn:
        conn.execute(text("TRUNCATE users RESTART IDENTITY"))
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
