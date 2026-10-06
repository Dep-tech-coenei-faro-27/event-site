import logging
import threading

from app.core.config import settings
from app.core.email import (
    BackgroundEmailSender,
    ConsoleEmailSender,
    EmailSender,
    get_email_sender,
)
from app.core.email.base import EmailDeliveryError
from app.core.email.factory import _build_sender
from app.core.email.smtp import SmtpEmailSender


class _BlockingSender(EmailSender):
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.sent = []

    def send_html(self, to_email, subject, html_body):
        self.started.set()
        self.release.wait(timeout=5)
        self.sent.append((to_email, subject))


class _FailingSender(EmailSender):
    def send_html(self, to_email, subject, html_body):
        raise EmailDeliveryError("mail server down")


def test_send_html_returns_while_the_mail_server_is_still_busy():
    sender = _BlockingSender()
    background = BackgroundEmailSender(sender, workers=1)

    background.send_html("to@example.com", "Hi", "<p>Hi</p>")

    assert sender.started.wait(timeout=2)
    assert sender.sent == []
    sender.release.set()
    background._queue.join()
    assert sender.sent == [("to@example.com", "Hi")]


def test_delivery_errors_are_logged_and_not_raised(caplog):
    background = BackgroundEmailSender(_FailingSender(), workers=1)

    with caplog.at_level(logging.WARNING):
        background.send_html("to@example.com", "Hi", "<p>Hi</p>")
        background._queue.join()

    assert "Failed to send email: mail server down" in caplog.text


def test_emails_are_dropped_and_logged_when_the_queue_is_full(caplog):
    sender = _BlockingSender()
    background = BackgroundEmailSender(sender, workers=1, max_queue=1)
    background.send_html("to@example.com", "First", "<p>1</p>")
    assert sender.started.wait(timeout=2)
    background.send_html("to@example.com", "Second", "<p>2</p>")

    with caplog.at_level(logging.WARNING):
        background.send_html("to@example.com", "Third", "<p>3</p>")

    assert "Email queue is full, dropping email: Third" in caplog.text
    sender.release.set()
    background._queue.join()
    assert [subject for _, subject in sender.sent] == ["First", "Second"]


def test_get_email_sender_delivers_in_the_background_with_one_shared_sender(
    monkeypatch,
):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    _build_sender.cache_clear()
    sender = get_email_sender()

    assert isinstance(sender, BackgroundEmailSender)
    assert get_email_sender() is sender
    assert isinstance(sender.sender, SmtpEmailSender)
    assert sender.sender.timeout == float(settings.SMTP_TIMEOUT_SECONDS)
    _build_sender.cache_clear()


def test_without_an_smtp_host_emails_go_to_the_console_sender(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    _build_sender.cache_clear()

    sender = get_email_sender()

    assert isinstance(sender, BackgroundEmailSender)
    assert isinstance(sender.sender, ConsoleEmailSender)
    _build_sender.cache_clear()
