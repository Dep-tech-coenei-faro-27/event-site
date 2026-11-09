"""The ticket tables on a database the migrations created (not ``create_all``)."""

import os
import re
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.domains.payments.models import TicketTier
from app.domains.tickets.models import PaymentStatus, Ticket
from app.domains.users.models import User
from tests.conftest import TEST_DATABASE_URL

pytestmark = pytest.mark.skipif(
    not (TEST_DATABASE_URL or "").startswith("postgresql"),
    reason="the migrations are written for PostgreSQL",
)


BACKEND_DIR = Path(__file__).resolve().parents[1]


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


def test_each_of_the_five_modalities_gets_a_ticket(scratch_database):
    url, engine = scratch_database
    alembic(url, "upgrade", "head")

    with Session(bind=engine) as db:
        for number, tier in enumerate(TicketTier):
            user = User(
                name=f"Pessoa {number}",
                email=f"p{number}@example.com",
                password_hash="x",
                is_verified=True,
            )
            db.add(user)
            db.flush()
            db.add(
                Ticket(
                    user_id=user.id,
                    transaction_reference=f"REF-{number}",
                    ticket_tier=tier,
                    payment_status=PaymentStatus.PAID,
                    paid_at=datetime.now(UTC),
                )
            )
        db.commit()
        assert db.query(Ticket).count() == len(TicketTier) == 5


def test_the_ticket_check_lists_exactly_the_modalities_of_the_enum(
    scratch_database,
):
    url, engine = scratch_database
    alembic(url, "upgrade", "head")

    with engine.connect() as conn:
        definition = conn.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint"
                " WHERE conname = 'ck_tickets_ticket_tier'"
            )
        ).scalar_one()

    assert set(re.findall(r"'([a-z_]+)'", definition)) == {t.value for t in TicketTier}


def test_a_modality_outside_the_enum_is_refused(scratch_database):
    url, engine = scratch_database
    alembic(url, "upgrade", "head")

    with Session(bind=engine) as db:
        user = User(name="Ana", email="a@example.com", password_hash="x")
        db.add(user)
        db.flush()
        with pytest.raises(Exception, match="ck_tickets_ticket_tier"):
            db.execute(
                text(
                    "INSERT INTO tickets (user_id, transaction_reference, ticket_tier,"
                    " payment_status) VALUES (:u, 'R', 'vip', :paid)"
                ),
                {"u": user.id, "paid": PaymentStatus.PAID.value},
            )


def test_the_outbox_gets_its_text_body_column(scratch_database):
    url, engine = scratch_database
    alembic(url, "upgrade", "head")

    with engine.connect() as conn:
        columns = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns"
                    " WHERE table_name = 'email_outbox'"
                )
            )
        }
    assert "text_body" in columns
