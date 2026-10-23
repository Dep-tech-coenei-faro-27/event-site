"""End-to-end scenarios of the whole ticket pipeline, through the real routes.

Register/login (a signed cookie), ``POST /payment/initiate``, the status poll, the
ifthenpay callback and ``GET /users/me``, with a provider that tests control
(statuses, failures, amounts) and, on PostgreSQL, bursts of concurrent buyers.
Every request runs in its own database session, as in production.
"""

import os
import threading
import time
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import EmailSender, get_email_sender
from app.core.email.models import EmailOutbox
from app.core.qr import verify_qr_payload
from app.core.security import ACCESS_COOKIE_NAME, hash_password
from app.db.session import get_db
from app.domains.payments.gateway import (
    MBWayPayment,
    PaymentGatewayError,
    SimulatedMBWayGateway,
    UnrecognisedStatusError,
    get_mbway_gateway,
)
from app.domains.payments.models import (
    TicketTier,
    TicketTierPrice,
    Transaction,
    TransactionStatus,
)
from app.domains.tickets.models import PaymentStatus, Ticket
from app.domains.users.models import StudentVerificationStatus, User
from app.main import app
from tests.helpers import (
    DEFAULT_TEST_PRICES,
    access_claims,
    encode_claims,
    seed_ticket_tiers,
)

CALLBACK_KEY = "pipeline-callback-key"
PASSWORD_HASH = hash_password("Password123!")  # hashing is slow: do it once
INITIATE_URL = "/api/payment/initiate"
CALLBACK_URL = "/api/payment/callback"
ME_URL = "/api/users/me"
GERAL = TicketTier.GERAL
requires_postgres = pytest.mark.skipif(
    not (os.environ.get("TEST_DATABASE_URL") or "").startswith("postgresql"),
    reason="needs PostgreSQL (real row locks and concurrent sessions)",
)


class Provider:
    """A scriptable MB WAY: remembers each payment and answers with what we set."""

    name = "scripted"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.status_by_provider_ref: dict[str, TransactionStatus] = {}
        self.create_calls = 0
        self.status_calls = 0
        self.fail_create = False
        self.fail_status = False
        self.fail_status_unrecognised = False
        self.latency = 0.0

    def create_payment(self, *, reference, amount_cents, phone, email) -> MBWayPayment:
        with self._lock:
            self.create_calls += 1
            if self.fail_create:
                raise PaymentGatewayError("provider refused the request")
            provider_ref = f"P-{reference}"
            self.status_by_provider_ref[provider_ref] = TransactionStatus.PENDING
        return MBWayPayment(provider_reference=provider_ref)

    def get_status(self, *, reference, provider_reference) -> TransactionStatus:
        if self.latency:
            time.sleep(self.latency)  # a slow provider, outside the lock
        with self._lock:
            self.status_calls += 1
            if self.fail_status:
                raise PaymentGatewayError("provider unreachable")
            if self.fail_status_unrecognised:
                raise UnrecognisedStatusError("unrecognised status 999")
            return self.status_by_provider_ref.get(
                provider_reference, TransactionStatus.PENDING
            )

    def set_status(self, reference: str, status: TransactionStatus) -> None:
        with self._lock:
            self.status_by_provider_ref[f"P-{reference}"] = status


