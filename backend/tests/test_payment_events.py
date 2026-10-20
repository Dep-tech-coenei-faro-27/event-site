import asyncio
import threading
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.domains.payments import service, stream
from app.domains.payments.events import PaymentEvents, events
from app.domains.payments.gateway import get_mbway_gateway
from app.domains.payments.models import Transaction, TransactionStatus
from app.domains.tickets.models import Ticket
from app.domains.users.models import User
from app.main import app
from tests.helpers import INITIATE_URL, authenticate, seed_ticket_tiers
from tests.test_payments import INITIATE, FakeGateway

pytestmark = pytest.mark.usefixtures("email_sender")


@pytest.fixture
def gateway():
    fake = FakeGateway()
    app.dependency_overrides[get_mbway_gateway] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_mbway_gateway, None)


@pytest.fixture(autouse=True)
def streams_use_the_test_database(monkeypatch, test_engine):
    """The stream opens its own short sessions: point them at the test database."""
    monkeypatch.setattr(stream, "SessionLocal", sessionmaker(bind=test_engine))
    monkeypatch.setattr(settings, "PAYMENT_EVENTS_MAX_SECONDS", 2.0)
    yield
    assert events.listening() == []  # no stream is left subscribed by any test


def events_url(reference: str) -> str:
    return f"/api/payment/transactions/{reference}/events"


def start_payment(auth_client, email_sender, db_session) -> str:
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)
    response = auth_client.post(INITIATE_URL, json=INITIATE)
    assert response.status_code == 201
    return response.json()["reference"]


def read_stream(auth_client, reference: str) -> list[str]:
    with auth_client.stream("GET", events_url(reference)) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-accel-buffering"] == "no"
        return [line for line in response.iter_lines() if line]


def statuses(lines: list[str]) -> list[str]:
    return [line.split('"')[3] for line in lines if line.startswith("data:")]


def test_a_stream_needs_a_session(auth_client):
    assert auth_client.get(events_url("ENEI-NONE")).status_code == 401


def test_a_stream_of_someone_elses_payment_does_not_exist(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)
    auth_client.cookies.clear()
    authenticate(auth_client, email_sender, db_session, email="bia@example.com")

    assert auth_client.get(events_url(reference)).status_code == 404
    assert auth_client.get(events_url("ENEI-NOPE")).status_code == 404


def test_it_starts_with_the_current_status_and_ends_when_it_is_final(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)
    gateway.status = TransactionStatus.CONFIRMED
    auth_client.get(f"/api/payment/transactions/{reference}")  # confirms it

    lines = read_stream(auth_client, reference)

    assert "retry: 3000" in lines
    assert statuses(lines) == ["confirmed"]


def test_a_change_reaches_the_open_stream_and_ends_it(
    auth_client, email_sender, db_session, gateway
):
    reference = start_payment(auth_client, email_sender, db_session)
    threading.Timer(0.4, events.publish, args=(reference, "confirmed")).start()

    lines = read_stream(auth_client, reference)

    assert statuses(lines) == ["pending", "confirmed"]


def test_the_provider_answer_is_pushed_without_anyone_polling(
    auth_client, email_sender, db_session, gateway, test_engine
):
    """The loop refresh confirms the payment, issues the ticket and tells the stream."""
    reference = start_payment(auth_client, email_sender, db_session)
    gateway.status = TransactionStatus.CONFIRMED

    def provider_changed():
        with Session(bind=test_engine) as other:
            service.refresh_pending_payment(other, reference, gateway)

    threading.Timer(0.4, provider_changed).start()

    lines = read_stream(auth_client, reference)

    assert statuses(lines) == ["pending", "confirmed"]
    db_session.expire_all()
    transaction = db_session.scalar(
        select(Transaction).where(Transaction.reference == reference)
    )
    assert transaction.status is TransactionStatus.CONFIRMED
    assert db_session.scalar(select(Ticket)) is not None


