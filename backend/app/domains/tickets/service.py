from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.qr import generate_qr_payload
from app.domains.tickets.models import PaymentStatus, Ticket


class TicketNotFoundError(Exception):
    """Raised when the ticket or transaction does not exist."""


def get_ticket_for_user(db: Session, user_id: int) -> Ticket | None:
    """The ticket issued to a user, if any.

    A user can only have one active ticket today, so the oldest row wins.
    """
    return db.scalar(
        select(Ticket).where(Ticket.user_id == user_id).order_by(Ticket.id).limit(1)
    )


class PaymentNotConfirmedError(Exception):
    """Raised when attempting to generate a QR code for an unpaid ticket."""


def confirm_ticket_payment_and_issue_qr(db: Session, ticket_id: int) -> Ticket:
    """Mark a ticket as PAID (if not already) and generate its unique QR payload.

    Idempotent: if the ticket already has a ``qr_payload`` and is ``PAID``,
    returns the existing ticket without overwriting the QR code.
    """
    ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update())
    if ticket is None:
        raise TicketNotFoundError(f"Ticket {ticket_id} not found")

    if ticket.payment_status == PaymentStatus.CANCELLED:
        raise PaymentNotConfirmedError("Cannot confirm a cancelled ticket")

    if ticket.payment_status == PaymentStatus.PAID and ticket.qr_payload:
        return ticket

    ticket.payment_status = PaymentStatus.PAID
    ticket.paid_at = datetime.now(UTC)
    ticket.qr_payload = generate_qr_payload(ticket.id)

    db.commit()
    db.refresh(ticket)
    return ticket


def issue_ticket_for_paid_transaction(
    db: Session, *, user_id: int, transaction_reference: str
) -> Ticket:
    """Issue the ticket for a paid transaction and sign its unique QR payload.

    Idempotent by ``transaction_reference``: re-issuing for the same reference
    returns the existing ticket and never overwrites an already signed QR, so a
    repeated payment callback cannot duplicate a ticket.
    """
    ticket = db.scalar(
        select(Ticket)
        .where(Ticket.transaction_reference == transaction_reference)
        .with_for_update()
    )
    if ticket is None:
        ticket = Ticket(
            user_id=user_id,
            transaction_reference=transaction_reference,
            payment_status=PaymentStatus.PAID,
            paid_at=datetime.now(UTC),
        )
        db.add(ticket)
        db.flush()
    elif ticket.payment_status == PaymentStatus.CANCELLED:
        raise PaymentNotConfirmedError("Cannot confirm a cancelled ticket")
    elif ticket.payment_status == PaymentStatus.PAID and ticket.qr_payload:
        return ticket

    ticket.payment_status = PaymentStatus.PAID
    ticket.paid_at = ticket.paid_at or datetime.now(UTC)
    ticket.qr_payload = generate_qr_payload(ticket.id)
    db.commit()
    db.refresh(ticket)
    return ticket


def issue_qr_for_confirmed_ticket(db: Session, ticket: Ticket) -> Ticket:
    """Generate and persist a QR payload for an already confirmed ticket."""
    if ticket.payment_status != PaymentStatus.PAID:
        raise PaymentNotConfirmedError(
            "QR payload can only be generated after payment confirmation"
        )
    if not ticket.qr_payload:
        ticket.qr_payload = generate_qr_payload(ticket.id)
        db.commit()
        db.refresh(ticket)
    return ticket
