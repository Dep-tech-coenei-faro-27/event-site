import smtplib
import ssl
from email.message import EmailMessage

from app.core.email.base import EmailDeliveryError, EmailSender, mask_email


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

    def send_html(self, to_email: str, subject: str, html_body: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.from_email
        message["To"] = to_email
        message.set_content(html_body, subtype="html")

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
                f"Could not send email to {masked}: {reason}"
            ) from exc
