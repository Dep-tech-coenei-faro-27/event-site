import base64
import logging

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.email.models import EmailOutbox
from app.core.email.templates import TICKET_EMAIL_SUBJECT, TICKET_QR_CID
from app.core.qr import verify_qr_payload
from app.domains.payments.gateway import MBWayPayment, get_mbway_gateway
from app.domains.payments.models import TicketTier, Transaction, TransactionStatus
from app.domains.tickets.models import PaymentStatus, Ticket
from app.main import app
from tests.helpers import INITIATE_URL, authenticate, seed_ticket_tiers, transaction_url

CALLBACK_URL = "/api/payment/callback"
CALLBACK_KEY = "if-then-pay-anti-phishing-key"

INITIATE = {"ticket_tier": TicketTier.GERAL.value, "phone": "912345678"}


class FakeGateway:
    name = "fake"

    def __init__(self):
        self.status = TransactionStatus.PENDING
        self.provider_reference = "TX-1"

    def create_payment(self, *, reference, amount_cents, phone, email) -> MBWayPayment:
        return MBWayPayment(provider_reference=self.provider_reference)

    def get_status(self, *, reference, provider_reference) -> TransactionStatus:
        return self.status


@pytest.fixture
def gateway():
    fake = FakeGateway()
    app.dependency_overrides[get_mbway_gateway] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_mbway_gateway, None)


@pytest.fixture
def callback_key(monkeypatch):
    monkeypatch.setattr(settings, "MBWAY_CALLBACK_KEY", CALLBACK_KEY)
    return CALLBACK_KEY


def start_payment(auth_client, email_sender, db_session, gateway) -> dict:
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    response = auth_client.post(INITIATE_URL, json=INITIATE)
    assert response.status_code == 201
    return response.json()


def count_tickets(db_session, reference: str) -> int:
    return db_session.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(Ticket.transaction_reference == reference)
    )


def test_callback_confirms_the_transaction_and_issues_the_ticket(
    auth_client, email_sender, db_session, gateway, callback_key
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)

    response = auth_client.get(
        CALLBACK_URL,
        params={
            "key": callback_key,
            "orderId": payment["reference"],
            "amount": "50.00",
        },
    )

    assert response.status_code == 200

    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == payment["reference"])
    )
    db_session.refresh(transaction)
    assert transaction.status is TransactionStatus.CONFIRMED
    assert transaction.confirmed_at is not None

    ticket = db_session.scalar(
        select(Ticket).where(Ticket.transaction_reference == payment["reference"])
    )
    assert ticket is not None
    assert ticket.payment_status is PaymentStatus.PAID
    assert ticket.paid_at is not None
    assert verify_qr_payload(ticket.qr_payload).ticket_id == ticket.id


def test_polling_confirms_the_transaction_and_issues_the_ticket(
    auth_client, email_sender, db_session, gateway
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)
    gateway.status = TransactionStatus.CONFIRMED

    response = auth_client.get(transaction_url(payment["reference"]))

    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"

    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == payment["reference"])
    )
    db_session.refresh(transaction)
    assert transaction.confirmed_at is not None

    ticket = db_session.scalar(
        select(Ticket).where(Ticket.transaction_reference == payment["reference"])
    )
    assert ticket is not None
    assert ticket.payment_status is PaymentStatus.PAID
    assert verify_qr_payload(ticket.qr_payload).ticket_id == ticket.id


@pytest.mark.parametrize(
    "terminal_status", [TransactionStatus.FAILED, TransactionStatus.EXPIRED]
)
def test_callback_ignores_failed_or_expired_transactions(
    auth_client,
    email_sender,
    db_session,
    gateway,
    callback_key,
    caplog,
    terminal_status,
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == payment["reference"])
    )
    transaction.status = terminal_status
    db_session.commit()

    with caplog.at_level(logging.WARNING, logger="app.domains.payments.service"):
        response = auth_client.get(
            CALLBACK_URL,
            params={
                "key": callback_key,
                "orderId": payment["reference"],
                "amount": "50.00",
            },
        )

    assert response.status_code == 200
    db_session.refresh(transaction)
    assert transaction.status is terminal_status
    assert transaction.confirmed_at is None
    assert count_tickets(db_session, payment["reference"]) == 0
    assert payment["reference"] in caplog.text


def test_callback_is_rate_limited_per_ip(
    auth_client, email_sender, db_session, gateway, monkeypatch
):
    monkeypatch.setattr(settings, "RATE_LIMIT_PAYMENT_CALLBACK_PER_IP_PER_MINUTE", 2)
    params = {"key": "wrong", "orderId": "ENEI-DOES-NOT-EXIST", "amount": "1.00"}

    first = auth_client.get(CALLBACK_URL, params=params)
    second = auth_client.get(CALLBACK_URL, params=params)
    third = auth_client.get(CALLBACK_URL, params=params)

    assert first.status_code == 403
    assert second.status_code == 403
    assert third.status_code == 429