class World:
    def __init__(self, engine, provider: Provider) -> None:
        self.engine = engine
        self.provider = provider
        self.clients: dict[str, TestClient] = {}

    # --- data -----------------------------------------------------------------
    def session(self) -> Session:
        return Session(bind=self.engine)

    def seed(self, *, limit: int | None = None, tier: TicketTier = GERAL) -> None:
        with self.session() as db:
            seed_ticket_tiers(db)
            if limit is not None:
                row = db.scalar(
                    select(TicketTierPrice).where(TicketTierPrice.tier == tier)
                )
                row.inventory_limit = limit
                db.commit()

    def user(
        self,
        name: str,
        *,
        verified: bool = True,
        student: bool = False,
    ) -> TestClient:
        """A signed-in user: a client carrying a valid access cookie."""
        with self.session() as db:
            user = User(
                name=name.title(),
                email=f"{name}@example.com",
                password_hash=PASSWORD_HASH,
                is_verified=verified,
                email_verified_at=datetime.now(UTC) if verified else None,
                student_verification_status=(
                    StudentVerificationStatus.VERIFIED
                    if student
                    else StudentVerificationStatus.PENDING
                ),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            cookie = encode_claims(access_claims(user.id, user.token_version))
        client = TestClient(app, base_url="https://testserver")
        client.cookies.set(ACCESS_COOKIE_NAME, cookie)
        self.clients[name] = client
        return client

    def anonymous(self) -> TestClient:
        return TestClient(app, base_url="https://testserver")

    # --- routes ---------------------------------------------------------------
    @staticmethod
    def buy(client: TestClient, tier: str = "geral", phone: str = "912345678", **extra):
        return client.post(
            INITIATE_URL, json={"ticket_tier": tier, "phone": phone, **extra}
        )

    @staticmethod
    def poll(client: TestClient, reference: str):
        return client.get(f"/api/payment/transactions/{reference}")

    @staticmethod
    def callback(client: TestClient, reference: str, amount="50.00", key=CALLBACK_KEY):
        params = {"orderId": reference, "amount": amount}
        if key is not None:
            params["key"] = key
        return client.get(CALLBACK_URL, params=params)

    def pays(self, client: TestClient, reference: str, amount="50.00"):
        """The provider marks it paid, then sends the callback."""
        self.provider.set_status(reference, TransactionStatus.CONFIRMED)
        return self.callback(client, reference, amount)

    # --- reads ----------------------------------------------------------------
    def tx(self, reference: str) -> Transaction:
        with self.session() as db:
            return db.scalar(
                select(Transaction).where(Transaction.reference == reference)
            )

    def status(self, reference: str) -> TransactionStatus:
        return self.tx(reference).status

    def tickets_of(self, email: str) -> list[Ticket]:
        with self.session() as db:
            return list(
                db.scalars(
                    select(Ticket)
                    .join(User, User.id == Ticket.user_id)
                    .where(User.email == email)
                )
            )

    def age(self, reference: str, *, minutes: int) -> None:
        """Make the payment's deadline pass, as if `minutes` went by."""
        with self.session() as db:
            row = db.scalar(
                select(Transaction).where(Transaction.reference == reference)
            )
            row.expires_at = datetime.now(UTC) - timedelta(minutes=minutes)
            db.commit()

    def invariants(self, *, limit: int | None = None) -> None:
        """What must hold whatever happened."""
        with self.session() as db:
            active = db.execute(
                select(Ticket.user_id, func.count())
                .where(Ticket.payment_status != PaymentStatus.CANCELLED)
                .group_by(Ticket.user_id)
            ).all()
            assert all(n == 1 for _, n in active), "a person holds two tickets"

            live = select(Ticket).where(
                Ticket.payment_status != PaymentStatus.CANCELLED
            )
            for ticket in db.scalars(live):
                owner_tx = db.scalar(
                    select(Transaction).where(
                        Transaction.reference == ticket.transaction_reference
                    )
                )
                assert owner_tx is not None
                assert owner_tx.status is TransactionStatus.CONFIRMED
                assert ticket.qr_payload
                assert verify_qr_payload(ticket.qr_payload).ticket_id == ticket.id

            # Paid but without a ticket is only allowed as a refund_due.
            lost = db.execute(
                select(Transaction.reference)
                .outerjoin(
                    Ticket, Ticket.transaction_reference == Transaction.reference
                )
                .where(
                    Transaction.status == TransactionStatus.CONFIRMED,
                    Ticket.id.is_(None),
                )
            ).all()
            assert lost == [], f"confirmed without a ticket: {lost}"

            held = db.scalar(
                select(func.coalesce(func.sum(Transaction.quantity), 0)).where(
                    Transaction.status.in_(
                        (TransactionStatus.CONFIRMED, TransactionStatus.PENDING)
                    )
                )
            )
            if limit is not None:
                assert held <= limit, f"{held} seats held for a limit of {limit}"
            sold = db.scalar(
                select(func.count())
                .select_from(Ticket)
                .where(Ticket.payment_status != PaymentStatus.CANCELLED)
            )
            if limit is not None:
                assert sold <= limit, f"{sold} tickets sold for a limit of {limit}"

            people_with_two_open = db.execute(
                select(Transaction.user_id, func.count())
                .where(Transaction.status == TransactionStatus.PENDING)
                .group_by(Transaction.user_id)
            ).all()
            assert all(n == 1 for _, n in people_with_two_open), (
                "a person has two payments waiting"
            )


class NoEmailAllowed(EmailSender):
    """The payment pipeline sends no email (no purchase email in the first version)."""

    def send_html(self, to_email: str, subject: str, html_body: str) -> None:
        raise AssertionError("the payment pipeline must not send email")


@pytest.fixture
def world(test_engine, db_session, monkeypatch):
    """Per-request sessions on the test engine, a scripted provider, a callback key."""
    provider = Provider()

    def request_session():
        session = Session(bind=test_engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = request_session
    app.dependency_overrides[get_mbway_gateway] = lambda: provider
    app.dependency_overrides[get_email_sender] = lambda: NoEmailAllowed()
    monkeypatch.setattr(settings, "MBWAY_CALLBACK_KEY", CALLBACK_KEY)
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    yield World(test_engine, provider)
    app.dependency_overrides.clear()


# --- happy


def test_the_whole_journey_from_purchase_to_qr(world):
    world.seed()
    ana = world.user("ana")

    started = world.buy(ana)
    assert started.status_code == 201
    body = started.json()
    assert body["status"] == "pending"
    assert body["amount_cents"] == DEFAULT_TEST_PRICES[GERAL]
    reference = body["reference"]
    assert reference.startswith("ENEI-") and len(reference) == 15

    assert world.poll(ana, reference).json()["status"] == "pending"
    assert ana.get(ME_URL).json()["qr_code"] is None

    assert world.pays(ana, reference).status_code == 200

    polled = world.poll(ana, reference).json()
    assert polled["status"] == "confirmed" and polled["confirmed_at"]
    qr = ana.get(ME_URL).json()["qr_code"]
    assert (
        qr
        and verify_qr_payload(qr).ticket_id == world.tickets_of("ana@example.com")[0].id
    )
    world.invariants()


def test_the_payment_is_found_by_polling_alone_when_the_callback_never_comes(world):
    world.seed()
    ana = world.user("ana")
    reference = world.buy(ana).json()["reference"]

    world.provider.set_status(reference, TransactionStatus.CONFIRMED)
    assert world.poll(ana, reference).json()["status"] == "confirmed"

    assert ana.get(ME_URL).json()["qr_code"]
    world.invariants()


def test_the_simulated_gateway_runs_the_journey_with_a_clock(
    test_engine, db_session, monkeypatch
):
    """The real simulator, with a controllable clock: pending, then paid by itself."""
    clock = [1_000_000.0]
    simulator = SimulatedMBWayGateway(
        confirm_after_seconds=10, expire_after_seconds=240, now=lambda: clock[0]
    )

    def request_session():
        session = Session(bind=test_engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = request_session
    app.dependency_overrides[get_mbway_gateway] = lambda: simulator
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    try:
        world = World(test_engine, Provider())
        world.seed()
        ana = world.user("ana")
        reference = world.buy(ana).json()["reference"]
        assert world.poll(ana, reference).json()["status"] == "pending"
        clock[0] += 11
        assert world.poll(ana, reference).json()["status"] == "confirmed"
        assert ana.get(ME_URL).json()["qr_code"]
    finally:
        app.dependency_overrides.clear()


# --- stock / reserve


def test_the_third_buyer_sees_sold_out_while_two_payments_wait(world):
    world.seed(limit=2)
    ana, rui, eva = world.user("ana"), world.user("rui"), world.user("eva")

    assert world.buy(ana).status_code == 201
    assert world.buy(rui).status_code == 201
    third = world.buy(eva)

    assert third.status_code == 409
    assert "sold out" in third.json()["detail"]
    world.invariants(limit=2)


def test_a_seat_freed_by_an_expired_payment_goes_to_the_next_buyer(world):
    world.seed(limit=1)
    ana, rui = world.user("ana"), world.user("rui")
    first = world.buy(ana).json()["reference"]
    assert world.buy(rui).status_code == 409

    world.provider.set_status(first, TransactionStatus.EXPIRED)
    assert world.poll(ana, first).json()["status"] == "expired"

    assert world.buy(rui).status_code == 201
    world.invariants(limit=1)


def test_an_abandoned_payment_is_freed_when_someone_else_asks_for_the_last_seat(world):
    """Nobody polls the abandoned payment: the next buyer's request settles it."""
    world.seed(limit=1)
    ana, rui = world.user("ana"), world.user("rui")
    abandoned = world.buy(ana).json()["reference"]
    world.age(abandoned, minutes=10)
    assert world.buy(rui).status_code == 409  # the provider still says it waits

    world.provider.set_status(abandoned, TransactionStatus.EXPIRED)
    assert world.buy(rui).status_code == 201
    assert world.status(abandoned) is TransactionStatus.EXPIRED
    world.invariants(limit=1)


def test_an_abandoned_payment_that_was_paid_is_not_given_away(world):
    """The person closed the page but paid: the provider says so when asked."""
    world.seed(limit=1)
    ana, rui = world.user("ana"), world.user("rui")
    paid = world.buy(ana).json()["reference"]
    world.age(paid, minutes=10)
    world.provider.set_status(paid, TransactionStatus.CONFIRMED)

    sold_out = world.buy(rui)

    assert sold_out.status_code == 409
    assert len(world.tickets_of("ana@example.com")) == 1
    assert world.tickets_of("rui@example.com") == []
    world.invariants(limit=1)


def test_a_payment_past_its_deadline_keeps_its_seat_and_still_gets_the_ticket(world):
    world.seed(limit=1)
    ana, rui = world.user("ana"), world.user("rui")
    reference = world.buy(ana).json()["reference"]
    world.age(reference, minutes=3)

    assert world.poll(ana, reference).json()["status"] == "pending"  # not expired
    assert world.buy(rui).status_code == 409
    assert world.pays(ana, reference).status_code == 200
    assert len(world.tickets_of("ana@example.com")) == 1
    world.invariants(limit=1)


def test_unlimited_modalities_never_ask_the_provider_about_others(world):
    world.seed()  # no inventory limit
    ana, rui = world.user("ana"), world.user("rui")
    old = world.buy(ana).json()["reference"]
    world.age(old, minutes=30)
    world.provider.status_calls = 0

    assert world.buy(rui).status_code == 201
    assert world.provider.status_calls == 0


# --- late / duplicate


def test_a_late_payment_gets_the_ticket_when_there_is_stock(world):
    world.seed(limit=3)
    ana = world.user("ana")
    reference = world.buy(ana).json()["reference"]
    world.provider.set_status(reference, TransactionStatus.EXPIRED)
    assert world.poll(ana, reference).json()["status"] == "expired"

    assert world.callback(ana, reference).status_code == 200  # paid after all

    assert world.status(reference) is TransactionStatus.CONFIRMED
    assert len(world.tickets_of("ana@example.com")) == 1
    world.invariants(limit=3)


def test_a_late_payment_is_refunded_not_sold_when_the_modality_sold_out(world):
    world.seed(limit=1)
    ana, rui = world.user("ana"), world.user("rui")
    late = world.buy(ana).json()["reference"]
    world.provider.set_status(late, TransactionStatus.EXPIRED)
    world.poll(ana, late)  # expired: the seat is free
    taken = world.buy(rui).json()["reference"]
    assert world.pays(rui, taken).status_code == 200

    assert world.callback(ana, late).status_code == 200  # 200 so it stops retrying

    assert world.status(late) is TransactionStatus.REFUND_DUE
    assert world.tickets_of("ana@example.com") == []
    assert len(world.tickets_of("rui@example.com")) == 1
    assert ana.get(ME_URL).json()["qr_code"] is None
    assert world.poll(ana, late).json()["status"] == "refund_due"
    with world.session() as db:
        queued = db.scalars(
            select(EmailOutbox.to_email).where(EmailOutbox.dedupe_key.like("ticket:%"))
        ).all()
    assert queued == ["rui@example.com"]  # nobody gets a ticket email for a refund
    world.invariants(limit=1)


def test_a_refund_due_payment_ignores_repeated_callbacks_and_frees_no_seat(world):
    world.seed(limit=1)
    ana, rui, eva = world.user("ana"), world.user("rui"), world.user("eva")
    late = world.buy(ana).json()["reference"]
    world.provider.set_status(late, TransactionStatus.EXPIRED)
    world.poll(ana, late)
    taken = world.buy(rui).json()["reference"]
    world.pays(rui, taken)
    world.callback(ana, late)

    for _ in range(3):
        assert world.callback(ana, late).status_code == 200

    assert world.status(late) is TransactionStatus.REFUND_DUE
    assert world.buy(eva).status_code == 409  # still sold out
    world.invariants(limit=1)


def test_paying_twice_gives_one_ticket_and_the_second_payment_for_refund(world):
    """The first attempt is declared over, a second is paid, then the first arrives."""
    world.seed()
    ana = world.user("ana")
    first = world.buy(ana).json()["reference"]
    world.provider.set_status(first, TransactionStatus.EXPIRED)
    world.poll(ana, first)
    second = world.buy(ana).json()["reference"]
    assert world.pays(ana, second).status_code == 200

    assert world.callback(ana, first).status_code == 200

    assert world.status(first) is TransactionStatus.REFUND_DUE
    assert world.status(second) is TransactionStatus.CONFIRMED
    assert len(world.tickets_of("ana@example.com")) == 1
    world.invariants()


def test_the_double_click_cannot_start_two_payments(world):
    world.seed()
    ana = world.user("ana")

    first, second = world.buy(ana), world.buy(ana)

    assert (first.status_code, second.status_code) == (201, 409)
    assert "already have a ticket or a payment in progress" in second.json()["detail"]
    with world.session() as db:
        assert db.scalar(select(func.count()).select_from(Transaction)) == 1


def test_a_person_with_a_ticket_cannot_buy_another(world):
    world.seed()
    ana = world.user("ana")
    world.pays(ana, world.buy(ana).json()["reference"])

    again = world.buy(ana)

    assert again.status_code == 409
    world.invariants()


def test_a_cancelled_ticket_frees_the_person_to_buy_again_and_never_comes_back(world):
    world.seed()
    ana = world.user("ana")
    first = world.buy(ana).json()["reference"]
    world.pays(ana, first)
    with world.session() as db:
        ticket = db.scalar(select(Ticket))
        ticket.payment_status = PaymentStatus.CANCELLED
        db.commit()
    assert ana.get(ME_URL).json()["qr_code"] is None

    second = world.buy(ana)
    assert second.status_code == 201
    world.pays(ana, second.json()["reference"])
    new_qr = ana.get(ME_URL).json()["qr_code"]
    assert new_qr

    assert world.callback(ana, first).status_code == 200  # redelivery of the old one
    assert ana.get(ME_URL).json()["qr_code"] == new_qr
    active = [
        t
        for t in world.tickets_of("ana@example.com")
        if t.payment_status is not PaymentStatus.CANCELLED
    ]
    assert len(active) == 1


# --- callback edges


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        ("50.00", 200),
        ("50", 200),
        ("50.0", 200),
        ("050.00", 200),
        ("5000", 400),  # cents instead of euros
        ("49.99", 400),
        ("50.01", 400),
        ("0", 400),
        ("-50.00", 400),
        ("50,00", 400),
        ("", 400),
        ("abc", 400),
        ("NaN", 400),
        ("1e2", 400),
        ("50.00 ", 200),
    ],
)
def test_callback_amount_edge_cases(world, amount, expected):
    world.seed()
    ana = world.user("ana")
    reference = world.buy(ana).json()["reference"]

    response = world.callback(ana, reference, amount=amount)

    assert response.status_code == expected
    confirmed = world.status(reference) is TransactionStatus.CONFIRMED
    assert confirmed is (expected == 200)


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (CALLBACK_KEY, 200),
        ("wrong", 403),
        ("", 403),
        (None, 403),
        (CALLBACK_KEY + " ", 403),
    ],
)
def test_callback_key_edge_cases(world, key, expected):
    world.seed()
    ana = world.user("ana")
    reference = world.buy(ana).json()["reference"]

    assert world.callback(ana, reference, key=key).status_code == expected


