from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import ACCESS_COOKIE_NAME, hash_password
from app.domains.payments.gateway import (
    IfThenPayMBWayGateway,
    MBWayPayment,
    PaymentGatewayError,
    SimulatedMBWayGateway,
    get_mbway_gateway,
)
from app.domains.payments.models import (
    TicketTier,
    Transaction,
    TransactionStatus,
)
from app.domains.users.models import User
from app.main import app
from tests.helpers import (
    INITIATE_URL,
    access_claims,
    authenticate,
    encode_claims,
    register_user,
    seed_ticket_tiers,
    transaction_url,
)

INITIATE = {"ticket_tier": TicketTier.GERAL.value, "phone": "912345678"}


class FakeGateway:
    name = "fake"

    def __init__(self):
        self.create_calls: list[dict] = []
        self.status_calls: list[tuple[str, str | None]] = []
        self.status = TransactionStatus.PENDING
        self.provider_reference = "TX-1"
        self.create_error: Exception | None = None
        self.status_error: Exception | None = None

    def create_payment(self, *, reference, amount_cents, phone, email) -> MBWayPayment:
        self.create_calls.append(
            {
                "reference": reference,
                "amount_cents": amount_cents,
                "phone": phone,
                "email": email,
            }
        )
        if self.create_error is not None:
            raise self.create_error
        return MBWayPayment(provider_reference=self.provider_reference)

    def get_status(self, *, reference, provider_reference) -> TransactionStatus:
        self.status_calls.append((reference, provider_reference))
        if self.status_error is not None:
            raise self.status_error
        return self.status


@pytest.fixture
def gateway():
    fake = FakeGateway()
    app.dependency_overrides[get_mbway_gateway] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_mbway_gateway, None)


def test_initiate_requires_authentication(auth_client):
    response = auth_client.post(INITIATE_URL, json=INITIATE)

    assert response.status_code == 401


def test_initiate_requires_verified_email(auth_client, email_sender, db_session):
    register_user(auth_client, email_sender, email="pending@example.com")
    user = db_session.scalar(select(User).where(User.email == "pending@example.com"))
    auth_client.cookies.set(
        ACCESS_COOKIE_NAME, encode_claims(access_claims(user.id, user.token_version))
    )
    seed_ticket_tiers(db_session)

    response = auth_client.post(INITIATE_URL, json=INITIATE)

    assert response.status_code == 403


