import base64
import logging
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event, func, select

from app.core.config import settings
from app.core.email.models import EmailOutbox
from app.core.email.templates import TICKET_EMAIL_SUBJECT, TICKET_QR_CID
from app.core.qr import verify_qr_payload
from app.domains.payments.gateway import MBWayPayment, get_mbway_gateway
from app.domains.payments.models import (
    TicketTier,
    TicketTierPrice,
    Transaction,
    TransactionStatus,
)
from app.domains.payments.service import queue_missing_ticket_emails
from app.domains.tickets.models import PaymentStatus, Ticket
from app.domains.users.models import User
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


def test_the_ifthenpay_callback_cannot_settle_a_stripe_payment(
    auth_client, email_sender, db_session, gateway, callback_key
):
    gateway.name = "stripe"
    payment = start_payment(auth_client, email_sender, db_session, gateway)

    response = auth_client.get(
        CALLBACK_URL,
        params={
            "key": callback_key,
            "orderId": payment["reference"],
            "amount": "50.00",
        },
    )

    assert response.status_code == 404
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == payment["reference"])
    )
    db_session.refresh(transaction)
    assert transaction.status is TransactionStatus.PENDING
    assert count_tickets(db_session, payment["reference"]) == 0


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


def pay(auth_client, reference: str):
    return auth_client.get(
        CALLBACK_URL,
        params={"key": CALLBACK_KEY, "orderId": reference, "amount": "50.00"},
    )


@pytest.mark.parametrize(
    "terminal_status", [TransactionStatus.FAILED, TransactionStatus.EXPIRED]
)
def test_a_late_callback_still_issues_the_ticket(
    auth_client,
    email_sender,
    db_session,
    gateway,
    callback_key,
    caplog,
    terminal_status,
):
    """The callback only comes when the money was paid: the person gets the ticket."""
    payment = start_payment(auth_client, email_sender, db_session, gateway)
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == payment["reference"])
    )
    transaction.status = terminal_status
    db_session.commit()

    with caplog.at_level(logging.WARNING, logger="app.domains.payments.service"):
        response = pay(auth_client, payment["reference"])

    assert response.status_code == 200
    db_session.refresh(transaction)
    assert transaction.status is TransactionStatus.CONFIRMED
    assert transaction.confirmed_at is not None
    assert count_tickets(db_session, payment["reference"]) == 1
    assert "Late MB WAY payment" in caplog.text
    assert payment["reference"] in caplog.text


def test_a_late_payment_for_someone_who_already_has_a_ticket_is_kept_for_a_refund(
    auth_client, email_sender, db_session, gateway, callback_key, caplog
):
    first = start_payment(auth_client, email_sender, db_session, gateway)
    assert pay(auth_client, first["reference"]).status_code == 200
    original = db_session.scalar(select(Ticket))
    signed_payload = original.qr_payload
    paid = db_session.scalar(
        select(Transaction).where(Transaction.reference == first["reference"])
    )
    second = Transaction(
        reference="ENEI-LATE000001",
        user_id=paid.user_id,
        ticket_tier_id=paid.ticket_tier_id,
        amount_cents=paid.amount_cents,
        quantity=1,
        status=TransactionStatus.EXPIRED,
        phone=paid.phone,
        provider=paid.provider,
        expires_at=paid.expires_at,
    )
    db_session.add(second)
    db_session.commit()

    with caplog.at_level(logging.ERROR, logger="app.domains.payments.service"):
        response = pay(auth_client, "ENEI-LATE000001")

    assert response.status_code == 200
    db_session.refresh(second)
    assert second.status is TransactionStatus.REFUND_DUE
    assert count_tickets(db_session, "ENEI-LATE000001") == 0
    assert db_session.scalar(select(func.count()).select_from(Ticket)) == 1
    db_session.refresh(original)
    assert original.qr_payload == signed_payload
    assert "Payment ENEI-LATE000001 needs a refund" in caplog.text


def test_two_payments_of_one_person_never_crash_the_callback(
    auth_client, email_sender, db_session, test_engine, gateway, callback_key, caplog
):
    """The provider closed the first attempt, a second one was started and paid, and
    then the first one is paid too (it should not happen): it used to fail with a
    500 and be retried for ever."""
    first = start_payment(auth_client, email_sender, db_session, gateway)
    stale = db_session.scalar(
        select(Transaction).where(Transaction.reference == first["reference"])
    )
    stale.status = TransactionStatus.EXPIRED
    db_session.commit()
    second = auth_client.post(INITIATE_URL, json=INITIATE)
    assert second.status_code == 201
    assert pay(auth_client, second.json()["reference"]).status_code == 200

    database_errors: list[object] = []

    def remember(context) -> None:
        database_errors.append(context.original_exception)

    event.listen(test_engine, "handle_error", remember)
    try:
        with caplog.at_level(logging.ERROR, logger="app.domains.payments.service"):
            response = pay(auth_client, first["reference"])
    finally:
        event.remove(test_engine, "handle_error", remember)

    assert response.status_code == 200
    # Found by looking before inserting, not by colliding with the unique index.
    assert database_errors == []
    db_session.refresh(stale)
    assert stale.status is TransactionStatus.REFUND_DUE
    assert count_tickets(db_session, first["reference"]) == 0
    assert count_tickets(db_session, second.json()["reference"]) == 1
    assert f"Payment {first['reference']} needs a refund" in caplog.text