def test_callback_for_an_unknown_or_missing_reference(world):
    world.seed()
    anonymous = world.anonymous()

    assert world.callback(anonymous, "ENEI-DOESNOTEXIST").status_code == 404
    assert anonymous.get(CALLBACK_URL, params={"key": CALLBACK_KEY}).status_code == 404
    assert (
        anonymous.get(
            CALLBACK_URL, params={"key": CALLBACK_KEY, "orderId": "' OR 1=1 --"}
        ).status_code
        == 404
    )


def test_callback_accepts_the_current_ifthenpay_parameter_names(world):
    world.seed()
    ana = world.user("ana")
    reference = world.buy(ana).json()["reference"]

    response = world.anonymous().get(
        CALLBACK_URL,
        params={"apk": CALLBACK_KEY, "oid": reference, "val": "50.00", "tid": "x"},
    )

    assert response.status_code == 200
    assert len(world.tickets_of("ana@example.com")) == 1


def test_the_callback_is_idempotent_over_many_deliveries(world):
    world.seed()
    ana = world.user("ana")
    reference = world.buy(ana).json()["reference"]
    world.provider.set_status(reference, TransactionStatus.CONFIRMED)

    codes = {world.callback(ana, reference).status_code for _ in range(6)}

    assert codes == {200}
    assert len(world.tickets_of("ana@example.com")) == 1
    world.invariants()


