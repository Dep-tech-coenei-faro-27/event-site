import logging

import pytest

from app.core.email import EmailDeliveryError, mask_email
from app.core.email.factory import get_email_sender
from app.core.email.smtp import SmtpEmailSender
from app.main import app

REGISTER_URL = "/api/auth/register"


@pytest.mark.parametrize(
    ("address", "masked"),
    [
        ("ana@example.com", "a***@example.com"),
        ("j@example.com", "j***@example.com"),
        ("not-an-email", "***"),
        ("@example.com", "***"),
        ("", "***"),
    ],
)
def test_mask_email_keeps_only_the_first_letter_and_the_domain(address, masked):
    assert mask_email(address) == masked


def test_smtp_errors_do_not_contain_the_recipient(monkeypatch):
    def refuse(*args, **kwargs):
        raise OSError("550 rejected <ana@example.com>")

    monkeypatch.setattr("app.core.email.smtp.smtplib.SMTP", refuse)
    sender = SmtpEmailSender("smtp.example.com", 587, "", "", "noreply@example.com")

    with pytest.raises(EmailDeliveryError) as error:
        sender.send_html("ana@example.com", "Hi", "<p>Hi</p>")

    assert "ana@example.com" not in str(error.value)
    assert "a***@example.com" in str(error.value)


def test_a_failed_verification_email_is_logged_without_the_address(auth_client, caplog):
    class FailingSender:
        def send_html(self, to_email, subject, html_body):
            raise EmailDeliveryError("smtp is down")

    app.dependency_overrides[get_email_sender] = lambda: FailingSender()

    with caplog.at_level(logging.WARNING):
        response = auth_client.post(
            REGISTER_URL,
            json={
                "name": "Ana Silva",
                "email": "ana@example.com",
                "password": "Password123!",
                "accept_terms": True,
            },
        )

    assert response.status_code == 201
    assert "Failed to send verification email to a***@example.com" in caplog.text
    assert "ana@example.com" not in caplog.text
