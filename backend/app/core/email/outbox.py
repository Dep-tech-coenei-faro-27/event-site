"""Durable email queue.

``OutboxEmailSender.send_html`` writes the email to the ``email_outbox`` table and
returns at once. A worker (a thread started with the app, or the command
``python -m app.core.email``) sends what is due and retries failures with a
growing delay, so an email survives a restart of the server or a mail provider
outage. Delivery is at least once: a crash between sending and recording can send
the same email again.
"""

import base64
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.email.base import EmailDeliveryError, EmailSender, mask_email
from app.core.email.models import EmailOutbox, EmailStatus

logger = logging.getLogger(__name__)

# Delay before the next attempt, indexed by how many attempts have failed so far.
RETRY_DELAYS_SECONDS = (30, 120, 600, 1800, 7200, 21600)
LEASE_SECONDS = 120
MAX_ERROR_LENGTH = 200


BATCH_SIZE = 20


@dataclass(frozen=True)
class DeliveryReport:
    claimed: int = 0
    sent: int = 0
    retried: int = 0
    failed: int = 0


def _now() -> datetime:
    return datetime.now(UTC)


def enqueue_email(
    db: Session,
    to_email: str,
    subject: str,
    html_body: str,
    *,
    inline_images: dict[str, bytes] | None = None,
    dedupe_key: str | None = None,
    now: datetime | None = None,
) -> EmailOutbox:
    """Store an email to be sent. A repeated ``dedupe_key`` returns the first one."""
    if dedupe_key is not None:
        existing = db.scalar(
            select(EmailOutbox).where(EmailOutbox.dedupe_key == dedupe_key)
        )
        if existing is not None:
            return existing

    when = now or _now()
    row = EmailOutbox(
        to_email=to_email,
        subject=subject[:255],
        html_body=html_body,
        inline_images=_encode_images(inline_images),
        dedupe_key=dedupe_key,
        status=EmailStatus.PENDING,
        attempts=0,
        next_attempt_at=when,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # Two requests queued the same dedupe_key at once: keep the first.
        db.rollback()
        existing = db.scalar(
            select(EmailOutbox).where(EmailOutbox.dedupe_key == dedupe_key)
        )
        if existing is None:
            raise
        return existing
    db.refresh(row)
    return row


def _encode_images(images: dict[str, bytes] | None) -> dict[str, str] | None:
    if not images:
        return None
    return {cid: base64.b64encode(png).decode("ascii") for cid, png in images.items()}


def _decode_images(images: dict[str, str] | None) -> dict[str, bytes] | None:
    if not images:
        return None
    return {cid: base64.b64decode(data) for cid, data in images.items()}


def _scrub(message: str, to_email: str) -> str:
    return message.replace(to_email, mask_email(to_email))[:MAX_ERROR_LENGTH]


def _claim_due(db: Session, now: datetime, limit: int) -> list[int]:
    """Lease the emails that are due so two workers never take the same one."""
    rows = db.scalars(
        select(EmailOutbox)
        .where(
            EmailOutbox.status == EmailStatus.PENDING,
            EmailOutbox.next_attempt_at <= now,
            or_(
                EmailOutbox.locked_until.is_(None),
                EmailOutbox.locked_until < now,
            ),
        )
        .order_by(EmailOutbox.next_attempt_at, EmailOutbox.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    ).all()
    for row in rows:
        row.locked_until = now + timedelta(seconds=LEASE_SECONDS)
    ids = [row.id for row in rows]
    db.commit()
    return ids


def deliver_due(
    db: Session,
    transport: EmailSender,
    *,
    now: datetime | None = None,
    limit: int = BATCH_SIZE,
    max_attempts: int = 10,
) -> DeliveryReport:
    """Send the emails that are due once, recording the outcome of each."""
    when = now or _now()
    sent = retried = failed = 0
    ids = _claim_due(db, when, limit)
    for email_id in ids:
        row = db.get(EmailOutbox, email_id)
        if row is None:
            continue
        to_email, subject, html_body = row.to_email, row.subject, row.html_body
        images = _decode_images(row.inline_images)
        try:
            if images:
                transport.send_html(to_email, subject, html_body, images)
            else:
                transport.send_html(to_email, subject, html_body)
        except Exception as exc:
            row.attempts += 1
            row.locked_until = None
            row.last_error = _scrub(f"{type(exc).__name__}: {exc}", to_email)
            if row.attempts >= max_attempts:
                row.status = EmailStatus.FAILED
                failed += 1
                logger.error(
                    "Email %s to %s gave up after %s attempts: %s",
                    row.id,
                    mask_email(to_email),
                    row.attempts,
                    row.last_error,
                )
            else:
                index = min(row.attempts - 1, len(RETRY_DELAYS_SECONDS) - 1)
                row.next_attempt_at = when + timedelta(
                    seconds=RETRY_DELAYS_SECONDS[index]
                )
                retried += 1
                logger.warning(
                    "Email %s to %s failed (attempt %s), will retry: %s",
                    row.id,
                    mask_email(to_email),
                    row.attempts,
                    row.last_error,
                )
        else:
            row.status = EmailStatus.SENT
            row.sent_at = when
            row.locked_until = None
            row.last_error = None
            # The body can hold sign-in or verification links: do not keep it.
            row.html_body = ""
            row.inline_images = None
            sent += 1
        db.commit()
    return DeliveryReport(claimed=len(ids), sent=sent, retried=retried, failed=failed)


def delete_old_emails(
    db: Session,
    *,
    sent_older_than_days: int = 7,
    failed_older_than_days: int = 30,
    failed_body_days: int = 1,
) -> int:
    """Housekeeping: the queue is not an archive of what people received.

    Rows that were sent are deleted after a week and failed ones after a month.
    A failed email keeps its body for a day (so it can be sent again by hand) and
    is blanked after that, together with its inline images (the ticket QR), because
    the links inside have long expired.
    """
    now = _now()
    db.execute(
        update(EmailOutbox)
        .where(
            EmailOutbox.status == EmailStatus.FAILED,
            EmailOutbox.created_at < now - timedelta(days=failed_body_days),
        )
        .values(html_body="", inline_images=None)
        .execution_options(synchronize_session=False)
    )
    result = db.execute(
        delete(EmailOutbox)
        .where(
            or_(
                and_(
                    EmailOutbox.status == EmailStatus.SENT,
                    EmailOutbox.sent_at < now - timedelta(days=sent_older_than_days),
                ),
                and_(
                    EmailOutbox.status == EmailStatus.FAILED,
                    EmailOutbox.created_at
                    < now - timedelta(days=failed_older_than_days),
                ),
            )
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount


def delete_emails_for(db: Session, to_email: str) -> int:
    """Erase every queued or recorded email to one address (for account erasure)."""
    result = db.execute(
        delete(EmailOutbox)
        .where(func.lower(EmailOutbox.to_email) == to_email.strip().lower())
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount


def requeue_failed(db: Session, *, now: datetime | None = None) -> int:
    """Put emails that gave up back in the queue (for example after a quota reset).

    Rows whose body was already blanked cannot be sent and are left alone.
    """
    result = db.execute(
        update(EmailOutbox)
        .where(EmailOutbox.status == EmailStatus.FAILED, EmailOutbox.html_body != "")
        .values(
            status=EmailStatus.PENDING,
            attempts=0,
            next_attempt_at=now or _now(),
            locked_until=None,
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount


def queue_stats(db: Session, *, now: datetime | None = None) -> dict[str, object]:
    """How many emails are in each state and how long the oldest pending one waits."""
    when = now or _now()
    counts = {status.value: 0 for status in EmailStatus}
    for status, number in db.execute(
        select(EmailOutbox.status, func.count()).group_by(EmailOutbox.status)
    ):
        counts[str(status)] = number
    oldest = db.scalar(
        select(func.min(EmailOutbox.created_at)).where(
            EmailOutbox.status == EmailStatus.PENDING
        )
    )
    age = None
    if oldest is not None:
        if oldest.tzinfo is None:
            oldest = oldest.replace(tzinfo=UTC)
        age = int((when - oldest).total_seconds())
    return {**counts, "oldest_pending_seconds": age}


class OutboxEmailSender(EmailSender):
    """EmailSender that stores the email and lets the worker deliver it."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        wake: threading.Event | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._wake = wake

    def send_html(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        inline_images: dict[str, bytes] | None = None,
    ) -> None:
        try:
            with self._session_factory() as db:
                enqueue_email(
                    db, to_email, subject, html_body, inline_images=inline_images
                )
        except Exception as exc:
            logger.error("Could not queue email %r: %s", subject, type(exc).__name__)
            raise EmailDeliveryError("could not queue the email") from exc
        if self._wake is not None:
            self._wake.set()


class OutboxWorker:
    """Thread that sends the due emails every few seconds, or as soon as woken."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        transport: EmailSender,
        *,
        poll_seconds: float = 5.0,
        max_attempts: int = 10,
    ) -> None:
        self._session_factory = session_factory
        self.transport = transport
        self._poll_seconds = poll_seconds
        self._max_attempts = max_attempts
        self.wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="email-outbox", daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        self.wake.set()
        if self._thread is not None:
            self._thread.join(timeout)

    def _run(self) -> None:
        while not self._stop.is_set():
            self.wake.wait(self._poll_seconds)
            self.wake.clear()
            if self._stop.is_set():
                break
            try:
                with self._session_factory() as db:
                    # Keep going while there is a backlog instead of waiting.
                    while not self._stop.is_set():
                        report = deliver_due(
                            db, self.transport, max_attempts=self._max_attempts
                        )
                        if report.claimed < BATCH_SIZE:
                            break
            except Exception as exc:  # the worker must never die
                logger.error("Email worker error: %s", type(exc).__name__)


def main(argv: list[str] | None = None) -> None:
    """Send what is due, show the queue, or put failed emails back in the queue."""
    import argparse

    from app.core.config import settings
    from app.core.email.factory import build_transport
    from app.db.session import SessionLocal

    parser = argparse.ArgumentParser(description="Email outbox")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--status", action="store_true", help="show the queue")
    action.add_argument(
        "--requeue-failed", action="store_true", help="try the failed emails again"
    )
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        if args.status:
            print(queue_stats(db))
        elif args.requeue_failed:
            print(f"Requeued {requeue_failed(db)} failed emails")
        else:
            transport = build_transport()
            sent = retried = failed = 0
            while True:
                report = deliver_due(
                    db, transport, max_attempts=settings.EMAIL_OUTBOX_MAX_ATTEMPTS
                )
                sent += report.sent
                retried += report.retried
                failed += report.failed
                if report.claimed < BATCH_SIZE:
                    break
            print(f"Sent {sent}, will retry {retried}, gave up {failed}")