def test_a_price_change_after_the_purchase_does_not_change_what_was_charged(world):
    world.seed()
    ana = world.user("ana")
    reference = world.buy(ana).json()["reference"]
    with world.session() as db:
        tier = db.scalar(select(TicketTierPrice).where(TicketTierPrice.tier == GERAL))
        tier.price_cents = 9900
        db.commit()

    assert world.callback(ana, reference, amount="99.00").status_code == 400
    assert world.callback(ana, reference, amount="50.00").status_code == 200
    assert world.tx(reference).amount_cents == 5000


# --- provider faults


def test_the_provider_refusing_the_request_gives_a_502_and_allows_a_retry(world):
    world.seed()
    ana = world.user("ana")
    world.provider.fail_create = True

    failed = world.buy(ana)

    assert failed.status_code == 502
    with world.session() as db:
        assert db.scalar(select(Transaction.status)) is TransactionStatus.FAILED
    world.provider.fail_create = False
    assert world.buy(ana).status_code == 201
    world.invariants()


def test_a_502_does_not_hold_a_seat(world):
    world.seed(limit=1)
    ana, rui = world.user("ana"), world.user("rui")
    world.provider.fail_create = True
    assert world.buy(ana).status_code == 502
    world.provider.fail_create = False

    assert world.buy(rui).status_code == 201


