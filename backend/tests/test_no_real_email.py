"""The tests, and so the CI, never send a real email."""

import smtplib

import pytest

from app.core.config import settings
from app.core.email import get_email_sender
from app.core.email.console import ConsoleEmailSender
from app.core.email.factory import build_transport
from app.core.email.outbox import OutboxEmailSender


def test_no_smtp_server_is_configured_in_the_tests():
    assert settings.SMTP_HOST == ""
    assert settings.SMTP_USER == "" and settings.SMTP_PASSWORD == ""


def test_the_transport_the_worker_would_use_only_writes_to_the_log():
    assert isinstance(build_transport(), ConsoleEmailSender)


def test_the_outbox_worker_is_off_so_nothing_is_sent_in_the_background():
    assert settings.EMAIL_OUTBOX_WORKER is False


def test_the_sender_the_routes_use_only_queues():
    assert isinstance(get_email_sender(), OutboxEmailSender)


@pytest.mark.parametrize("name", ["SMTP", "SMTP_SSL"])
def test_opening_an_smtp_connection_trips_the_wire(name):
    with pytest.raises(AssertionError, match="SMTP"):
        getattr(smtplib, name)("smtp.example.com", 587)


def test_registering_sends_nothing_outside_the_fake(auth_client, email_sender):
    response = auth_client.post(
        "/api/auth/register",
        json={
            "name": "Ana Silva",
            "email": "ana@example.com",
            "password": "Password123!",
            "accept_terms": True,
        },
    )

    assert response.status_code == 201
    assert len(email_sender.sent) == 1  # the fake caught it; no server was opened