def test_callback_accepts_the_current_ifthenpay_parameter_names(
    auth_client, email_sender, db_session, gateway, callback_key
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)

    response = auth_client.get(
        CALLBACK_URL,
        params={
            "apk": callback_key,
            "oid": payment["reference"],
            "val": "50.00",
            "tid": "itp-request-id",
            "pm": "MBWAY",
        },
    )

    assert response.status_code == 200
    ticket = db_session.scalar(
        select(Ticket).where(Ticket.transaction_reference == payment["reference"])
    )
    assert ticket is not None


def test_callback_rejects_a_wrong_key(
    auth_client, email_sender, db_session, gateway, callback_key
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)

    response = auth_client.get(
        CALLBACK_URL,
        params={
            "key": "the-wrong-key",
            "orderId": payment["reference"],
            "amount": "50.00",
        },
    )

    assert response.status_code == 403
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == payment["reference"])
    )
    db_session.refresh(transaction)
    assert transaction.status is TransactionStatus.PENDING
    assert count_tickets(db_session, payment["reference"]) == 0


def test_callback_rejects_a_missing_key(
    auth_client, email_sender, db_session, gateway, callback_key
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)

    response = auth_client.get(
        CALLBACK_URL,
        params={"orderId": payment["reference"], "amount": "50.00"},
    )

    assert response.status_code == 403
    assert count_tickets(db_session, payment["reference"]) == 0


def test_callback_is_rejected_while_the_server_key_is_unset(
    auth_client, email_sender, db_session, gateway, monkeypatch
):
    monkeypatch.setattr(settings, "MBWAY_CALLBACK_KEY", "")
    payment = start_payment(auth_client, email_sender, db_session, gateway)

    response = auth_client.get(
        CALLBACK_URL,
        params={
            "key": "",
            "orderId": payment["reference"],
            "amount": "50.00",
        },
    )

    assert response.status_code == 403


def test_callback_rejects_an_unknown_reference(
    auth_client, email_sender, db_session, gateway, callback_key
):
    response = auth_client.get(
        CALLBACK_URL,
        params={
            "key": callback_key,
            "orderId": "ENEI-DOES-NOT-EXIST",
            "amount": "50.00",
        },
    )

    assert response.status_code == 404


def test_callback_rejects_a_mismatched_amount(
    auth_client, email_sender, db_session, gateway, callback_key
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)

    response = auth_client.get(
        CALLBACK_URL,
        params={
            "key": callback_key,
            "orderId": payment["reference"],
            "amount": "0.01",
        },
    )

    assert response.status_code == 400
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == payment["reference"])
    )
    db_session.refresh(transaction)
    assert transaction.status is TransactionStatus.PENDING
    assert count_tickets(db_session, payment["reference"]) == 0


def test_callback_rejects_a_non_numeric_amount(
    auth_client, email_sender, db_session, gateway, callback_key
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)

    response = auth_client.get(
        CALLBACK_URL,
        params={
            "key": callback_key,
            "orderId": payment["reference"],
            "amount": "fifty euros",
        },
    )

    assert response.status_code == 400


def test_callback_is_idempotent_and_never_duplicates_the_ticket(
    auth_client, email_sender, db_session, gateway, callback_key
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)
    params = {
        "key": callback_key,
        "orderId": payment["reference"],
        "amount": "50.00",
    }

    first = auth_client.get(CALLBACK_URL, params=params)
    ticket = db_session.scalar(
        select(Ticket).where(Ticket.transaction_reference == payment["reference"])
    )
    signed_payload = ticket.qr_payload

    second = auth_client.get(CALLBACK_URL, params=params)

    assert first.status_code == 200
    assert second.status_code == 200
    assert count_tickets(db_session, payment["reference"]) == 1
    db_session.refresh(ticket)
    assert ticket.qr_payload == signed_payload


def test_callback_is_public_and_needs_no_authentication(
    auth_client, email_sender, db_session, gateway, callback_key
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)
    auth_client.cookies.clear()

    response = auth_client.get(
        CALLBACK_URL,
        params={
            "key": callback_key,
            "orderId": payment["reference"],
            "amount": "50.00",
        },
    )

    assert response.status_code == 200


def test_confirmed_payment_queues_the_ticket_email_with_the_qr_once(
    auth_client, email_sender, db_session, gateway, callback_key
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)
    params = {
        "key": callback_key,
        "orderId": payment["reference"],
        "amount": "50.00",
    }

    auth_client.get(CALLBACK_URL, params=params)
    auth_client.get(CALLBACK_URL, params=params)

    emails = db_session.scalars(
        select(EmailOutbox).where(EmailOutbox.subject == TICKET_EMAIL_SUBJECT)
    ).all()
    assert len(emails) == 1
    email = emails[0]
    ticket = db_session.scalar(
        select(Ticket).where(Ticket.transaction_reference == payment["reference"])
    )
    assert email.dedupe_key == f"ticket:{ticket.id}"
    assert f"cid:{TICKET_QR_CID}" in email.html_body
    assert payment["reference"] in email.html_body
    assert "Passe geral" in email.html_body
    png = base64.b64decode(email.inline_images[TICKET_QR_CID])
    assert png.startswith(b"\x89PNG")