def test_an_unreachable_provider_leaves_the_payment_waiting(world):
    world.seed()
    ana = world.user("ana")
    reference = world.buy(ana).json()["reference"]
    world.age(reference, minutes=30)
    world.provider.fail_status = True

    assert world.poll(ana, reference).json()["status"] == "pending"
    assert world.buy(ana).status_code == 409  # still one payment at a time

    world.provider.fail_status = False
    world.pays(ana, reference)
    assert world.poll(ana, reference).json()["status"] == "confirmed"
    world.invariants()


def test_a_payment_declined_by_the_user_frees_the_seat_and_allows_a_retry(world):
    world.seed(limit=1)
    ana = world.user("ana")
    reference = world.buy(ana).json()["reference"]
    world.provider.set_status(reference, TransactionStatus.FAILED)

    assert world.poll(ana, reference).json()["status"] == "failed"

    assert world.buy(ana).status_code == 201
    world.invariants(limit=1)


# --- request validation


@pytest.mark.parametrize(
    "payload",
    [
        {"ticket_tier": "geral", "phone": "812345678"},
        {"ticket_tier": "geral", "phone": "91234567"},
        {"ticket_tier": "geral", "phone": ""},
        {"ticket_tier": "geral", "phone": "abc"},
        {"ticket_tier": "vip", "phone": "912345678"},
        {"phone": "912345678"},
        {"ticket_tier": "geral", "phone": "912345678", "quantity": 2},
        {"ticket_tier": "geral", "phone": "912345678", "quantity": 0},
        {"ticket_tier": "geral", "phone": "912345678", "quantity": -1},
        {"ticket_tier": "geral", "phone": "912345678", "email": "not-an-email"},
    ],
)
def test_invalid_purchase_requests_are_rejected_without_side_effects(world, payload):
    world.seed()
    ana = world.user("ana")

    response = ana.post(INITIATE_URL, json=payload)

    assert response.status_code == 422
    with world.session() as db:
        assert db.scalar(select(func.count()).select_from(Transaction)) == 0


