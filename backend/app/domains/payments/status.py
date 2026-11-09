"""Read, only, how the payments are doing (for the monitoring).

    python -m app.domains.payments.status

Prints ``key=value`` lines: ``pending`` (payments waiting), ``stuck_pending_seconds``
(how long past its deadline the oldest waiting payment is, 0 if none is past it) and
``refund_due`` (payments that arrived and wait to be paid back). A payment is settled
by the provider's webhook, by the person's page, by their account page and by the
sweep, so one that is still ``pending`` long after its deadline means all of them are
failing: ``scripts/export-metrics.sh`` turns the number into a metric and
``monitoring/alerts.yml`` into an alert. Nothing is changed or printed about a person.
"""

from datetime import UTC, datetime

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.domains.payments.models import Transaction, TransactionStatus


def payment_status(db, now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    pending, oldest_deadline = db.execute(
        select(func.count(), func.min(Transaction.expires_at)).where(
            Transaction.status == TransactionStatus.PENDING
        )
    ).one()
    refund_due = db.scalar(
        select(func.count()).where(Transaction.status == TransactionStatus.REFUND_DUE)
    )
    stuck = 0
    if oldest_deadline is not None:
        if oldest_deadline.tzinfo is None:
            oldest_deadline = oldest_deadline.replace(tzinfo=UTC)
        stuck = max(0, int((now - oldest_deadline).total_seconds()))
    return {
        "pending": int(pending or 0),
        "stuck_pending_seconds": stuck,
        "refund_due": int(refund_due or 0),
    }


def main() -> None:
    with SessionLocal() as db:
        values = payment_status(db)
    for key, value in values.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
