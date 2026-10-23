"""The migration of the proof of enrolment, on a database the migrations created."""

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from tests.conftest import TEST_DATABASE_URL

BACKEND_DIR = Path(__file__).resolve().parents[1]
BEFORE = "d6b3e9a15c47"
THIS = "f1a8d3c6e902"

pytestmark = pytest.mark.skipif(
    not (TEST_DATABASE_URL or "").startswith("postgresql"),
    reason="the migrations are written for PostgreSQL",
)


@pytest.fixture
def scratch_database():
    """An empty database, made for the test and dropped after it."""
    server = make_url(TEST_DATABASE_URL)
    name = f"migration_{uuid.uuid4().hex[:12]}"
    admin = create_engine(server, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = server.set(database=name)
    engine = create_engine(url)
    yield url, engine
    engine.dispose()
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    admin.dispose()


def alembic(url, *arguments):
    env = {
        **os.environ,
        "POSTGRES_USER": url.username,
        "POSTGRES_PASSWORD": url.password,
        "POSTGRES_HOST": url.host,
        "POSTGRES_PORT": str(url.port),
        "POSTGRES_DB": url.database,
    }
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]


def insert_user(engine, email, status):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (name, email, password_hash, role, is_verified,"
                " student_verification_status, is_active, token_version,"
                " terms_accepted_at, created_at, updated_at)"
                " VALUES ('Ana', :email, 'x', 'USER', true, :status, true, 0,"
                " now(), now(), now())"
            ),
            {"email": email, "status": status},
        )


def test_the_migrations_build_the_tables_of_the_proof(scratch_database):
    url, engine = scratch_database

    alembic(url, "upgrade", "head")

    names = set(inspect(engine).get_table_names())
    assert {"student_proofs", "student_proof_events", "institution_nipcs"} <= names
    indexes = {index["name"] for index in inspect(engine).get_indexes("student_proofs")}
    assert {
        "uq_student_proofs_one_active",
        "uq_student_proofs_verified_hash",
    } <= indexes


def test_the_partial_indexes_hold_in_the_database(scratch_database):
    url, engine = scratch_database
    alembic(url, "upgrade", "head")
    insert_user(engine, "a@x.pt", "none")
    insert_user(engine, "b@x.pt", "none")

    def proof(user, status, digest="a" * 64):
        return text(
            "INSERT INTO student_proofs (user_id, status, file_kind, file_hash, report)"
            f" SELECT id, '{status}', 'pdf', '{digest}', '{{}}' FROM users"
            f" WHERE email = '{user}'"
        )

    with engine.begin() as conn:
        conn.execute(proof("a@x.pt", "rejected"))
        conn.execute(proof("a@x.pt", "submitted"))
    with pytest.raises(Exception, match="uq_student_proofs_one_active"):
        with engine.begin() as conn:
            conn.execute(proof("a@x.pt", "submitted", "b" * 64))
    with engine.begin() as conn:
        conn.execute(proof("a@x.pt", "verified", "c" * 64))
    with pytest.raises(Exception, match="uq_student_proofs_verified_hash"):
        with engine.begin() as conn:
            conn.execute(proof("b@x.pt", "verified", "c" * 64))


def test_the_status_constraint_accepts_the_old_and_the_new_values(scratch_database):
    url, engine = scratch_database
    alembic(url, "upgrade", "head")

    for number, status in enumerate(
        ["pending", "none", "submitted", "verified", "rejected"]
    ):
        insert_user(engine, f"u{number}@x.pt", status)
    with pytest.raises(Exception, match="ck_users_student_status"):
        insert_user(engine, "bad@x.pt", "approved")


def test_accounts_from_before_keep_working_and_read_as_none(scratch_database):
    from sqlalchemy.orm import Session

    from app.domains.users.models import StudentVerificationStatus, User

    url, engine = scratch_database
    alembic(url, "upgrade", BEFORE)
    insert_user(engine, "old@x.pt", "pending")

    alembic(url, "upgrade", THIS)

    with engine.connect() as conn:
        stored = conn.execute(
            text("SELECT student_verification_status FROM users")
        ).scalar_one()
    assert stored == "pending"
    with Session(bind=engine) as session:
        user = session.query(User).one()
        assert user.student_verification_status is StudentVerificationStatus.NONE


def test_the_migration_can_be_undone(scratch_database):
    url, engine = scratch_database
    alembic(url, "upgrade", "head")
    insert_user(engine, "a@x.pt", "none")
    insert_user(engine, "b@x.pt", "submitted")

    alembic(url, "downgrade", BEFORE)

    assert "student_proofs" not in inspect(engine).get_table_names()
    with engine.connect() as conn:
        values = (
            conn.execute(text("SELECT DISTINCT student_verification_status FROM users"))
            .scalars()
            .all()
        )
    assert values == ["pending"]
