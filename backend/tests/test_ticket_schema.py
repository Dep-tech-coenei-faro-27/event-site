from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.domains.payments.models import (
    Ticket,
    TicketTier,
    Transaction,
    TransactionStatus,
)
from tests.helpers import authenticate


def test_ticket_stores_tier_price_and_inventory(db_session):
    ticket = Ticket(
        tier=TicketTier.COMPLETO,
        name="Experiência completa",
        price_cents=4500,
        is_student=True,
        inventory_limit=120,
    )
    db_session.add(ticket)
    db_session.commit()

    stored = db_session.scalar(select(Ticket).where(Ticket.tier == TicketTier.COMPLETO))

    assert stored is not None
    assert stored.price_cents == 4500
    assert stored.is_student is True
    assert stored.inventory_limit == 120
    assert stored.tier is TicketTier.COMPLETO


def test_transaction_records_user_ticket_amount_and_status(
    auth_client, email_sender, db_session
):
    user = authenticate(auth_client, email_sender, db_session)
    ticket = Ticket(
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
        ticket_id=ticket.id,
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
    assert stored.ticket_id == ticket.id
    assert stored.amount_cents == 5000
    assert stored.status is TransactionStatus.PENDING
    assert stored.created_at is not None
