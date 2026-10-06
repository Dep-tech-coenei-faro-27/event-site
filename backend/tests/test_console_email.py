import logging

from app.core.email import ConsoleEmailSender
from app.core.email.templates import (
    VERIFICATION_EMAIL_SUBJECT,
    build_verification_email_html,
)


def test_console_sender_logs_recipient_subject_and_links(caplog):
    html = build_verification_email_html(
        "Ana", "https://app.example.com/verify-email?token=abc&x=1"
    )

    with caplog.at_level(logging.INFO):
        ConsoleEmailSender().send_html("ana@example.com", "Hi", html)

    assert "ana@example.com" in caplog.text
    assert "Hi" in caplog.text
    assert "https://app.example.com/verify-email?token=abc&x=1" in caplog.text


def test_console_sender_lists_each_link_once(caplog):
    html = build_verification_email_html("Ana", "https://app.example.com/v?token=abc")

    with caplog.at_level(logging.INFO):
        ConsoleEmailSender().send_html("ana@example.com", "Hi", html)

    assert caplog.text.count("https://app.example.com/v?token=abc") == 1


def test_verification_email_is_in_portuguese():
    html = build_verification_email_html("Ana", "https://app.example.com/v?token=abc")

    assert VERIFICATION_EMAIL_SUBJECT == "Confirma o teu email"
    assert "Olá Ana," in html
    assert "Confirmar email" in html
    assert "Confirm your email" not in html
