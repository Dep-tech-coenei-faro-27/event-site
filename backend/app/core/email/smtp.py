import re
import smtplib
import ssl
from email.message import EmailMessage

from app.core.email.base import EmailDeliveryError, EmailSender, mask_email
from app.core.email.text import html_to_text


class SmtpEmailSender(EmailSender):
    """EmailSender backed by plain smtplib so any SMTP server can be used.

    Port 465 implies implicit TLS (``SMTP_SSL``); other ports use ``SMTP``
    with ``starttls()``. ``security`` overrides that rule with ``"ssl"``,
    ``"starttls"`` or ``"none"`` (local mail catchers only). Both TLS modes
    verify the server certificate and host name.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_email: str,
        start_tls: bool | None = None,
        timeout: float = 10.0,
        security: str | None = None,
        tls_context: ssl.SSLContext | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.timeout = timeout

        if security is None:
            if start_tls is None:
                security = "ssl" if port == 465 else "starttls"
            else:
                security = "starttls" if start_tls else "ssl"
        if security not in {"ssl", "starttls", "none"}:
            raise ValueError(f"Unknown SMTP security mode: {security!r}")
        self.security = security
        self.start_tls = security == "starttls"
        self.tls_context = tls_context or ssl.create_default_context()

    def send_html(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        inline_images: dict[str, bytes] | None = None,
        text_body: str | None = None,
    ) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.from_email
        message["To"] = to_email
        message.set_content(text_body or html_to_text(html_body))
        message.add_alternative(html_body, subtype="html")
        html_part = message.get_payload()[1]
        for cid, png in (inline_images or {}).items():
            html_part.add_related(png, maintype="image", subtype="png", cid=f"<{cid}>")

        try:
            if self.security == "ssl":
                server = smtplib.SMTP_SSL(
                    self.host,
                    self.port,
                    timeout=self.timeout,
                    context=self.tls_context,
                )
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=self.timeout)

            with server:
                if self.security == "starttls":
                    server.starttls(context=self.tls_context)
                if self.username:
                    server.login(self.username, self.password)
                server.send_message(message)
        except Exception as exc:
            masked = mask_email(to_email)
            reason = str(exc).replace(to_email, masked)
            raise EmailDeliveryError(
                f"Could not send email to {masked}: {reason}", classify_error(exc)
            ) from exc


# Words a provider uses when it refuses for the whole day, for example
# "550 5.4.5 Daily user sending quota exceeded". Only a permanent (5xx) answer counts:
# it keeps the primary out until midnight UTC, so it must be about the day.
DAILY_PATTERN = re.compile(rb"quota|daily|per day|5\.4\.5", re.IGNORECASE)
# Answers that match those words but are about this one email or mailbox:
# "552 5.3.4 Message size exceeds fixed limit", "552 5.2.2 Mailbox over quota".
NOT_DAILY_PATTERN = re.compile(rb"size|mailbox|5\.3\.4|5\.2\.2", re.IGNORECASE)


def _responses(exc: Exception) -> list[tuple[int, bytes]]:
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return [
            (code, message if isinstance(message, bytes) else str(message).encode())
            for code, message in exc.recipients.values()
        ]
    if isinstance(exc, smtplib.SMTPResponseException):
        message = exc.smtp_error
        if not isinstance(message, bytes):
            message = str(message).encode()
        return [(exc.smtp_code, message)]
    return []


def classify_error(exc: Exception) -> str:
    """Whether a failure was the day's quota, a refused recipient or the server.

    - A refused recipient never goes to the fallback (the other server would refuse
      the same address) and never marks the day: a full mailbox is that person's.
      A temporary (4xx) refusal of the recipient is the server's: that email only.
    - Any other temporary (4xx) answer, "421 rate limited" or "454 too many login
      attempts" included, sends that email only through the fallback.
    - Only a permanent (5xx) answer that names the daily quota is ``"limit"``.
    """
    responses = _responses(exc)
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        if responses and all(400 <= code < 500 for code, _ in responses):
            return EmailDeliveryError.SERVER
        return EmailDeliveryError.RECIPIENT
    if any(
        code >= 500
        and DAILY_PATTERN.search(message)
        and not NOT_DAILY_PATTERN.search(message)
        for code, message in responses
    ):
        return EmailDeliveryError.LIMIT
    return EmailDeliveryError.SERVER
