from functools import lru_cache

from app.core.config import settings
from app.core.email.base import EmailSender
from app.core.email.console import ConsoleEmailSender
from app.core.email.outbox import OutboxEmailSender, OutboxWorker
from app.core.email.smtp import SmtpEmailSender
from app.db.session import SessionLocal


def build_transport() -> EmailSender:
    if not settings.SMTP_HOST:
        return ConsoleEmailSender()
    return SmtpEmailSender(
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        from_email=settings.EMAIL_SENDER,
        timeout=float(settings.SMTP_TIMEOUT_SECONDS),
        security=None if settings.SMTP_SECURITY == "auto" else settings.SMTP_SECURITY,
    )


@lru_cache
def _build_worker() -> OutboxWorker:
    return OutboxWorker(
        SessionLocal,
        build_transport(),
        poll_seconds=settings.EMAIL_OUTBOX_POLL_SECONDS,
        max_attempts=settings.EMAIL_OUTBOX_MAX_ATTEMPTS,
    )


@lru_cache
def _build_sender() -> EmailSender:
    return OutboxEmailSender(SessionLocal, wake=_build_worker().wake)


_worker_running = False


def start_email_worker() -> None:
    """Start the thread that delivers queued emails (once, with the app)."""
    global _worker_running
    if settings.EMAIL_OUTBOX_WORKER:
        _build_worker().start()
        _worker_running = True


def stop_email_worker() -> None:
    global _worker_running
    if _worker_running:
        _build_worker().stop()
        _worker_running = False


def get_email_sender() -> EmailSender:
    """Return the sender used by the routes.

    Emails are written to the ``email_outbox`` table and delivered by a worker,
    so a slow or unreachable mail server never holds up a request and a queued
    email survives a restart. Swap the transport in ``build_transport`` (for
    example for a self-hosted provider) without touching the code that sends.
    """
    return _build_sender()
