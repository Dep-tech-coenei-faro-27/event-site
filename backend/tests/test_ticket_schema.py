from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domains.payments.models import (
    TicketTier,
    TicketTierPrice,
    Transaction,
    TransactionStatus,
)
from app.domains.tickets.models import PaymentStatus, Ticket
from app.domains.users.models import User
from tests.helpers import authenticate


def test_ticket_price_can_be_null_while_the_ticket_office_is_closed(db_session):
    ticket = TicketTierPrice(
        tier=TicketTier.ACESSO,
        name="Apenas acesso",
        price_cents=None,
        is_student=True,
    )
    db_session.add(ticket)
    db_session.commit()

    stored = db_session.scalar(
        select(TicketTierPrice).where(TicketTierPrice.tier == TicketTier.ACESSO)
    )

    assert stored is not None
    assert stored.price_cents is None


def test_ticket_price_cannot_be_zero(db_session):
    db_session.add(
        TicketTierPrice(
            tier=TicketTier.GERAL,
            name="Passe geral",
            price_cents=0,
            is_student=False,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_ticket_stores_tier_price_and_inventory(db_session):
    ticket = TicketTierPrice(
        tier=TicketTier.COMPLETO,
        name="Experiência completa",
        price_cents=4500,
        is_student=True,
        inventory_limit=120,
    )
    db_session.add(ticket)
    db_session.commit()

    stored = db_session.scalar(
        select(TicketTierPrice).where(TicketTierPrice.tier == TicketTier.COMPLETO)
    )

    assert stored is not None
    assert stored.price_cents == 4500
    assert stored.is_student is True
    assert stored.inventory_limit == 120
    assert stored.tier is TicketTier.COMPLETO


def _make_user(db_session) -> User:
    user = User(
        name="Aluno Teste",
        email="aluno@ualg.pt",
        password_hash="hashed_pw",
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_a_user_cannot_hold_two_active_tickets(db_session):
    user = _make_user(db_session)
    db_session.add(Ticket(user_id=user.id, transaction_reference="ENEI-ACTIVE0001"))
    db_session.commit()

    db_session.add(Ticket(user_id=user.id, transaction_reference="ENEI-ACTIVE0002"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cancelling_a_ticket_frees_the_user_slot(db_session):
    user = _make_user(db_session)
    db_session.add(
        Ticket(
            user_id=user.id,
            transaction_reference="ENEI-CANCEL0001",
            payment_status=PaymentStatus.CANCELLED,
        )
    )
    db_session.commit()

    db_session.add(Ticket(user_id=user.id, transaction_reference="ENEI-ACTIVE0003"))
    db_session.commit()

    active = db_session.scalar(
        select(Ticket).where(Ticket.transaction_reference == "ENEI-ACTIVE0003")
    )
    assert active is not None
    assert active.payment_status is PaymentStatus.PENDING


def test_transaction_records_user_ticket_amount_and_status(
    auth_client, email_sender, db_session
):
    user = authenticate(auth_client, email_sender, db_session)
    ticket = TicketTierPrice(
        tier=TicketTier.GERAL,
        name="Passe geral",
        price_cents=5000,
        is_student=False,
    )
    db_session.add(ticket)
    db_session.commit()

    transaction = Transaction(
        reference="ENEI-ABCDEFGHIJ",
        user_id=user.id,
        ticket_tier_id=ticket.id,
        amount_cents=5000,
        quantity=1,
        status=TransactionStatus.PENDING,
        phone="912345678",
        provider="simulated",
        expires_at=datetime.now(UTC) + timedelta(minutes=4),
    )
    db_session.add(transaction)
    db_session.commit()

    stored = db_session.scalar(
        select(Transaction).where(Transaction.reference == "ENEI-ABCDEFGHIJ")
    )

    assert stored is not None
    assert stored.user_id == user.id
    assert stored.ticket_tier_id == ticket.id
    assert stored.amount_cents == 5000
    assert stored.status is TransactionStatus.PENDING
    assert stored.created_at is not None
