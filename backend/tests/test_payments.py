import logging
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import ACCESS_COOKIE_NAME, hash_password
from app.domains.payments.gateway import (
    IfThenPayMBWayGateway,
    MBWayPayment,
    PaymentGatewayError,
    SimulatedMBWayGateway,
    UnrecognisedStatusError,
    get_mbway_gateway,
)
from app.domains.payments.models import (
    TicketTier,
    Transaction,
    TransactionStatus,
)
from app.domains.payments.schemas import PaymentInitiateRequest
from app.domains.payments.service import TicketSoldOutError, initiate_payment
from app.domains.tickets.models import PaymentStatus, Ticket
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

    def create_payment(
        self, *, reference, amount_cents, phone, email, description
    ) -> MBWayPayment:
        self.create_calls.append(
            {
                "reference": reference,
                "amount_cents": amount_cents,
                "phone": phone,
                "email": email,
                "description": description,
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


def test_initiate_returns_503_while_the_ticket_office_is_closed(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    tickets = seed_ticket_tiers(db_session)
    tickets[TicketTier.GERAL].price_cents = None
    db_session.commit()

    response = auth_client.post(INITIATE_URL, json=INITIATE)

    assert response.status_code == 503
    assert db_session.scalar(select(Transaction)) is None
    assert gateway.create_calls == []


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


def test_the_provider_is_told_which_event_and_product_the_payment_is_for(
    auth_client, email_sender, db_session, gateway
):
    """The Stripe account is shared: each charge says ``ENEI - <product name>``."""
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    response = auth_client.post(
        INITIATE_URL,
        json={"ticket_tier": TicketTier.GERAL.value, "phone": "912345678"},
    )

    assert response.status_code == 201
    assert gateway.create_calls[0]["description"] == "ENEI - Passe geral"


@pytest.mark.parametrize("tier", list(TicketTier))
def test_every_modality_has_its_own_payment_description(tier):
    from app.domains.payments.service import payment_description
    from app.domains.payments.tiers import TIER_SPECS

    assert payment_description(tier) == f"ENEI - {TIER_SPECS[tier].name}"
    assert len({payment_description(other) for other in TicketTier}) == len(
        list(TicketTier)
    )


def test_a_non_student_can_buy_the_general_pass_with_meals(
    auth_client, email_sender, db_session, gateway
):
    """The fifth modality is for non-students: it needs no student verification."""
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    response = auth_client.post(
        INITIATE_URL,
        json={"ticket_tier": TicketTier.GERAL_REFEICOES.value, "phone": "912345678"},
    )

    assert response.status_code == 201
    assert response.json()["ticket_tier"] == "geral_refeicoes"
    assert response.json()["amount_cents"] == 6500
    assert gateway.create_calls[0]["amount_cents"] == 6500


def test_a_student_modality_still_needs_student_verification(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    response = auth_client.post(
        INITIATE_URL,
        json={"ticket_tier": TicketTier.REFEICOES.value, "phone": "912345678"},
    )

    assert response.status_code == 403


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


def test_initiate_only_accepts_a_single_ticket(auth_client, email_sender, db_session):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    response = auth_client.post(INITIATE_URL, json={**INITIATE, "quantity": 3})

    assert response.status_code == 422


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
    authenticate(auth_client, email_sender, db_session, email="rui@example.com")
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
    assert user.student_verification_status.value == "none"


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


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        ("123456789", "123456789"),
        ("123 456 789", "123456789"),
        ("PT123456789", "123456789"),
        ("123.456.789", "123456789"),
        ("501964843", "501964843"),
    ],
)
def test_initiate_stores_the_nif_as_nine_digits(
    auth_client, email_sender, db_session, gateway, typed, stored
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    response = auth_client.post(INITIATE_URL, json={**INITIATE, "nif": typed})

    assert response.status_code == 201
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == response.json()["reference"])
    )
    assert transaction is not None
    assert transaction.nif == stored


@pytest.mark.parametrize("nif", [None, "", "   "])
def test_initiate_does_not_need_a_nif(
    auth_client, email_sender, db_session, gateway, nif
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    body = {**INITIATE} if nif is None else {**INITIATE, "nif": nif}
    response = auth_client.post(INITIATE_URL, json=body)

    assert response.status_code == 201
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == response.json()["reference"])
    )
    assert transaction is not None
    assert transaction.nif is None