@pytest.mark.parametrize(
    "phone",
    ["912345678", "912 345 678", "+351 912345678", "00351912345678", "351912345678"],
)
def test_phone_formats_are_normalised(world, phone):
    world.seed()
    ana = world.user("ana")

    response = world.buy(ana, phone=phone)

    assert response.status_code == 201
    assert response.json()["phone"] == "912345678"


def test_the_client_cannot_choose_the_price(world):
    world.seed()
    ana = world.user("ana")

    response = world.buy(ana, amount_cents=1, price_cents=1, price=0.01)

    assert response.status_code == 201
    assert response.json()["amount_cents"] == DEFAULT_TEST_PRICES[GERAL]


def test_access_rules(world):
    world.seed()
    ana = world.user("ana")
    eva = world.user("eva", verified=False)
    mallory = world.user("mallory")
    reference = world.buy(ana).json()["reference"]

    assert (
        world.anonymous()
        .post(INITIATE_URL, json={"ticket_tier": "geral", "phone": "912345678"})
        .status_code
        == 401
    )
    assert world.buy(eva).status_code == 403  # email not verified
    assert (
        world.anonymous().get(f"/api/payment/transactions/{reference}").status_code
        == 401
    )
    assert world.poll(mallory, reference).status_code == 404  # not hers
    assert world.poll(ana, "ENEI-NOPE").status_code == 404


def test_student_modalities_need_a_verified_student(world):
    world.seed()
    plain = world.user("plain")
    student = world.user("student", student=True)

    assert world.buy(plain, tier="acesso").status_code == 403
    assert world.buy(student, tier="acesso").status_code == 201
    assert world.buy(plain, tier="geral").status_code == 201


