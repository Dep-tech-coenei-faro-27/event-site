"""Taking a ticket away by hand, without refunding (the policy once it is given)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.domains.payments import cancel_ticket as cli
from app.domains.payments.models import TicketTier, Transaction, TransactionStatus
from app.domains.payments.service import confirm_transaction
from app.domains.tickets.models import PaymentStatus, Ticket
from tests.helpers import authenticate, seed_ticket_tiers


@pytest.fixture
def shop(auth_client, email_sender, db_session):
    user = authenticate(auth_client, email_sender, db_session)
    return user, seed_ticket_tiers(db_session)


def make_payment(db_session, shop, reference, *, status=TransactionStatus.PENDING):
    user, tiers = shop
    transaction = Transaction(
        reference=reference,
        user_id=user.id,
        ticket_tier_id=tiers[TicketTier.GERAL].id,
        amount_cents=2500,
        quantity=1,
        phone="912345678",
        provider="stripe",
        provider_reference="pi_" + reference[-6:],
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        status=status,
    )
    db_session.add(transaction)
    db_session.commit()
    return transaction


def paid_with_ticket(db_session, shop, reference):
    transaction = make_payment(db_session, shop, reference)
    confirm_transaction(db_session, transaction)
    db_session.refresh(transaction)
    assert transaction.status is TransactionStatus.CONFIRMED
    return transaction


def status_of(db_session, reference):
    db_session.expire_all()
    return db_session.scalar(
        select(Transaction.status).where(Transaction.reference == reference)
    )


def ticket_status(db_session, reference):
    db_session.expire_all()
    return db_session.scalar(
        select(Ticket.payment_status).where(Ticket.transaction_reference == reference)
    )


@pytest.fixture
def command(monkeypatch, test_engine):
    monkeypatch.setattr(
        cli,
        "SessionLocal",
        sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False),
    )
    return cli.main


def test_the_command_takes_the_ticket_away_and_closes_the_payment(
    db_session, shop, command, capsys
):
    paid_with_ticket(db_session, shop, "ENEI-0000000001")

    assert command(["ENEI-0000000001"]) == 0

    out = capsys.readouterr().out
    assert "ENEI-0000000001: ticket cancelled, seat freed" in out
    assert "Stripe was not touched" in out
    assert status_of(db_session, "ENEI-0000000001") is TransactionStatus.REFUNDED
    assert ticket_status(db_session, "ENEI-0000000001") is PaymentStatus.CANCELLED


def test_the_command_never_calls_stripe(db_session, shop, command, monkeypatch):
    paid_with_ticket(db_session, shop, "ENEI-0000000001")

    def forbidden(*args, **kwargs):
        raise AssertionError("the command must not ask for a payment gateway")

    monkeypatch.setattr("app.domains.payments.gateway.get_mbway_gateway", forbidden)

    assert command(["ENEI-0000000001"]) == 0
    assert not hasattr(cli, "get_mbway_gateway")


def test_a_dry_run_changes_nothing(db_session, shop, command, capsys):
    paid_with_ticket(db_session, shop, "ENEI-0000000001")

    assert command(["ENEI-0000000001", "--dry-run"]) == 0

    assert "would cancel" in capsys.readouterr().out
    assert status_of(db_session, "ENEI-0000000001") is TransactionStatus.CONFIRMED
    assert ticket_status(db_session, "ENEI-0000000001") is not PaymentStatus.CANCELLED


def test_repeating_the_command_is_safe(db_session, shop, command, capsys):
    paid_with_ticket(db_session, shop, "ENEI-0000000001")

    assert command(["ENEI-0000000001"]) == 0
    assert command(["ENEI-0000000001"]) == 0

    assert "already cancelled" in capsys.readouterr().out
    assert status_of(db_session, "ENEI-0000000001") is TransactionStatus.REFUNDED


def test_the_seat_is_free_again_for_the_person(db_session, shop, command):
    paid_with_ticket(db_session, shop, "ENEI-0000000001")
    assert command(["ENEI-0000000001"]) == 0

    # The unique index lets the person hold a new active ticket.
    again = paid_with_ticket(db_session, shop, "ENEI-0000000002")

    assert again.status is TransactionStatus.CONFIRMED


def test_the_ticket_of_another_payment_of_the_person_is_never_touched(
    db_session, shop, command
):
    paid_with_ticket(db_session, shop, "ENEI-0000000001")
    assert command(["ENEI-0000000001"]) == 0
    paid_with_ticket(db_session, shop, "ENEI-0000000002")

    assert command(["ENEI-0000000001"]) == 0  # repeating the old one

    assert status_of(db_session, "ENEI-0000000002") is TransactionStatus.CONFIRMED
    assert ticket_status(db_session, "ENEI-0000000002") is not PaymentStatus.CANCELLED


def test_an_unknown_reference_is_refused(db_session, shop, command, capsys):
    assert command(["ENEI-9999999999"]) == 1

    assert "NOT cancelled: Unknown transaction reference" in capsys.readouterr().out


@pytest.mark.parametrize(
    "status",
    [
        TransactionStatus.PENDING,
        TransactionStatus.FAILED,
        TransactionStatus.EXPIRED,
        TransactionStatus.REFUND_DUE,
    ],
)
def test_a_payment_without_a_ticket_is_refused(
    db_session, shop, command, capsys, status
):
    make_payment(db_session, shop, "ENEI-0000000001", status=status)

    assert command(["ENEI-0000000001"]) == 1

    assert "has no ticket to take away" in capsys.readouterr().out
    assert status_of(db_session, "ENEI-0000000001") is status


def test_the_output_never_has_anything_about_the_person(
    db_session, shop, command, capsys
):
    user, _ = shop
    paid_with_ticket(db_session, shop, "ENEI-0000000001")

    command(["ENEI-0000000001"])

    out = capsys.readouterr().out
    assert user.email not in out
    assert user.name not in out
    assert "912345678" not in out
