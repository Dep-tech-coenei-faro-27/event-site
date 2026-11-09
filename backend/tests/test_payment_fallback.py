"""The safety net for a webhook that never comes: the sweep and the account page."""

import asyncio
import os
import threading
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.email.models import EmailOutbox
from app.core.email.templates import TICKET_EMAIL_SUBJECT
from app.domains.payments import service, stream
from app.domains.payments.events import events
from app.domains.payments.gateway import (
    PaymentGatewayError,
    get_mbway_gateway,
    get_mbway_gateway_or_none,
)
from app.domains.payments.models import Transaction, TransactionStatus
from app.domains.tickets.models import Ticket
from app.main import app
from tests.helpers import INITIATE_URL, authenticate, seed_ticket_tiers
from tests.test_payments import INITIATE, FakeGateway

pytestmark = pytest.mark.usefixtures("email_sender")

ME = "/api/users/me"


@pytest.fixture
def gateway(monkeypatch):
    fake = FakeGateway()
    app.dependency_overrides[get_mbway_gateway] = lambda: fake
    app.dependency_overrides[get_mbway_gateway_or_none] = lambda: fake
    monkeypatch.setattr(stream, "get_mbway_gateway", lambda: fake)
    yield fake
    app.dependency_overrides.pop(get_mbway_gateway, None)
    app.dependency_overrides.pop(get_mbway_gateway_or_none, None)


@pytest.fixture(autouse=True)
def the_stream_uses_the_test_database(monkeypatch, test_engine):
    monkeypatch.setattr(stream, "SessionLocal", sessionmaker(bind=test_engine))
    monkeypatch.setattr(settings, "PAYMENT_SWEEP_MIN_AGE_SECONDS", 0)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER_MIN_INTERVAL_SECONDS", 0)
    yield
    assert events.listening() == []


def start_payment(auth_client, email_sender, db_session) -> str:
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    response = auth_client.post(INITIATE_URL, json=INITIATE)
    assert response.status_code == 201
    return response.json()["reference"]


def status_of(db_session, reference) -> TransactionStatus:
    db_session.expire_all()
    return db_session.scalar(
        select(Transaction.status).where(Transaction.reference == reference)
    )


# --- the sweep ---------------------------------------------------------------------


def test_the_sweep_confirms_a_paid_payment_nobody_is_waiting_for(
    auth_client, email_sender, db_session, gateway
):
    """The webhook never came and the page was closed: the ticket still arrives."""
    reference = start_payment(auth_client, email_sender, db_session)
    gateway.status = TransactionStatus.CONFIRMED

    asked = asyncio.run(stream.sweep_once())

    assert asked == 1
    assert status_of(db_session, reference) is TransactionStatus.CONFIRMED
    assert db_session.scalar(select(Ticket).limit(1)) is not None
    assert any(m["subject"] for m in email_sender.sent)  # the ticket email


def test_the_sweep_frees_the_seat_of_a_payment_the_provider_ended(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)
    gateway.status = TransactionStatus.FAILED

    asyncio.run(stream.sweep_once())

    assert status_of(db_session, reference) is TransactionStatus.FAILED


def test_the_sweep_leaves_a_payment_the_provider_still_waits_for(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)

    asyncio.run(stream.sweep_once())

    assert status_of(db_session, reference) is TransactionStatus.PENDING
    assert len(gateway.status_calls) == 1


def test_the_sweep_does_not_ask_about_a_payment_that_is_too_young(
    auth_client, email_sender, db_session, gateway, monkeypatch
):
    start_payment(auth_client, email_sender, db_session)
    monkeypatch.setattr(settings, "PAYMENT_SWEEP_MIN_AGE_SECONDS", 3600)

    assert asyncio.run(stream.sweep_once()) == 0
    assert gateway.status_calls == []


def test_one_payment_that_cannot_be_read_does_not_stop_the_others(
    auth_client, email_sender, db_session, gateway
):
    first = start_payment(auth_client, email_sender, db_session)
    gateway.status_error = PaymentGatewayError("the provider is down")

    assert asyncio.run(stream.sweep_once()) == 1  # asked, failed, nothing raised

    gateway.status_error = None
    gateway.status = TransactionStatus.CONFIRMED
    asyncio.run(stream.sweep_once())
    assert status_of(db_session, first) is TransactionStatus.CONFIRMED


def test_the_sweep_does_nothing_while_payments_are_off(
    auth_client, email_sender, db_session, gateway, monkeypatch
):
    start_payment(auth_client, email_sender, db_session)

    def off():
        raise HTTPException(status_code=503, detail="Payments are currently disabled.")

    monkeypatch.setattr(stream, "get_mbway_gateway", off)

    assert asyncio.run(stream.sweep_once()) == 0
    assert gateway.status_calls == []


