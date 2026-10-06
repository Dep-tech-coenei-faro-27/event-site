from functools import lru_cache

from app.core.config import settings
from app.core.email.background import BackgroundEmailSender
from app.core.email.base import EmailSender
from app.core.email.console import ConsoleEmailSender
from app.core.email.smtp import SmtpEmailSender


def _build_transport() -> EmailSender:
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
def _build_sender() -> EmailSender:
    return BackgroundEmailSender(_build_transport())


def get_email_sender() -> EmailSender:
    """Return the configured email transport.

    Swap the transport in ``_build_sender`` (e.g. for a self-hosted provider)
    without touching the code that sends emails. Delivery runs in the
    background, so a slow mail server never holds up a request.
    """
    return _build_sender()
