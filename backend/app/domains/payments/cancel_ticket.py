"""Take a ticket away from a person without giving any money back.

    python -m app.domains.payments.cancel_ticket ENEI-0123456789
    python -m app.domains.payments.cancel_ticket ENEI-0123456789 --dry-run

A ticket that was paid and given is not refunded: a person who asks (by email) may get
part of the money back, by hand in the Stripe dashboard, and then the ticket is taken
away with this command. It cancels the ticket of THIS payment, frees its seat and
makes the payment ``refunded`` (it is no longer a valid sale). **It never calls
Stripe**: the money is dealt with separately, and a full refund of a payment that
did not need one is ``python -m app.domains.payments.refund``. A ticket of the same
person from another payment is never touched. Repeating it is safe. Only the reference
is printed, never anything about the person.
"""

import argparse
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.domains.payments.models import Transaction, TransactionStatus
from app.domains.payments.service import cancel_ticket
from app.domains.tickets.models import PaymentStatus, Ticket


class NothingToCancelError(Exception):
    """The reference has no active ticket to take away."""


def take_ticket_away(db: Session, reference: str, *, dry_run: bool = False) -> str:
    """Cancel the active ticket of a payment. Returns what happened, in words."""
    transaction = db.scalar(
        select(Transaction).where(Transaction.reference == reference)
    )
    if transaction is None:
        raise NothingToCancelError("Unknown transaction reference")
    ticket = db.scalar(select(Ticket).where(Ticket.transaction_reference == reference))
    if ticket is not None and ticket.payment_status is PaymentStatus.CANCELLED:
        return "ticket already cancelled, nothing changed"
    if ticket is None or transaction.status is not TransactionStatus.CONFIRMED:
        raise NothingToCancelError(
            f"A {transaction.status.value} payment has no ticket to take away"
        )
    if dry_run:
        return "would cancel the ticket and free the seat (nothing was changed)"
    cancel_ticket(db, ticket.id)
    return "ticket cancelled, seat freed, payment now refunded; Stripe was not touched"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.domains.payments.cancel_ticket"
    )
    parser.add_argument("reference", help="the payment, e.g. ENEI-0123456789")
    parser.add_argument(
        "--dry-run", action="store_true", help="say what would happen, change nothing"
    )
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        try:
            outcome = take_ticket_away(db, args.reference, dry_run=args.dry_run)
        except NothingToCancelError as error:
            db.rollback()
            print(f"{args.reference}: NOT cancelled: {error}")
            return 1
    print(f"{args.reference}: {outcome}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