def _sell_out_the_modality(db_session, payment: dict) -> None:
    """Give the modality of ``payment`` a limit of one that another buyer holds."""
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == payment["reference"])
    )
    tier = db_session.get(TicketTierPrice, transaction.ticket_tier_id)
    tier.inventory_limit = 1
    other = User(name="Rui Costa", email="rui@example.com", password_hash="x")
    db_session.add(other)
    db_session.flush()
    db_session.add(
        Transaction(
            reference="ENEI-OTHER00001",
            user_id=other.id,
            ticket_tier_id=tier.id,
            amount_cents=transaction.amount_cents,
            quantity=1,
            status=TransactionStatus.CONFIRMED,
            phone="912345678",
            provider="fake",
            expires_at=transaction.expires_at,
        )
    )
    db_session.commit()


@pytest.mark.parametrize(
    "late_status", [TransactionStatus.FAILED, TransactionStatus.EXPIRED]
)
def test_a_late_payment_is_not_sold_when_the_modality_sold_out(
    auth_client, email_sender, db_session, gateway, callback_key, caplog, late_status
):
    """We do not sell what we no longer have: the payment is kept for a refund."""
    payment = start_payment(auth_client, email_sender, db_session, gateway)
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == payment["reference"])
    )
    transaction.status = late_status
    db_session.commit()
    _sell_out_the_modality(db_session, payment)

    with caplog.at_level(logging.ERROR, logger="app.domains.payments.service"):
        response = pay(auth_client, payment["reference"])

    assert response.status_code == 200
    db_session.refresh(transaction)
    assert transaction.status is TransactionStatus.REFUND_DUE
    assert count_tickets(db_session, payment["reference"]) == 0
    assert "the modality sold out" in caplog.text


def test_a_payment_still_waiting_past_its_deadline_is_sold_even_at_the_limit(
    auth_client, email_sender, db_session, gateway, callback_key
):
    """Waiting payments hold their seat: when the modality is at its limit, that
    seat is this one, so a callback after the deadline gets the ticket."""
    payment = start_payment(auth_client, email_sender, db_session, gateway)
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == payment["reference"])
    )
    transaction.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    tier = db_session.get(TicketTierPrice, transaction.ticket_tier_id)
    tier.inventory_limit = 1
    db_session.commit()

    assert pay(auth_client, payment["reference"]).status_code == 200

    db_session.refresh(transaction)
    assert transaction.status is TransactionStatus.CONFIRMED
    assert count_tickets(db_session, payment["reference"]) == 1


def test_a_payment_inside_its_window_always_keeps_its_seat(
    auth_client, email_sender, db_session, gateway, callback_key
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == payment["reference"])
    )
    tier = db_session.get(TicketTierPrice, transaction.ticket_tier_id)
    tier.inventory_limit = 1  # this very payment holds the last seat
    db_session.commit()

    assert pay(auth_client, payment["reference"]).status_code == 200

    db_session.refresh(transaction)
    assert transaction.status is TransactionStatus.CONFIRMED
    assert count_tickets(db_session, payment["reference"]) == 1


def test_a_late_payment_is_sold_while_there_is_still_stock(
    auth_client, email_sender, db_session, gateway, callback_key
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == payment["reference"])
    )
    transaction.status = TransactionStatus.EXPIRED
    tier = db_session.get(TicketTierPrice, transaction.ticket_tier_id)
    tier.inventory_limit = 5
    db_session.commit()

    assert pay(auth_client, payment["reference"]).status_code == 200

    db_session.refresh(transaction)
    assert transaction.status is TransactionStatus.CONFIRMED
    assert count_tickets(db_session, payment["reference"]) == 1


def test_a_refund_due_payment_stays_that_way_when_the_callback_is_repeated(
    auth_client, email_sender, db_session, gateway, callback_key
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == payment["reference"])
    )
    transaction.status = TransactionStatus.EXPIRED
    db_session.commit()
    _sell_out_the_modality(db_session, payment)
    pay(auth_client, payment["reference"])

    tier = db_session.get(TicketTierPrice, transaction.ticket_tier_id)
    tier.inventory_limit = None  # stock came back, the decision was already taken
    db_session.commit()
    assert pay(auth_client, payment["reference"]).status_code == 200

    db_session.refresh(transaction)
    assert transaction.status is TransactionStatus.REFUND_DUE
    assert count_tickets(db_session, payment["reference"]) == 0


def test_a_repeated_callback_repairs_a_transaction_that_already_has_its_ticket(
    auth_client, email_sender, db_session, gateway, callback_key
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)
    assert pay(auth_client, payment["reference"]).status_code == 200
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == payment["reference"])
    )
    transaction.status = TransactionStatus.EXPIRED
    db_session.commit()

    assert pay(auth_client, payment["reference"]).status_code == 200

    db_session.rollback()  # whatever was not committed is gone
    db_session.refresh(transaction)
    assert transaction.status is TransactionStatus.CONFIRMED
    assert count_tickets(db_session, payment["reference"]) == 1


