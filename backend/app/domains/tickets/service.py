from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.qr import generate_qr_payload
from app.domains.tickets.models import PaymentStatus, Ticket


class TicketNotFoundError(Exception):
    """Raised when the ticket or transaction does not exist."""


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