def test_a_closed_box_office_and_disabled_payments(world, monkeypatch):
    world.seed()
    ana = world.user("ana")
    with world.session() as db:
        tier = db.scalar(select(TicketTierPrice).where(TicketTierPrice.tier == GERAL))
        tier.price_cents = None
        db.commit()

    closed = world.buy(ana)

    assert closed.status_code == 503
    assert closed.json()["detail"] == "Ticket sales are not open yet"


def test_the_payment_rate_limit_answers_429_with_retry_after(world, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_PAYMENT_PER_MINUTE", 3)
    world.seed()
    ana = world.user("ana")
    world.provider.fail_create = True  # every attempt fails, so none blocks the next

    codes = [world.buy(ana).status_code for _ in range(5)]

    assert codes[:3] == [502, 502, 502]
    assert codes[3:] == [429, 429]
    limited = world.buy(ana)
    assert int(limited.headers["Retry-After"]) >= 1


# --- the burst


def _run_all(jobs, *, workers: int | None = None):
    """Run the jobs at the same moment, each in its own thread."""
    barrier = threading.Barrier(len(jobs))
    results = [None] * len(jobs)
    errors: list[BaseException] = []

    def runner(index, job):
        try:
            barrier.wait(timeout=30)
            results[index] = job()
        except BaseException as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=runner, args=(i, job)) for i, job in enumerate(jobs)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
    assert errors == [], errors
    return results


@requires_postgres
def test_a_burst_of_buyers_sells_exactly_the_stock(world):
    """40 buyers for 25 seats by default; PIPELINE_BUYERS=300 PIPELINE_SEATS=150
    reproduces the size of the launch peak."""
    buyers = int(os.environ.get("PIPELINE_BUYERS", "40"))
    seats = int(os.environ.get("PIPELINE_SEATS", "25"))
    world.seed(limit=seats)
    clients = [world.user(f"buyer{i:03d}") for i in range(buyers)]

    results = _run_all([lambda c=c: world.buy(c) for c in clients])

    codes = [r.status_code for r in results]
    assert codes.count(201) == seats, codes
    assert codes.count(409) == buyers - seats, codes
    assert not [c for c in codes if c >= 500], codes
    world.invariants(limit=seats)


@requires_postgres
def test_the_buyers_pay_while_polling_and_the_provider_redelivers(world):
    buyers = int(os.environ.get("PIPELINE_BUYERS", "30"))
    seats = int(os.environ.get("PIPELINE_SEATS", "20"))
    world.seed(limit=seats)
    clients = [world.user(f"buyer{i:03d}") for i in range(buyers)]
    started = [(c, world.buy(c)) for c in clients]
    winners = [(c, r.json()["reference"]) for c, r in started if r.status_code == 201]
    assert len(winners) == seats
    for _, reference in winners:
        world.provider.set_status(reference, TransactionStatus.CONFIRMED)

    jobs = []
    for client, reference in winners:
        jobs.append(lambda c=client, r=reference: world.callback(c, r))
        jobs.append(lambda c=client, r=reference: world.callback(c, r))  # redelivery
        jobs.append(lambda c=client, r=reference: world.poll(c, r))
        jobs.append(lambda c=client, r=reference: c.get(ME_URL))
    results = _run_all(jobs)

    assert not [r.status_code for r in results if r.status_code >= 500]
    for client, reference in winners:
        assert world.status(reference) is TransactionStatus.CONFIRMED
        assert client.get(ME_URL).json()["qr_code"]
    with world.session() as db:
        assert db.scalar(select(func.count()).select_from(Ticket)) == seats
    world.invariants(limit=seats)


@requires_postgres
def test_a_chaotic_hour_keeps_every_invariant(world):
    """Buyers start, abandon, retry and pay late, in random order, all at once."""
    import random

    rng = random.Random(20261101)
    people = int(os.environ.get("PIPELINE_BUYERS", "30"))
    seats = int(os.environ.get("PIPELINE_SEATS", "12"))
    world.seed(limit=seats)
    names = [f"person{i:03d}" for i in range(people)]
    clients = {n: world.user(n) for n in names}
    references: dict[str, list[str]] = {n: [] for n in names}

    for round_number in range(4):
        jobs = []
        for name in names:
            action = rng.choice(["buy", "buy", "poll", "pay", "late", "abandon"])
            client = clients[name]

            def job(name=name, client=client, action=action):
                refs = references[name]
                if action == "buy":
                    response = world.buy(client)
                    if response.status_code == 201:
                        refs.append(response.json()["reference"])
                    return response
                if not refs:
                    return client.get(ME_URL)
                reference = refs[-1]
                if action == "poll":
                    return world.poll(client, reference)
                if action == "pay":
                    return world.pays(client, reference)
                if action == "late":
                    world.provider.set_status(reference, TransactionStatus.EXPIRED)
                    world.poll(client, reference)
                    world.provider.set_status(reference, TransactionStatus.CONFIRMED)
                    return world.callback(client, reference)
                world.provider.set_status(reference, TransactionStatus.EXPIRED)
                return world.poll(client, reference)

            jobs.append(job)
        results = _run_all(jobs)
        bad = [r.status_code for r in results if r.status_code >= 500]
        assert bad == [], f"round {round_number}: {bad}"
        world.invariants(limit=seats)

    # The system settles: whatever is still waiting can be closed or paid.
    for name in names:
        for reference in references[name]:
            if world.status(reference) is TransactionStatus.PENDING:
                world.provider.set_status(reference, TransactionStatus.EXPIRED)
                world.poll(clients[name], reference)
    world.invariants(limit=seats)


