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


# Words providers use when they refuse because of a sending quota, for example
# "450 Daily sending quota exceeded" or "550 5.4.5 Daily user sending limit".
LIMIT_PATTERN = re.compile(
    rb"quota|limit|too many|exceeded|throttl|5\.4\.5|4\.7\.28", re.IGNORECASE
)
# "552 5.3.4 Message size exceeds fixed limit" is about this email, not the day.
SIZE_PATTERN = re.compile(rb"size|5\.3\.4", re.IGNORECASE)


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
    """Whether a failure was a quota, a refused recipient or the server itself.

    A refused recipient never goes to the fallback: the other server would refuse
    the same address, and the email would only spend the fallback's quota.
    """
    responses = _responses(exc)
    if any(
        LIMIT_PATTERN.search(message) and not SIZE_PATTERN.search(message)
        for _, message in responses
    ):
        return EmailDeliveryError.LIMIT
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return EmailDeliveryError.RECIPIENT
    return EmailDeliveryError.SERVER
