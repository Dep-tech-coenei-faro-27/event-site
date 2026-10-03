import smtplib

import pytest

from app.core.email.base import EmailDeliveryError, EmailSender
from app.core.email.smtp import SmtpEmailSender
from app.core.email.templates import (
    VERIFICATION_EMAIL_SUBJECT,
    build_verification_email_html,
)


class _RecordingServer:
    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.login_called = None
        self.sent_message = None
        self.quit_called = False
        self.tls_started = False

    def starttls(self):
        self.tls_started = True
        return (220, b"Ready to start TLS")

    def login(self, username, password):
        self.login_called = (username, password)
        return (235, b"Authentication successful")

    def send_message(self, message):
        self.sent_message = message

    def quit(self):
        self.quit_called = True
        return (221, b"Bye")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.quit()


def _make_server(recorded, server_cls=_RecordingServer):
    def factory(host, port, timeout=None):
        server = server_cls(host, port, timeout)
        recorded.append(server)
        return server

    return factory


def _message_parts(sender, to_email):
    html = sender.sent_message.get_content()
    return {
        "from": sender.sent_message["From"],
        "to": sender.sent_message["To"],
        "subject": sender.sent_message["Subject"],
        "content_type": sender.sent_message.get_content_type(),
        "html": html,
    }


def test_email_sender_is_abstract():
    with pytest.raises(TypeError):
        EmailSender()


def test_send_html_uses_implicit_tls_on_port_465(monkeypatch):
    servers = []
    monkeypatch.setattr(smtplib, "SMTP_SSL", _make_server(servers))

    def unexpected_smtp(*args, **kwargs):
        raise AssertionError("SMTP should not be used for port 465")

    monkeypatch.setattr(smtplib, "SMTP", unexpected_smtp)

    sender = SmtpEmailSender(
        host="smtp.example.com",
        port=465,
        username="user",
        password="secret",
        from_email="no-reply@example.com",
    )
    sender.send_html("recipient@example.com", "Greetings", "<p>Hello</p>")

    assert len(servers) == 1
    server = servers[0]
    assert server.host == "smtp.example.com"
    assert server.port == 465
    assert server.login_called == ("user", "secret")
    assert server.quit_called

    message = _message_parts(server, "recipient@example.com")
    assert message["from"] == "no-reply@example.com"
    assert message["to"] == "recipient@example.com"
    assert message["subject"] == "Greetings"
    assert message["content_type"] == "text/html"
    assert message["html"].strip() == "<p>Hello</p>"


def test_send_html_uses_starttls_on_other_ports(monkeypatch):
    servers = []
    monkeypatch.setattr(smtplib, "SMTP", _make_server(servers))

    def unexpected_ssl(*args, **kwargs):
        raise AssertionError("SMTP_SSL should not be used for port 587")

    monkeypatch.setattr(smtplib, "SMTP_SSL", unexpected_ssl)

    sender = SmtpEmailSender(
        host="smtp.resend.com",
        port=587,
        username="resend",
        password="token",
        from_email="onboarding@resend.dev",
    )
    sender.send_html("to@example.com", "Hi", "<b>Hi</b>")

    assert len(servers) == 1
    server = servers[0]
    assert server.host == "smtp.resend.com"
    assert server.port == 587
    assert server.tls_started
    assert server.login_called == ("resend", "token")
    assert server.quit_called

    message = _message_parts(server, "to@example.com")
    assert message["to"] == "to@example.com"
    assert message["subject"] == "Hi"
    assert message["html"].strip() == "<b>Hi</b>"


def test_send_html_skips_login_when_no_credentials(monkeypatch):
    servers = []
    monkeypatch.setattr(smtplib, "SMTP_SSL", _make_server(servers))

    sender = SmtpEmailSender(
        host="smtp.example.com",
        port=465,
        username="",
        password="",
        from_email="no-reply@example.com",
    )
    sender.send_html("to@example.com", "Hi", "<p>Hi</p>")

    assert len(servers) == 1
    assert servers[0].login_called is None


def test_send_html_wraps_network_errors_in_email_delivery_error(monkeypatch):
    class BrokenServer:
        def __init__(self, host, port, timeout=None):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def send_message(self, message):
            raise ConnectionRefusedError("connection refused")

    monkeypatch.setattr(smtplib, "SMTP_SSL", BrokenServer)

    sender = SmtpEmailSender(
        host="127.0.0.1",
        port=465,
        username="user",
        password="pass",
        from_email="from@example.com",
    )

    with pytest.raises(EmailDeliveryError):
        sender.send_html("to@example.com", "Hi", "<p>Hi</p>")


def test_send_html_allows_explicit_starttls_override(monkeypatch):
    servers = []
    monkeypatch.setattr(smtplib, "SMTP", _make_server(servers))

    sender = SmtpEmailSender(
        host="smtp.example.com",
        port=465,
        username="",
        password="",
        from_email="from@example.com",
        start_tls=True,
    )
    sender.send_html("to@example.com", "Hi", "<p>Hi</p>")

    assert len(servers) == 1
    assert servers[0].port == 465
    assert servers[0].tls_started


def test_verification_template_contains_link_and_subject():
    html = build_verification_email_html(
        "Ana", "https://app.example.com/verify-email?token=abc123"
    )

    assert "<html" in html.lower()
    assert "Ana" in html
    assert "https://app.example.com/verify-email?token=abc123" in html
    assert VERIFICATION_EMAIL_SUBJECT != ""


def test_verification_template_escapes_html_in_name():
    html = build_verification_email_html(
        "<script>alert('xss')</script>",
        "https://app.example.com/verify-email?token=abc",
    )

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