def test_a_quiet_stream_sends_a_heartbeat_and_closes_after_its_lifetime(
    auth_client, email_sender, db_session, gateway, monkeypatch
):
    monkeypatch.setattr(settings, "PAYMENT_EVENTS_HEARTBEAT_SECONDS", 0.1)
    monkeypatch.setattr(settings, "PAYMENT_EVENTS_MAX_SECONDS", 0.55)
    reference = start_payment(auth_client, email_sender, db_session)

    lines = read_stream(auth_client, reference)

    assert lines.count(": keep-alive") >= 3
    assert statuses(lines) == ["pending"]  # then the browser reconnects by itself


def test_a_person_cannot_open_more_streams_than_the_limit(
    auth_client, email_sender, db_session, gateway, monkeypatch
):
    monkeypatch.setattr(settings, "PAYMENT_EVENTS_MAX_PER_USER", 0)
    reference = start_payment(auth_client, email_sender, db_session)

    response = auth_client.get(events_url(reference))

    assert response.status_code == 429


def test_the_registry_limits_streams_per_person_and_frees_them():
    registry = PaymentEvents()

    async def scenario():
        first = registry.subscribe("A", 1, limit=2)
        second = registry.subscribe("B", 1, limit=2)
        assert first is not None and second is not None
        assert registry.subscribe("C", 1, limit=2) is None  # the third is refused
        assert registry.subscribe("C", 2, limit=2) is not None  # another person is fine
        registry.unsubscribe("A", 1, first)
        registry.unsubscribe("A", 1, first)  # twice is harmless
        assert registry.subscribe("D", 1, limit=2) is not None  # a place was freed
        assert sorted(registry.listening()) == ["B", "C", "D"]

    asyncio.run(scenario())


def test_publishing_with_nobody_listening_never_fails():
    registry = PaymentEvents()
    registry.publish("ENEI-X", "confirmed")  # no loop and no listeners

    async def scenario():
        registry.bind_loop(asyncio.get_running_loop())
        registry.publish("ENEI-X", "confirmed")

    asyncio.run(scenario())


def test_every_change_of_state_notifies(db_session, monkeypatch):
    calls = []
    monkeypatch.setattr(service, "notify", lambda ref, st: calls.append((ref, st)))
    tiers = seed_ticket_tiers(db_session)
    user = User(name="X", email="x@example.com", password_hash="h", is_verified=True)
    db_session.add(user)
    db_session.commit()
    transaction = Transaction(
        reference="ENEI-NOTIFY",
        user_id=user.id,
        ticket_tier_id=next(iter(tiers.values())).id,
        amount_cents=5000,
        quantity=1,
        status=TransactionStatus.PENDING,
        phone="912345678",
        provider="fake",
        expires_at=datetime.now(UTC),
    )
    db_session.add(transaction)
    db_session.commit()

    service._settle_pending(db_session, transaction, TransactionStatus.EXPIRED)

    assert calls == [("ENEI-NOTIFY", TransactionStatus.EXPIRED)]


def test_one_reconciliation_pass_asks_only_about_payments_being_waited_for(
    auth_client, email_sender, db_session, gateway, monkeypatch
):
    reference = start_payment(auth_client, email_sender, db_session)
    gateway.status = TransactionStatus.CONFIRMED
    monkeypatch.setattr(stream, "get_mbway_gateway", lambda: gateway)

    async def scenario():
        events.bind_loop(asyncio.get_running_loop())
        await stream.reconcile_once()  # nobody listening: the provider is not asked
        assert gateway.status_calls == []
        queue = events.subscribe(reference, 1, limit=3)
        try:
            await stream.reconcile_once()
            assert await asyncio.wait_for(queue.get(), 2) == "confirmed"
        finally:
            events.unsubscribe(reference, 1, queue)

    asyncio.run(scenario())
    assert len(gateway.status_calls) == 1