@pytest.mark.parametrize(
    "nif",
    [
        "12345678",
        "1234567890",
        "12345678a",
        "123456780",
        "PT12345",
        "PT",
        "9" * 9,
        # digits of other scripts pass `\\d` and `int()`: they must not be stored
        "".join(chr(0x660 + int(c)) for c in "123456789"),
        "".join(chr(0xFF10 + int(c)) for c in "123456789"),
        # check digit fine but a leading digit the tax authority never assigns
        "000000000",
        "400000008",
        "1" * 33,
        "123456789" + "0" * 100,
    ],
)
def test_initiate_rejects_an_invalid_nif_without_reserving_a_seat(
    auth_client, email_sender, db_session, gateway, nif
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    response = auth_client.post(INITIATE_URL, json={**INITIATE, "nif": nif})

    assert response.status_code == 422
    assert db_session.scalar(select(func.count()).select_from(Transaction)) == 0
    assert gateway.create_calls == []


def _nif_of(db_session, reference):
    db_session.expire_all()
    return db_session.scalar(
        select(Transaction.nif).where(Transaction.reference == reference)
    )


@pytest.mark.parametrize("ended", [TransactionStatus.FAILED, TransactionStatus.EXPIRED])
def test_the_nif_lives_with_the_transaction_like_the_phone(
    auth_client, email_sender, db_session, gateway, ended
):
    """It is kept as long as the transaction exists: a failed or expired payment does
    not erase it, only removing the whole purchase record does."""
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    reference = auth_client.post(
        INITIATE_URL, json={**INITIATE, "nif": "123456789"}
    ).json()["reference"]

    gateway.status = ended
    auth_client.get(transaction_url(reference))

    stored = db_session.scalar(
        select(Transaction).where(Transaction.reference == reference)
    )
    assert stored.status is ended
    assert stored.nif == "123456789"
    assert stored.phone == "912345678"


def test_the_nif_is_kept_when_the_provider_refuses_to_start_the_payment(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    gateway.create_error = PaymentGatewayError("provider down")

    response = auth_client.post(INITIATE_URL, json={**INITIATE, "nif": "123456789"})

    assert response.status_code == 502
    stored = db_session.scalar(select(Transaction))
    assert stored.status is TransactionStatus.FAILED
    assert stored.nif == "123456789"


def test_the_nif_is_kept_while_the_payment_waits_and_once_it_is_paid(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    reference = auth_client.post(
        INITIATE_URL, json={**INITIATE, "nif": "123456789"}
    ).json()["reference"]

    auth_client.get(transaction_url(reference))  # still pending at the provider
    assert _nif_of(db_session, reference) == "123456789"

    gateway.status = TransactionStatus.CONFIRMED
    auth_client.get(transaction_url(reference))
    assert db_session.scalar(select(Ticket)) is not None
    assert _nif_of(db_session, reference) == "123456789"


def test_the_nif_is_never_returned_by_the_api(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    created = auth_client.post(INITIATE_URL, json={**INITIATE, "nif": "123456789"})
    reference = created.json()["reference"]
    read = auth_client.get(transaction_url(reference))

    assert "nif" not in created.json()
    assert "nif" not in read.json()
    assert "123456789" not in created.text + read.text


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
    settings.TICKET_STOCK_LIMIT = 1
    db_session.add(
        Transaction(
            reference="ENEI-0000000001",
            user_id=user.id,
            ticket_tier_id=ticket.id,
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


def test_get_status_is_rate_limited_per_user(
    auth_client, email_sender, db_session, gateway, monkeypatch
):
    monkeypatch.setattr(settings, "RATE_LIMIT_PAYMENT_STATUS_PER_MINUTE", 2)
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    reference = auth_client.post(INITIATE_URL, json=INITIATE).json()["reference"]

    assert auth_client.get(transaction_url(reference)).status_code == 200
    assert auth_client.get(transaction_url(reference)).status_code == 200
    assert auth_client.get(transaction_url(reference)).status_code == 429


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
        ticket_tier_id=tickets[TicketTier.GERAL].id,
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


def test_a_pending_transaction_past_its_deadline_stays_pending_while_the_provider_waits(
    auth_client, email_sender, db_session, gateway
):
    """The deadline is the time the person has to approve; the seat is released only
    when the provider ends the payment."""
    user = authenticate(auth_client, email_sender, db_session)
    tickets = seed_ticket_tiers(db_session)
    db_session.add(
        Transaction(
            reference="ENEI-0000000003",
            user_id=user.id,
            ticket_tier_id=tickets[TicketTier.GERAL].id,
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
    assert response.json()["status"] == "pending"
    stored = db_session.scalar(
        select(Transaction).where(Transaction.reference == "ENEI-0000000003")
    )
    assert stored.status is TransactionStatus.PENDING


def test_confirmed_transaction_is_returned(
    auth_client, email_sender, db_session, gateway
):
    user = authenticate(auth_client, email_sender, db_session)
    tickets = seed_ticket_tiers(db_session)
    db_session.add(
        Transaction(
            reference="ENEI-0000000004",
            user_id=user.id,
            ticket_tier_id=tickets[TicketTier.GERAL].id,
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


def _let_the_deadline_pass(db_session, reference: str) -> Transaction:
    stored = db_session.scalar(
        select(Transaction).where(Transaction.reference == reference)
    )
    stored.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()
    return stored


def test_a_waiting_payment_keeps_its_seat_after_its_deadline_until_the_provider_answers(
    auth_client, email_sender, db_session, gateway
):
    """Like a shop: what is reserved for a waiting payment is not sold to anyone."""
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    settings.TICKET_STOCK_LIMIT = 1
    db_session.commit()
    reference = auth_client.post(INITIATE_URL, json=INITIATE).json()["reference"]
    _let_the_deadline_pass(db_session, reference)
    other = User(
        name="Rui Costa",
        email="rui@example.com",
        password_hash=hash_password("Password123!"),
    )
    db_session.add(other)
    db_session.commit()
    payload = PaymentInitiateRequest(ticket_tier=TicketTier.GERAL, phone="912345678")

    # The provider still says it is waiting: the seat is not for sale.
    with pytest.raises(TicketSoldOutError):
        initiate_payment(db_session, other, payload, gateway)

    # The person abandoned it and nobody polls. The provider closes it, and the
    # next buyer's request finds that out and gets the seat.
    gateway.status = TransactionStatus.EXPIRED
    initiate_payment(db_session, other, payload, gateway)
    assert (
        db_session.scalar(
            select(Transaction.status).where(Transaction.reference == reference)
        )
        is TransactionStatus.EXPIRED
    )


def test_a_sale_with_stock_left_does_not_ask_the_provider_about_other_payments(
    auth_client, email_sender, db_session, gateway
):
    user = authenticate(auth_client, email_sender, db_session)
    tiers = seed_ticket_tiers(db_session)
    settings.TICKET_STOCK_LIMIT = 5
    other = User(
        name="Rui Costa",
        email="rui@example.com",
        password_hash=hash_password("Password123!"),
    )
    db_session.add(other)
    db_session.flush()
    db_session.add(
        Transaction(
            reference="ENEI-OVERDUE001",
            user_id=other.id,
            ticket_tier_id=tiers[TicketTier.GERAL].id,
            amount_cents=5000,
            quantity=1,
            status=TransactionStatus.PENDING,
            phone="910000000",
            provider="fake",
            provider_reference="TX-OLD",
            expires_at=datetime.now(UTC) - timedelta(minutes=5),
        )
    )
    db_session.commit()
    assert user.id != other.id

    assert auth_client.post(INITIATE_URL, json=INITIATE).status_code == 201

    assert gateway.status_calls == []


def test_get_status_keeps_a_waiting_payment_pending_after_its_deadline(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    reference = auth_client.post(INITIATE_URL, json=INITIATE).json()["reference"]
    _let_the_deadline_pass(db_session, reference)

    assert auth_client.get(transaction_url(reference)).json()["status"] == "pending"


def test_a_new_payment_asks_the_provider_about_the_one_that_ran_out(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    first = auth_client.post(INITIATE_URL, json=INITIATE).json()["reference"]
    _let_the_deadline_pass(db_session, first)

    # Still waiting at the provider: one payment at a time.
    assert auth_client.post(INITIATE_URL, json=INITIATE).status_code == 409

    # The provider closed it: a new one is allowed.
    gateway.status = TransactionStatus.EXPIRED
    assert auth_client.post(INITIATE_URL, json=INITIATE).status_code == 201
    assert (
        db_session.scalar(
            select(Transaction.status).where(Transaction.reference == first)
        )
        is TransactionStatus.EXPIRED
    )


def test_a_new_payment_finds_out_that_the_old_one_was_paid(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    first = auth_client.post(INITIATE_URL, json=INITIATE).json()["reference"]
    _let_the_deadline_pass(db_session, first)
    gateway.status = TransactionStatus.CONFIRMED

    response = auth_client.post(INITIATE_URL, json=INITIATE)

    assert response.status_code == 409
    assert "already have a ticket" in response.json()["detail"]
    assert db_session.scalar(select(func.count()).select_from(Ticket)) == 1


def _seed_pending(db_session, user, *, reference, provider_reference, late_by):
    """A waiting payment whose deadline passed `late_by` ago."""
    tiers = seed_ticket_tiers(db_session)
    db_session.add(
        Transaction(
            reference=reference,
            user_id=user.id,
            ticket_tier_id=tiers[TicketTier.GERAL].id,
            amount_cents=5000,
            quantity=1,
            status=TransactionStatus.PENDING,
            phone="910000000",
            provider="fake",
            provider_reference=provider_reference,
            expires_at=datetime.now(UTC) - late_by,
        )
    )
    db_session.commit()


def _status_of(db_session, reference):
    db_session.expire_all()
    return db_session.scalar(
        select(Transaction.status).where(Transaction.reference == reference)
    )


def test_an_unreadable_answer_keeps_the_seat_for_a_while_then_gives_it_up(
    auth_client, email_sender, db_session, gateway, caplog
):
    """The provider answers something we cannot read: not "waiting for ever"."""
    user = authenticate(auth_client, email_sender, db_session)
    _seed_pending(
        db_session,
        user,
        reference="ENEI-0000000011",
        provider_reference="TX-11",
        late_by=timedelta(minutes=10),
    )
    gateway.status_error = UnrecognisedStatusError("unrecognised status 'x'")

    assert (
        auth_client.get(transaction_url("ENEI-0000000011")).json()["status"]
        == "pending"
    )

    stored = db_session.scalar(
        select(Transaction).where(Transaction.reference == "ENEI-0000000011")
    )
    stored.expires_at = datetime.now(UTC) - timedelta(
        seconds=settings.MBWAY_UNRESOLVED_MAX_WAIT_SECONDS + 60
    )
    db_session.commit()
    with caplog.at_level(logging.ERROR, logger="app.domains.payments.service"):
        response = auth_client.get(transaction_url("ENEI-0000000011"))

    assert response.json()["status"] == "expired"
    assert "could not be resolved with the provider" in caplog.text


def test_a_payment_without_a_provider_reference_is_not_asked_about_and_gives_up(
    auth_client, email_sender, db_session, gateway
):
    """The process died between asking the provider and saving its reference."""
    user = authenticate(auth_client, email_sender, db_session)
    _seed_pending(
        db_session,
        user,
        reference="ENEI-0000000012",
        provider_reference=None,
        late_by=timedelta(minutes=10),
    )

    assert (
        auth_client.get(transaction_url("ENEI-0000000012")).json()["status"]
        == "pending"
    )
    assert gateway.status_calls == []

    stored = db_session.scalar(
        select(Transaction).where(Transaction.reference == "ENEI-0000000012")
    )
    stored.expires_at = datetime.now(UTC) - timedelta(
        seconds=settings.MBWAY_UNRESOLVED_MAX_WAIT_SECONDS + 60
    )
    db_session.commit()

    assert (
        auth_client.get(transaction_url("ENEI-0000000012")).json()["status"]
        == "expired"
    )


def test_a_payment_the_provider_says_is_waiting_is_never_given_up(
    auth_client, email_sender, db_session, gateway
):
    user = authenticate(auth_client, email_sender, db_session)
    _seed_pending(
        db_session,
        user,
        reference="ENEI-0000000013",
        provider_reference="TX-13",
        late_by=timedelta(days=2),
    )

    assert (
        auth_client.get(transaction_url("ENEI-0000000013")).json()["status"]
        == "pending"
    )


def test_an_unreachable_provider_never_makes_a_payment_give_up(
    auth_client, email_sender, db_session, gateway
):
    """An outage is not a payment nobody can resolve: nothing is released."""
    user = authenticate(auth_client, email_sender, db_session)
    _seed_pending(
        db_session,
        user,
        reference="ENEI-0000000014",
        provider_reference="TX-14",
        late_by=timedelta(days=2),
    )
    gateway.status_error = PaymentGatewayError("provider down")

    assert (
        auth_client.get(transaction_url("ENEI-0000000014")).json()["status"]
        == "pending"
    )
    assert _status_of(db_session, "ENEI-0000000014") is TransactionStatus.PENDING


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


def test_a_pending_transaction_stays_pending_when_the_gateway_is_unreachable(
    auth_client, email_sender, db_session, gateway
):
    user = authenticate(auth_client, email_sender, db_session)
    tickets = seed_ticket_tiers(db_session)
    db_session.add(
        Transaction(
            reference="ENEI-0000000007",
            user_id=user.id,
            ticket_tier_id=tickets[TicketTier.GERAL].id,
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
    gateway.status_error = PaymentGatewayError("provider down")

    response = auth_client.get(transaction_url("ENEI-0000000007"))

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert gateway.status_calls == [("ENEI-0000000007", "TX-7")]


def test_finalized_transactions_are_not_synced_with_the_provider_again(
    auth_client, email_sender, db_session, gateway
):
    user = authenticate(auth_client, email_sender, db_session)
    tickets = seed_ticket_tiers(db_session)
    db_session.add(
        Transaction(
            reference="ENEI-0000000008",
            user_id=user.id,
            ticket_tier_id=tickets[TicketTier.GERAL].id,
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


def test_initiate_returns_503_when_payments_are_disabled(
    auth_client, email_sender, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "PAYMENTS_MODE", "off")
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    response = auth_client.post(INITIATE_URL, json=INITIATE)

    assert response.status_code == 503
    assert db_session.scalar(select(Transaction)) is None


def test_simulated_gateway_is_used_without_an_api_key(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENTS_MODE", "simulated")
    assert isinstance(get_mbway_gateway(), SimulatedMBWayGateway)


def test_real_gateway_is_used_when_a_key_is_configured(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENTS_MODE", "live")
    monkeypatch.setattr(settings, "PAYMENTS_PROVIDER", "ifthenpay")
    monkeypatch.setattr(settings, "MBWAY_KEY", "MBW-123456")
    assert isinstance(get_mbway_gateway(), IfThenPayMBWayGateway)


def test_gateway_is_disabled_when_payments_are_off(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENTS_MODE", "off")

    with pytest.raises(HTTPException) as error:
        get_mbway_gateway()

    assert error.value.status_code == 503


def test_simulated_gateway_never_returns_confirmed():
    result = SimulatedMBWayGateway().create_payment(
        reference="ENEI-0000000005",
        amount_cents=5000,
        phone="912345678",
        email="ana@example.com",
        description="ENEI - Passe geral",
    )
    assert result.status is TransactionStatus.PENDING
    assert result.provider_reference


def test_if_then_pay_gateway_sends_the_documented_payload():
    posted: list[tuple[str, dict, dict]] = []

    def fake_post(url, payload, headers):
        posted.append((url, payload, headers))
        return {
            "Status": "000",
            "Message": "Pending",
            "Amount": "10.50",
            "OrderId": "ENEI-0000000006",
            "RequestId": "itp-1",
        }

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
        description="ENEI - Passe geral",
    )

    url, payload, _ = posted[0]
    assert url == "https://api.ifthenpay.com/spg/payment/mbway"
    assert payload["mbWayKey"] == "MBW-123456"
    assert payload["orderId"] == "ENEI-0000000006"
    assert payload["amount"] == "10.50"
    assert payload["mobileNumber"] == "351#912345678"
    assert payload["email"] == "ana@example.com"
    assert payment.provider_reference == "itp-1"


# --- one ticket per person -------------------------------------------------


def _initiate(auth_client):
    return auth_client.post(INITIATE_URL, json=INITIATE)


def test_a_second_payment_is_refused_while_the_first_is_pending(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    assert _initiate(auth_client).status_code == 201

    response = _initiate(auth_client)

    assert response.status_code == 409
    assert len(gateway.create_calls) == 1
    assert db_session.scalar(select(func.count(Transaction.id))) == 1


def test_a_new_payment_is_allowed_after_the_previous_one_expired(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    first = _initiate(auth_client).json()
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == first["reference"])
    )
    transaction.status = TransactionStatus.EXPIRED
    db_session.commit()

    assert _initiate(auth_client).status_code == 201


def test_a_new_payment_is_allowed_after_the_previous_one_failed(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    first = _initiate(auth_client).json()
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == first["reference"])
    )
    transaction.status = TransactionStatus.FAILED
    db_session.commit()

    assert _initiate(auth_client).status_code == 201


def test_payment_is_refused_to_someone_who_already_has_a_ticket(
    auth_client, email_sender, db_session, gateway
):
    user = authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    db_session.add(
        Ticket(
            user_id=user.id,
            transaction_reference="ENEI-0000000001",
            payment_status=PaymentStatus.PAID,
        )
    )
    db_session.commit()

    response = _initiate(auth_client)

    assert response.status_code == 409
    assert gateway.create_calls == []


def test_a_cancelled_ticket_does_not_block_a_new_purchase(
    auth_client, email_sender, db_session, gateway
):
    user = authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    db_session.add(
        Ticket(
            user_id=user.id,
            transaction_reference="ENEI-0000000001",
            payment_status=PaymentStatus.CANCELLED,
        )
    )
    db_session.commit()

    assert _initiate(auth_client).status_code == 201


def test_other_people_are_not_blocked_by_someone_elses_payment(
    auth_client, email_sender, db_session, gateway
):
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    assert _initiate(auth_client).status_code == 201

    authenticate(auth_client, email_sender, db_session, email="rui@example.com")

    assert _initiate(auth_client).status_code == 201
