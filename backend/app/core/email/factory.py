from app.core.config import settings
from app.core.email.base import EmailSender
from app.core.email.smtp import SmtpEmailSender


def get_email_sender() -> EmailSender:
    """Build the configured email transport.

    Swap the transport here (e.g. for a self-hosted provider) without
    touching the code that sends emails.
    """
    return SmtpEmailSender(
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        from_email=settings.EMAIL_SENDER,
    )