def test_the_sweep_can_be_turned_off(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_SWEEP_SECONDS", 0)

    asyncio.run(asyncio.wait_for(stream.sweep_forever(), 1))  # returns at once


def test_the_references_to_sweep_are_the_oldest_pending_ones_up_to_the_batch(
    db_session,
):
    from app.core.security import hash_password
    from app.domains.payments.models import TicketTier
    from app.domains.users.models import User

    tiers = seed_ticket_tiers(db_session)
    user = User(name="Ana", email="ana@example.com", password_hash=hash_password("x"))
    db_session.add(user)
    db_session.flush()
    now = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
    states = [
        ("ENEI-OLD0000001", TransactionStatus.PENDING, 50),
        ("ENEI-OLD0000002", TransactionStatus.PENDING, 40),
        ("ENEI-NEW0000003", TransactionStatus.PENDING, 5),  # too young
        ("ENEI-PAID000004", TransactionStatus.CONFIRMED, 60),  # not pending
        ("ENEI-OLD0000005", TransactionStatus.PENDING, 30),
    ]
    for reference, status, minutes in states:
        db_session.add(
            Transaction(
                reference=reference,
                user_id=user.id,
                ticket_tier_id=tiers[TicketTier.GERAL].id,
                amount_cents=5000,
                status=status,
                phone="912345678",
                provider="fake",
                expires_at=now,
                created_at=now - timedelta(minutes=minutes),
            )
        )
    db_session.commit()

    found = service.pending_references_to_sweep(
        db_session, min_age_seconds=600, limit=2, now=now
    )

    assert found == ["ENEI-OLD0000001", "ENEI-OLD0000002"]


# --- the account page -----------------------------------------------------------------


def test_opening_the_account_settles_the_payment_the_person_left_behind(
    auth_client, email_sender, db_session, gateway
):
    start_payment(auth_client, email_sender, db_session)
    gateway.status = TransactionStatus.CONFIRMED

    body = auth_client.get(ME).json()

    assert body["qr_code"] is not None
    assert body["pending_payment"] is None


def test_the_account_still_opens_when_the_provider_is_down(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)
    gateway.status_error = PaymentGatewayError("the provider is down")

    response = auth_client.get(ME)

    assert response.status_code == 200
    assert response.json()["pending_payment"]["reference"] == reference


def test_the_account_still_opens_while_payments_are_off(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)
    app.dependency_overrides[get_mbway_gateway_or_none] = lambda: None

    response = auth_client.get(ME)

    assert response.status_code == 200
    assert response.json()["pending_payment"]["reference"] == reference
    assert gateway.status_calls == []


def test_the_account_asks_the_provider_only_when_a_payment_is_waiting(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)

    assert auth_client.get(ME).status_code == 200
    assert gateway.status_calls == []


# --- the monitoring ----------------------------------------------------------------


def test_the_status_says_how_long_a_payment_has_been_stuck_past_its_deadline(
    auth_client, email_sender, db_session, gateway
):
    from app.domains.payments.status import payment_status

    reference = start_payment(auth_client, email_sender, db_session)
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == reference)
    )
    deadline = transaction.expires_at

    assert payment_status(db_session, now=deadline - timedelta(seconds=30)) == {
        "pending": 1,
        "stuck_pending_seconds": 0,  # still inside its time: not stuck
        "refund_due": 0,
    }
    stuck = payment_status(db_session, now=deadline + timedelta(seconds=700))
    assert stuck["pending"] == 1 and stuck["stuck_pending_seconds"] == 700


def test_the_status_counts_the_payments_waiting_to_be_paid_back(
    auth_client, email_sender, db_session, gateway
):
    from app.domains.payments.status import payment_status

    reference = start_payment(auth_client, email_sender, db_session)
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == reference)
    )
    transaction.status = TransactionStatus.REFUND_DUE
    db_session.commit()

    values = payment_status(db_session)

    assert values == {"pending": 0, "stuck_pending_seconds": 0, "refund_due": 1}


def test_the_status_command_prints_key_value_lines_the_metrics_script_reads(
    monkeypatch, db_session, capsys
):
    from app.domains.payments import status as module

    seed_ticket_tiers(db_session)
    monkeypatch.setattr(module, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    module.main()

    assert capsys.readouterr().out.splitlines() == [
        "pending=0",
        "stuck_pending_seconds=0",
        "refund_due=0",
    ]


def test_the_sweep_and_the_account_leave_a_payment_made_with_another_provider(
    auth_client, email_sender, db_session, gateway
):
    """A leftover of a test run or an earlier provider must not be asked about."""
    reference = start_payment(auth_client, email_sender, db_session)
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == reference)
    )
    transaction.provider = "ifthenpay"
    db_session.commit()
    gateway.status = TransactionStatus.CONFIRMED

    assert asyncio.run(stream.sweep_once()) == 0
    assert auth_client.get(ME).status_code == 200

    assert gateway.status_calls == []
    assert status_of(db_session, reference) is TransactionStatus.PENDING


requires_postgres = pytest.mark.skipif(
    not (os.environ.get("TEST_DATABASE_URL") or "").startswith("postgresql"),
    reason="row-level locking requires PostgreSQL",
)


@requires_postgres
def test_the_sweep_the_account_and_the_webhook_at_once_issue_one_ticket(
    auth_client, email_sender, db_session, gateway, test_engine
):
    """The three ways of confirming a payment can land on the same payment together."""
    reference = start_payment(auth_client, email_sender, db_session)
    gateway.status = TransactionStatus.CONFIRMED
    errors: list[BaseException] = []
    start = threading.Barrier(6)

    def confirm(via_webhook: bool) -> None:
        try:
            with Session(bind=test_engine) as session:
                transaction = session.scalar(
                    select(Transaction).where(Transaction.reference == reference)
                )
                start.wait(timeout=10)
                if via_webhook:
                    service.confirm_transaction(session, transaction)
                else:
                    service._sync_provider_status(session, transaction, gateway)
        except BaseException as exc:  # surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=confirm, args=(n % 3 == 0,)) for n in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert errors == []
    assert status_of(db_session, reference) is TransactionStatus.CONFIRMED
    with Session(bind=test_engine) as session:
        assert session.scalar(select(func.count()).select_from(Ticket)) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(EmailOutbox)
                .where(EmailOutbox.subject == TICKET_EMAIL_SUBJECT)
            )
            == 1
        )
