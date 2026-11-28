"""Ask by email the students who bought a ticket for the size of their shirt.

    python -m app.domains.payments.ask_shirt_size            # only counts
    python -m app.domains.payments.ask_shirt_size --send     # queues the emails

The students who bought before the size was asked at checkout have a paid ticket of
a student modality and no size. Without ``--send`` nothing is queued: it prints how
many they are. With it, each one gets one email, sent by the email queue like every
other email (the dedupe key ``shirt:<ticket id>`` stops a second one for the same
ticket while the first is still in the queue). Only the count is printed, never a
name or an address. To remind whoever still has no size, run it again: the queue
forgets sent emails after a week, so a run a week later asks again, and one within
the week asks nobody twice.
"""

import argparse
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.email.models import EmailOutbox
from app.core.email.outbox import enqueue_email
from app.core.email.templates import SHIRT_SIZE_SUBJECT, build_shirt_size_email
from app.db.session import SessionLocal
from app.domains.payments.models import TicketTierPrice, Transaction
from app.domains.tickets.models import PaymentStatus, Ticket
from app.domains.users.models import User


def tickets_without_size(db: Session) -> list[tuple[Ticket, User]]:
    """Paid tickets of a student modality that have no shirt size, with their holder."""
    return list(
        db.execute(
            select(Ticket, User)
            .join(User, User.id == Ticket.user_id)
            .join(Transaction, Transaction.reference == Ticket.transaction_reference)
            .join(TicketTierPrice, TicketTierPrice.id == Transaction.ticket_tier_id)
            .where(
                Ticket.payment_status == PaymentStatus.PAID,
                TicketTierPrice.is_student.is_(True),
                Ticket.shirt_size.is_(None),
            )
            .order_by(Ticket.id)
        ).all()
    )


def queue_shirt_size_emails(db: Session) -> int:
    """Queue the email for every student without a size; returns how many are new.

    A repeated call queues nobody twice while the first email is still in the queue.
    """
    already = set(
        db.scalars(
            select(EmailOutbox.dedupe_key).where(EmailOutbox.dedupe_key.like("shirt:%"))
        )
    )
    queued = 0
    for ticket, user in tickets_without_size(db):
        key = f"shirt:{ticket.id}"
        if key in already:
            continue
        html, text = build_shirt_size_email(user.name)
        enqueue_email(
            db, user.email, SHIRT_SIZE_SUBJECT, html, text_body=text, dedupe_key=key
        )
        queued += 1
    return queued


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.domains.payments.ask_shirt_size"
    )
    parser.add_argument(
        "--send", action="store_true", help="queue the emails (default: only count)"
    )
    args = parser.parse_args(argv)
    with SessionLocal() as db:
        waiting = len(tickets_without_size(db))
        if not args.send:
            print(
                f"{waiting} students have a paid ticket and no shirt size. "
                "Nothing queued; run again with --send to email them."
            )
            return 0
        queued = queue_shirt_size_emails(db)
    print(f"{queued} emails queued for the {waiting} students without a shirt size.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