def test_a_repeated_callback_does_not_bring_back_a_cancelled_ticket(
    auth_client, email_sender, db_session, gateway, callback_key, caplog
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)
    assert pay(auth_client, payment["reference"]).status_code == 200
    ticket = db_session.scalar(select(Ticket))
    ticket.payment_status = PaymentStatus.CANCELLED
    db_session.commit()

    with caplog.at_level(logging.WARNING, logger="app.domains.payments.service"):
        response = pay(auth_client, payment["reference"])

    assert response.status_code == 200
    db_session.refresh(ticket)
    assert ticket.payment_status is PaymentStatus.CANCELLED
    assert count_tickets(db_session, payment["reference"]) == 1
    assert "its ticket is cancelled" in caplog.text


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


def test_issued_ticket_keeps_the_modality_transaction_and_holder(
    auth_client, email_sender, db_session, gateway, callback_key
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)

    auth_client.get(
        CALLBACK_URL,
        params={
            "key": callback_key,
            "orderId": payment["reference"],
            "amount": "50.00",
        },
    )

    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == payment["reference"])
    )
    ticket = db_session.scalar(
        select(Ticket).where(Ticket.transaction_reference == payment["reference"])
    )
    assert ticket.ticket_tier == TicketTier.GERAL
    assert ticket.user_id == transaction.user_id


def break_the_queue(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("queue down")

    monkeypatch.setattr("app.domains.payments.service.enqueue_email", boom)


def ticket_emails(db_session) -> list[EmailOutbox]:
    return db_session.scalars(
        select(EmailOutbox).where(EmailOutbox.subject == TICKET_EMAIL_SUBJECT)
    ).all()


def test_callback_survives_a_failing_email_queue(
    auth_client, email_sender, db_session, gateway, callback_key, monkeypatch
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)
    break_the_queue(monkeypatch)

    response = auth_client.get(
        CALLBACK_URL,
        params={
            "key": callback_key,
            "orderId": payment["reference"],
            "amount": "50.00",
        },
    )

    assert response.status_code == 200
    assert count_tickets(db_session, payment["reference"]) == 1
    assert ticket_emails(db_session) == []
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == payment["reference"])
    )
    db_session.refresh(transaction)
    assert transaction.status is TransactionStatus.CONFIRMED


def test_status_poll_survives_a_failing_email_queue(
    auth_client, email_sender, db_session, gateway, monkeypatch
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)
    gateway.status = TransactionStatus.CONFIRMED
    break_the_queue(monkeypatch)

    response = auth_client.get(transaction_url(payment["reference"]))

    assert response.status_code == 200
    assert response.json()["status"] == TransactionStatus.CONFIRMED.value
    assert count_tickets(db_session, payment["reference"]) == 1


def test_sweep_queues_the_missing_ticket_email_once(
    auth_client, email_sender, db_session, gateway, callback_key, monkeypatch
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)
    break_the_queue(monkeypatch)
    auth_client.get(
        CALLBACK_URL,
        params={
            "key": callback_key,
            "orderId": payment["reference"],
            "amount": "50.00",
        },
    )
    monkeypatch.undo()

    assert queue_missing_ticket_emails(db_session) == 1
    assert queue_missing_ticket_emails(db_session) == 0

    emails = ticket_emails(db_session)
    assert len(emails) == 1
    assert f"cid:{TICKET_QR_CID}" in emails[0].html_body


def test_sweep_ignores_old_tickets(
    auth_client, email_sender, db_session, gateway, callback_key, monkeypatch
):
    payment = start_payment(auth_client, email_sender, db_session, gateway)
    break_the_queue(monkeypatch)
    auth_client.get(
        CALLBACK_URL,
        params={
            "key": callback_key,
            "orderId": payment["reference"],
            "amount": "50.00",
        },
    )
    monkeypatch.undo()
    ticket = db_session.scalar(
        select(Ticket).where(Ticket.transaction_reference == payment["reference"])
    )
    ticket.paid_at = datetime.now(UTC) - timedelta(days=30)
    db_session.commit()

    assert queue_missing_ticket_emails(db_session) == 0
    assert ticket_emails(db_session) == []


def test_fifth_modality_issues_a_ticket(
    auth_client, email_sender, db_session, gateway, callback_key
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    response = auth_client.post(
        INITIATE_URL,
        json={"ticket_tier": TicketTier.GERAL_REFEICOES.value, "phone": "912345678"},
    )
    reference = response.json()["reference"]

    auth_client.get(
        CALLBACK_URL,
        params={"key": callback_key, "orderId": reference, "amount": "65.00"},
    )

    ticket = db_session.scalar(
        select(Ticket).where(Ticket.transaction_reference == reference)
    )
    assert ticket.ticket_tier == TicketTier.GERAL_REFEICOES
    assert len(ticket_emails(db_session)) == 1
