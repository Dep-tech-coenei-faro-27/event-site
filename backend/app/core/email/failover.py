"""A second SMTP server for when the first one stops sending.

The free plans of email providers allow a few hundred emails a day, fewer than the
first day of ticket sales needs. ``FailoverEmailSender`` sends through the primary
transport and moves to the fallback when the primary refuses for its daily quota
(or reaches ``daily_limit``), until midnight UTC, or when the primary server fails
for one email. A refused recipient never goes to the fallback.

The count of each day is kept in ``email_transport_usage`` so that every worker
(one per backend process, plus the command) sees the same quota.
"""

import logging
from collections.abc import Callable
from datetime import UTC, date, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.email.base import EmailDeliveryError, EmailSender, mask_email
from app.core.email.models import EmailTransportUsage

logger = logging.getLogger(__name__)

PRIMARY = "primary"
FALLBACK = "fallback"


def _now() -> datetime:
    return datetime.now(UTC)


def _ensure_row(db: Session, transport: str, day: date) -> None:
    exists = db.scalar(
        select(EmailTransportUsage.sent).where(
            EmailTransportUsage.transport == transport,
            EmailTransportUsage.day == day,
        )
    )
    if exists is not None:
        return
    db.add(EmailTransportUsage(transport=transport, day=day, sent=0))
    try:
        db.commit()
    except IntegrityError:
        # Another worker created it at the same time.
        db.rollback()


def _add(db: Session, transport: str, day: date, delta: int) -> None:
    _ensure_row(db, transport, day)
    db.execute(
        update(EmailTransportUsage)
        .where(
            EmailTransportUsage.transport == transport,
            EmailTransportUsage.day == day,
        )
        .values(sent=EmailTransportUsage.sent + delta)
        .execution_options(synchronize_session=False)
    )
    db.commit()


def reserve_primary(db: Session, day: date, daily_limit: int) -> bool:
    """Take one send of the primary's day, or say that the day is used up.

    The check and the increment are one ``UPDATE``, so two workers can never both
    take the last send of the day.
    """
    _ensure_row(db, PRIMARY, day)
    conditions = [
        EmailTransportUsage.transport == PRIMARY,
        EmailTransportUsage.day == day,
        EmailTransportUsage.exhausted_at.is_(None),
    ]
    if daily_limit:
        conditions.append(EmailTransportUsage.sent < daily_limit)
    result = db.execute(
        update(EmailTransportUsage)
        .where(*conditions)
        .values(sent=EmailTransportUsage.sent + 1)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount == 1


def mark_primary_exhausted(db: Session, day: date, when: datetime) -> None:
    _ensure_row(db, PRIMARY, day)
    db.execute(
        update(EmailTransportUsage)
        .where(
            EmailTransportUsage.transport == PRIMARY,
            EmailTransportUsage.day == day,
            EmailTransportUsage.exhausted_at.is_(None),
        )
        .values(exhausted_at=when)
        .execution_options(synchronize_session=False)
    )
    db.commit()


def usage_on(db: Session, day: date) -> dict[str, object]:
    """What each transport sent on ``day`` and whether the primary ran out."""
    rows = {
        row.transport: row
        for row in db.scalars(
            select(EmailTransportUsage).where(EmailTransportUsage.day == day)
        )
    }
    primary = rows.get(PRIMARY)
    fallback = rows.get(FALLBACK)
    return {
        "primary_sent_today": primary.sent if primary else 0,
        "primary_exhausted_today": bool(primary and primary.exhausted_at),
        "fallback_sent_today": fallback.sent if fallback else 0,
    }


class FailoverEmailSender(EmailSender):
    """Sends through ``primary`` and, when it cannot, through ``fallback``."""

    def __init__(
        self,
        primary: EmailSender,
        fallback: EmailSender,
        session_factory: Callable[[], Session],
        *,
        daily_limit: int = 0,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self._session_factory = session_factory
        self._daily_limit = daily_limit
        self._clock = clock
        self._warned_on: date | None = None

    def send_html(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        inline_images: dict[str, bytes] | None = None,
        text_body: str | None = None,
    ) -> None:
        extras: dict[str, object] = {}
        if inline_images:
            extras["inline_images"] = inline_images
        if text_body:
            extras["text_body"] = text_body
        now = self._clock()
        day = now.astimezone(UTC).date()
        with self._session_factory() as db:
            reserved = reserve_primary(db, day, self._daily_limit)
        if reserved:
            try:
                self.primary.send_html(to_email, subject, html_body, **extras)
                return
            except Exception as exc:
                kind = getattr(exc, "kind", EmailDeliveryError.SERVER)
                with self._session_factory() as db:
                    _add(db, PRIMARY, day, -1)
                    if kind == EmailDeliveryError.LIMIT:
                        mark_primary_exhausted(db, day, now)
                if kind == EmailDeliveryError.RECIPIENT:
                    raise
                if kind == EmailDeliveryError.LIMIT:
                    self._warn_day(day, "the provider refused for its daily quota")
                else:
                    logger.warning(
                        "Primary SMTP failed for the email to %s (%s); "
                        "sending it through the fallback SMTP",
                        mask_email(to_email),
                        type(exc).__name__,
                    )
        else:
            self._warn_day(day, "its daily limit was reached")

        self.fallback.send_html(to_email, subject, html_body, **extras)
        with self._session_factory() as db:
            _add(db, FALLBACK, day, 1)

    def _warn_day(self, day: date, reason: str) -> None:
        """One warning per day and process, not one per email."""
        if self._warned_on == day:
            return
        self._warned_on = day
        logger.warning(
            "Primary SMTP is out for today (%s): the fallback SMTP sends "
            "until midnight UTC",
            reason,
        )