def test_initiate_uses_the_server_side_price(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    response = auth_client.post(
        INITIATE_URL,
        json={"ticket_tier": TicketTier.GERAL.value, "phone": "912345678"},
    )

    assert response.status_code == 201
    assert response.json()["amount_cents"] == 5000
    assert gateway.create_calls[0]["amount_cents"] == 5000


def test_client_cannot_override_the_amount(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    response = auth_client.post(
        INITIATE_URL,
        json={
            "ticket_tier": TicketTier.GERAL.value,
            "phone": "912345678",
            "amount_cents": 1,
            "price": 1,
        },
    )

    assert response.status_code == 201
    assert response.json()["amount_cents"] == 5000
    assert gateway.create_calls[0]["amount_cents"] == 5000


def test_initiate_multiplies_price_by_quantity(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    response = auth_client.post(
        INITIATE_URL,
        json={
            "ticket_tier": TicketTier.GERAL.value,
            "phone": "912345678",
            "quantity": 3,
        },
    )

    assert response.status_code == 201
    assert response.json()["amount_cents"] == 15000


def test_initiate_creates_a_pending_transaction(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    body = auth_client.post(INITIATE_URL, json=INITIATE).json()

    stored = db_session.scalar(
        select(Transaction).where(Transaction.reference == body["reference"])
    )
    assert stored is not None
    assert stored.status is TransactionStatus.PENDING
    assert stored.amount_cents == 5000
    assert stored.phone == "912345678"
    assert stored.provider == "fake"
    assert stored.provider_reference == "TX-1"


def test_initiate_returns_reference_and_expiry(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    body = auth_client.post(INITIATE_URL, json=INITIATE).json()

    assert body["reference"].startswith("ENEI-")
    assert len(body["reference"]) <= 15
    assert body["status"] == "pending"
    assert body["currency"] == "EUR"
    created = datetime.fromisoformat(body["created_at"])
    expires = datetime.fromisoformat(body["expires_at"])
    assert (
        timedelta(minutes=3, seconds=50)
        < (expires - created)
        < timedelta(minutes=4, seconds=5)
    )


def test_references_are_unique(auth_client, email_sender, db_session, gateway):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    first = auth_client.post(INITIATE_URL, json=INITIATE).json()["reference"]
    second = auth_client.post(INITIATE_URL, json=INITIATE).json()["reference"]

    assert first != second


def test_student_tier_requires_a_verified_student(
    auth_client, email_sender, db_session, gateway, monkeypatch
):
    monkeypatch.setattr(settings, "STUDENT_EMAIL_DOMAINS", [])
    user = authenticate(auth_client, email_sender, db_session, email="ana@gmail.com")
    seed_ticket_tiers(db_session)

    response = auth_client.post(
        INITIATE_URL,
        json={"ticket_tier": TicketTier.ACESSO.value, "phone": "912345678"},
    )

    assert response.status_code == 403
    assert user.student_verification_status.value == "pending"


def test_non_student_tier_is_allowed_without_student_verification(
    auth_client, email_sender, db_session, gateway, monkeypatch
):
    monkeypatch.setattr(settings, "STUDENT_EMAIL_DOMAINS", [])
    authenticate(auth_client, email_sender, db_session, email="ana@gmail.com")
    seed_ticket_tiers(db_session)

    response = auth_client.post(
        INITIATE_URL,
        json={"ticket_tier": TicketTier.GERAL.value, "phone": "912345678"},
    )

    assert response.status_code == 201


def test_student_tier_is_allowed_for_a_verified_student(
    auth_client, email_sender, db_session, gateway, monkeypatch
):
    monkeypatch.setattr(settings, "STUDENT_EMAIL_DOMAINS", ["student.ualg.pt"])
    authenticate(
        auth_client,
        email_sender,
        db_session,
        email="ana@student.ualg.pt",
    )
    seed_ticket_tiers(db_session)

    response = auth_client.post(
        INITIATE_URL,
        json={"ticket_tier": TicketTier.ACESSO.value, "phone": "912345678"},
    )

    assert response.status_code == 201


@pytest.mark.parametrize("phone", ["123", "812345678", "abc", "9123456789"])
def test_initiate_rejects_invalid_phone(
    auth_client, email_sender, db_session, gateway, phone
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    response = auth_client.post(
        INITIATE_URL, json={"ticket_tier": TicketTier.GERAL.value, "phone": phone}
    )

    assert response.status_code == 422


def test_initiate_normalizes_phone_number(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    response = auth_client.post(
        INITIATE_URL,
        json={"ticket_tier": TicketTier.GERAL.value, "phone": "+351 912 345 678"},
    )

    assert response.status_code == 201
    assert response.json()["phone"] == "912345678"
    assert gateway.create_calls[0]["phone"] == "912345678"


def test_initiate_rejects_unknown_tier(auth_client, email_sender, db_session, gateway):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    response = auth_client.post(
        INITIATE_URL, json={"ticket_tier": "vip", "phone": "912345678"}
    )

    assert response.status_code == 422


def test_initiate_respects_inventory_limit(
    auth_client, email_sender, db_session, gateway
):
    user = authenticate(auth_client, email_sender, db_session)
    tickets = seed_ticket_tiers(db_session)
    ticket = tickets[TicketTier.GERAL]
    ticket.inventory_limit = 1
    db_session.add(
        Transaction(
            reference="ENEI-0000000001",
            user_id=user.id,
            ticket_id=ticket.id,
            amount_cents=5000,
            quantity=1,
            status=TransactionStatus.PENDING,
            phone="910000000",
            provider="seed",
            expires_at=datetime.now(UTC) + timedelta(minutes=4),
        )
    )
    db_session.commit()

    response = auth_client.post(INITIATE_URL, json=INITIATE)

    assert response.status_code == 409


def test_gateway_failure_marks_transaction_failed(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    gateway.create_error = PaymentGatewayError("provider down")

    response = auth_client.post(INITIATE_URL, json=INITIATE)

    assert response.status_code == 502
    stored = db_session.scalar(select(Transaction))
    assert stored.status is TransactionStatus.FAILED


def test_get_status_returns_the_transaction(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    reference = auth_client.post(INITIATE_URL, json=INITIATE).json()["reference"]

    response = auth_client.get(transaction_url(reference))

    assert response.status_code == 200
    body = response.json()
    assert body["reference"] == reference
    assert body["status"] == "pending"
    assert body["ticket_tier"] == "geral"
    assert body["amount_cents"] == 5000


def test_get_status_requires_authentication(auth_client):
    response = auth_client.get(transaction_url("ENEI-0000000001"))

    assert response.status_code == 401


def test_get_status_hides_other_users_transaction(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    tickets = seed_ticket_tiers(db_session)
    other = User(
        name="Other User",
        email="other@example.com",
        password_hash=hash_password("Password123!"),
    )
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)
    transaction = Transaction(
        reference="ENEI-0000000002",
        user_id=other.id,
        ticket_id=tickets[TicketTier.GERAL].id,
        amount_cents=5000,
        quantity=1,
        status=TransactionStatus.CONFIRMED,
        phone="910000000",
        provider="seed",
        expires_at=datetime.now(UTC) + timedelta(minutes=4),
    )
    db_session.add(transaction)
    db_session.commit()

    response = auth_client.get(transaction_url("ENEI-0000000002"))

    assert response.status_code == 404


def test_expired_pending_transaction_is_marked_expired(
    auth_client, email_sender, db_session, gateway
):
    user = authenticate(auth_client, email_sender, db_session)
    tickets = seed_ticket_tiers(db_session)
    db_session.add(
        Transaction(
            reference="ENEI-0000000003",
            user_id=user.id,
            ticket_id=tickets[TicketTier.GERAL].id,
            amount_cents=5000,
            quantity=1,
            status=TransactionStatus.PENDING,
            phone="910000000",
            provider="seed",
            expires_at=datetime.now(UTC) - timedelta(seconds=5),
        )
    )
    db_session.commit()

    response = auth_client.get(transaction_url("ENEI-0000000003"))

    assert response.status_code == 200
    assert response.json()["status"] == "expired"
    stored = db_session.scalar(
        select(Transaction).where(Transaction.reference == "ENEI-0000000003")
    )
    assert stored.status is TransactionStatus.EXPIRED


def test_confirmed_transaction_is_returned(
    auth_client, email_sender, db_session, gateway
):
    user = authenticate(auth_client, email_sender, db_session)
    tickets = seed_ticket_tiers(db_session)
    db_session.add(
        Transaction(
            reference="ENEI-0000000004",
            user_id=user.id,
            ticket_id=tickets[TicketTier.GERAL].id,
            amount_cents=5000,
            quantity=1,
            status=TransactionStatus.CONFIRMED,
            phone="910000000",
            provider="seed",
            expires_at=datetime.now(UTC) + timedelta(minutes=4),
        )
    )
    db_session.commit()

    response = auth_client.get(transaction_url("ENEI-0000000004"))

    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"


def test_get_status_polls_the_provider_and_persists_confirmed(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    reference = auth_client.post(INITIATE_URL, json=INITIATE).json()["reference"]
    gateway.status = TransactionStatus.CONFIRMED

    response = auth_client.get(transaction_url(reference))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["confirmed_at"] is not None
    assert gateway.status_calls == [(reference, "TX-1")]
    stored = db_session.scalar(
        select(Transaction).where(Transaction.reference == reference)
    )
    assert stored.status is TransactionStatus.CONFIRMED
    assert stored.confirmed_at is not None


def test_get_status_persists_provider_failed(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    reference = auth_client.post(INITIATE_URL, json=INITIATE).json()["reference"]
    gateway.status = TransactionStatus.FAILED

    response = auth_client.get(transaction_url(reference))

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    stored = db_session.scalar(
        select(Transaction).where(Transaction.reference == reference)
    )
    assert stored.status is TransactionStatus.FAILED


def test_get_status_persists_provider_expired(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    reference = auth_client.post(INITIATE_URL, json=INITIATE).json()["reference"]
    gateway.status = TransactionStatus.EXPIRED

    response = auth_client.get(transaction_url(reference))

    assert response.status_code == 200
    assert response.json()["status"] == "expired"
    stored = db_session.scalar(
        select(Transaction).where(Transaction.reference == reference)
    )
    assert stored.status is TransactionStatus.EXPIRED


def test_pending_status_is_kept_until_the_window_passes(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    reference = auth_client.post(INITIATE_URL, json=INITIATE).json()["reference"]
    gateway.status = TransactionStatus.PENDING

    response = auth_client.get(transaction_url(reference))

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    stored = db_session.scalar(
        select(Transaction).where(Transaction.reference == reference)
    )
    assert stored.status is TransactionStatus.PENDING


def test_local_expiry_applies_when_the_provider_still_says_pending(
    auth_client, email_sender, db_session, gateway
):
    user = authenticate(auth_client, email_sender, db_session)
    tickets = seed_ticket_tiers(db_session)
    db_session.add(
        Transaction(
            reference="ENEI-0000000007",
            user_id=user.id,
            ticket_id=tickets[TicketTier.GERAL].id,
            amount_cents=5000,
            quantity=1,
            status=TransactionStatus.PENDING,
            phone="910000000",
            provider="fake",
            provider_reference="TX-7",
            expires_at=datetime.now(UTC) - timedelta(seconds=5),
        )
    )
    db_session.commit()

    response = auth_client.get(transaction_url("ENEI-0000000007"))

    assert response.status_code == 200
    assert response.json()["status"] == "expired"
    assert gateway.status_calls == [("ENEI-0000000007", "TX-7")]
    stored = db_session.scalar(
        select(Transaction).where(Transaction.reference == "ENEI-0000000007")
    )
    assert stored.status is TransactionStatus.EXPIRED


def test_finalized_transactions_are_not_synced_with_the_provider_again(
    auth_client, email_sender, db_session, gateway
):
    user = authenticate(auth_client, email_sender, db_session)
    tickets = seed_ticket_tiers(db_session)
    db_session.add(
        Transaction(
            reference="ENEI-0000000008",
            user_id=user.id,
            ticket_id=tickets[TicketTier.GERAL].id,
            amount_cents=5000,
            quantity=1,
            status=TransactionStatus.CONFIRMED,
            phone="910000000",
            provider="fake",
            provider_reference="TX-8",
            confirmed_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) - timedelta(seconds=5),
        )
    )
    db_session.commit()

    response = auth_client.get(transaction_url("ENEI-0000000008"))

    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"
    assert gateway.status_calls == []


def test_gateway_error_during_poll_keeps_the_stored_status(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    reference = auth_client.post(INITIATE_URL, json=INITIATE).json()["reference"]
    gateway.status_error = PaymentGatewayError("provider down")

    response = auth_client.get(transaction_url(reference))

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    stored = db_session.scalar(
        select(Transaction).where(Transaction.reference == reference)
    )
    assert stored.status is TransactionStatus.PENDING


def test_simulated_gateway_is_used_without_an_api_key(monkeypatch):
    monkeypatch.setattr(settings, "MBWAY_KEY", "")
    assert isinstance(get_mbway_gateway(), SimulatedMBWayGateway)


def test_real_gateway_is_used_when_a_key_is_configured(monkeypatch):
    monkeypatch.setattr(settings, "MBWAY_KEY", "MBW-123456")
    assert isinstance(get_mbway_gateway(), IfThenPayMBWayGateway)


def test_simulated_gateway_never_returns_confirmed():
    result = SimulatedMBWayGateway().create_payment(
        reference="ENEI-0000000005",
        amount_cents=5000,
        phone="912345678",
        email="ana@example.com",
    )
    assert result.status is TransactionStatus.PENDING
    assert result.provider_reference


def test_if_then_pay_gateway_sends_the_documented_payload():
    posted: list[tuple[str, dict, dict]] = []

    def fake_post(url, payload, headers):
        posted.append((url, payload, headers))
        return {"transactionId": "itp-1", "status": "pending"}

    client = IfThenPayMBWayGateway(
        mbway_key="MBW-123456",
        base_url="https://api.ifthenpay.com/spg/payment/mbway",
        timeout_seconds=5,
        http_post=fake_post,
    )

    payment = client.create_payment(
        reference="ENEI-0000000006",
        amount_cents=1050,
        phone="912345678",
        email="ana@example.com",
    )

    url, payload, _ = posted[0]
    assert url == "https://api.ifthenpay.com/spg/payment/mbway"
    assert payload["mbWayKey"] == "MBW-123456"
    assert payload["orderId"] == "ENEI-0000000006"
    assert payload["amount"] == "10.50"
    assert payload["mobileNumber"] == "351#912345678"
    assert payload["email"] == "ana@example.com"
    assert payment.provider_reference == "itp-1"
