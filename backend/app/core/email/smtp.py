import smtplib
from email.message import EmailMessage

from app.core.email.base import EmailDeliveryError, EmailSender


class SmtpEmailSender(EmailSender):
    """EmailSender backed by plain smtplib so any SMTP server can be used.

    Port 465 implies implicit TLS (``SMTP_SSL``); other ports use
    ``SMTP`` with ``starttls()``. Both behaviors can be overridden with
    ``start_tls``.
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
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.start_tls = (port != 465) if start_tls is None else start_tls
        self.timeout = timeout

    def send_html(self, to_email: str, subject: str, html_body: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.from_email
        message["To"] = to_email
        message.set_content(html_body, subtype="html")

        try:
            if self.start_tls:
                server = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
                with server:
                    server.starttls()
                    if self.username:
                        server.login(self.username, self.password)
                    server.send_message(message)
            else:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout)
                with server:
                    if self.username:
                        server.login(self.username, self.password)
                    server.send_message(message)
        except Exception as exc:
            raise EmailDeliveryError(
                f"Could not send email to {to_email}: {exc}"
            ) from exc