@requires_postgres
def test_the_double_click_at_the_same_instant_starts_one_payment(world):
    world.seed()
    ana = world.user("ana")

    results = _run_all([lambda: world.buy(ana) for _ in range(6)])

    codes = sorted(r.status_code for r in results)
    assert codes == [201, 409, 409, 409, 409, 409], codes
    with world.session() as db:
        assert db.scalar(select(func.count()).select_from(Transaction)) == 1
    world.invariants()


@requires_postgres
def test_a_slow_provider_does_not_block_the_other_requests(world):
    """Polling forty waiting payments while the provider takes half a second each.

    The database connection is given back before each call to the provider, so the
    pool (15 connections) is never the limit, and nothing times out.
    """
    world.seed()
    clients = [world.user(f"slow{i:02d}") for i in range(40)]
    references = [world.buy(c).json()["reference"] for c in clients]
    world.provider.latency = 0.5

    started = time.monotonic()
    results = _run_all(
        [lambda c=c, r=r: world.poll(c, r) for c, r in zip(clients, references)]
    )
    elapsed = time.monotonic() - started

    assert {r.status_code for r in results} == {200}
    assert elapsed < 10, f"forty polls took {elapsed:.1f}s: requests queued up"
    world.invariants()


@requires_postgres
def test_a_burst_of_callbacks_for_the_same_last_seat_sells_it_once(world):
    """Two late payments for one seat, delivered in the same instant, many times."""
    for round_number in range(5):
        world.seed(limit=1) if round_number == 0 else None
        ana = world.user(f"early{round_number}")
        rui = world.user(f"later{round_number}")
        first = world.buy(ana).json()["reference"]
        world.provider.set_status(first, TransactionStatus.EXPIRED)
        world.poll(ana, first)
        second = world.buy(rui).json()["reference"]
        world.provider.set_status(second, TransactionStatus.EXPIRED)
        world.poll(rui, second)
        # both are over at the provider, then both turn out to have been paid
        results = _run_all(
            [
                lambda: world.callback(ana, first),
                lambda: world.callback(rui, second),
            ]
        )
        assert {r.status_code for r in results} == {200}
        with world.session() as db:
            sold = db.scalar(
                select(func.count())
                .select_from(Ticket)
                .where(Ticket.payment_status != PaymentStatus.CANCELLED)
            )
            assert sold == 1, f"round {round_number}: {sold} tickets for one seat"
        world.invariants(limit=1)
        # next round: free the seat again, as an admin cancelling the ticket would
        with world.session() as db:
            for ticket in db.scalars(select(Ticket)):
                ticket.payment_status = PaymentStatus.CANCELLED
            for transaction in db.scalars(select(Transaction)):
                if transaction.status is TransactionStatus.CONFIRMED:
                    transaction.status = TransactionStatus.REFUND_DUE
            db.commit()


def test_a_provider_that_cannot_say_does_not_hold_the_seat_for_ever(world):
    """The answer is unreadable: the seat is kept for a while and then released."""
    world.seed(limit=1)
    ana, rui = world.user("ana"), world.user("rui")
    stuck = world.buy(ana).json()["reference"]
    world.provider.fail_status_unrecognised = True
    world.age(stuck, minutes=10)
    assert world.buy(rui).status_code == 409  # still held after the deadline

    world.age(stuck, minutes=settings.MBWAY_UNRESOLVED_MAX_WAIT_SECONDS // 60 + 5)

    assert world.buy(rui).status_code == 201
    assert world.status(stuck) is TransactionStatus.EXPIRED
    world.invariants(limit=1)
