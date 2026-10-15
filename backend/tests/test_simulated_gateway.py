import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.core.config import Settings, settings
from app.core.qr import verify_qr_payload
from app.domains.payments.gateway import (
    SimulatedMBWayGateway,
    get_mbway_gateway,
)
from app.domains.payments.models import TransactionStatus
from app.domains.tickets.models import PaymentStatus, Ticket
from app.main import app
from tests.helpers import INITIATE_URL, authenticate, seed_ticket_tiers, transaction_url

USERS_ME_URL = "/api/users/me"

INITIATE = {"ticket_tier": "geral", "phone": "912345678"}


class Clock:
    def __init__(self, start: float = 1_000_000.0) -> None:
        self.value = start

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


@pytest.fixture
def confirming_gateway():
    clock = Clock()
    gateway = SimulatedMBWayGateway(confirm_after_seconds=5, now=clock)
    app.dependency_overrides[get_mbway_gateway] = lambda: gateway
    yield gateway, clock
    app.dependency_overrides.pop(get_mbway_gateway, None)


def test_simulated_gateway_stays_pending_by_default():
    gateway = SimulatedMBWayGateway()

    payment = gateway.create_payment(
        reference="ENEI-ABCDEFGHIJ",
        amount_cents=5000,
        phone="912345678",
        email="ana@example.com",
    )

    assert payment.status is TransactionStatus.PENDING
    assert (
        gateway.get_status(
            reference="ENEI-ABCDEFGHIJ",
            provider_reference=payment.provider_reference,
        )
        is TransactionStatus.PENDING
    )


def test_confirming_simulator_waits_the_configured_delay():
    clock = Clock()
    gateway = SimulatedMBWayGateway(confirm_after_seconds=5, now=clock)
    payment = gateway.create_payment(
        reference="ENEI-ABCDEFGHIJ",
        amount_cents=5000,
        phone="912345678",
        email="ana@example.com",
    )

    assert (
        gateway.get_status(
            reference="ENEI-ABCDEFGHIJ",
            provider_reference=payment.provider_reference,
        )
        is TransactionStatus.PENDING
    )

    clock.advance(4)
    assert (
        gateway.get_status(
            reference="ENEI-ABCDEFGHIJ",
            provider_reference=payment.provider_reference,
        )
        is TransactionStatus.PENDING
    )

    clock.advance(1)
    assert (
        gateway.get_status(
            reference="ENEI-ABCDEFGHIJ",
            provider_reference=payment.provider_reference,
        )
        is TransactionStatus.CONFIRMED
    )


@pytest.mark.parametrize("provider_reference", [None, "", "ifthenpay-1", "SIM-abc-x"])
def test_confirming_simulator_ignores_references_it_does_not_own(provider_reference):
    gateway = SimulatedMBWayGateway(confirm_after_seconds=1, now=Clock())

    status = gateway.get_status(
        reference="ENEI-ABCDEFGHIJ", provider_reference=provider_reference
    )

    assert status is TransactionStatus.PENDING


@pytest.mark.parametrize("environment", ["dev", "prod"])
def test_simulated_mode_builds_the_confirming_simulator(monkeypatch, environment):
    monkeypatch.setattr(settings, "PAYMENTS_MODE", "simulated")
    monkeypatch.setattr(settings, "ENVIRONMENT", environment)
    monkeypatch.setattr(settings, "PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS", 7)

    gateway = get_mbway_gateway()

    assert isinstance(gateway, SimulatedMBWayGateway)
    assert gateway.confirm_after_seconds == 7


def test_confirmed_payment_flows_through_the_api(
    auth_client, email_sender, db_session, confirming_gateway
):
    _, clock = confirming_gateway
    authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    reference = auth_client.post(INITIATE_URL, json=INITIATE).json()["reference"]
    assert auth_client.get(transaction_url(reference)).json()["status"] == "pending"

    clock.advance(5)

    body = auth_client.get(transaction_url(reference)).json()
    assert body["status"] == "confirmed"
    assert body["confirmed_at"] is not None


def test_confirmed_payment_issues_the_ticket_and_the_qr(
    auth_client, email_sender, db_session, confirming_gateway
):
    _, clock = confirming_gateway
    user = authenticate(auth_client, email_sender, db_session)
    seed_ticket_tiers(db_session)

    reference = auth_client.post(INITIATE_URL, json=INITIATE).json()["reference"]
    assert (
        db_session.scalar(
            select(Ticket).where(Ticket.transaction_reference == reference)
        )
        is None
    )

    clock.advance(5)
    assert auth_client.get(transaction_url(reference)).json()["status"] == "confirmed"

    ticket = db_session.scalar(
        select(Ticket).where(Ticket.transaction_reference == reference)
    )
    assert ticket is not None
    assert ticket.user_id == user.id
    assert ticket.payment_status is PaymentStatus.PAID

    qr_code = auth_client.get(USERS_ME_URL).json()["qr_code"]
    assert qr_code == ticket.qr_payload
    assert verify_qr_payload(qr_code).ticket_id == ticket.id


DEV = {
    "ENVIRONMENT": "dev",
    "POSTGRES_USER": "user",
    "POSTGRES_PASSWORD": "password",
    "POSTGRES_DB": "db",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": 5432,
    "JWT_SECRET_KEY": "k" * 40,
}

PROD = {
    **DEV,
    "ENVIRONMENT": "prod",
    "JWT_SECRET_KEY": "p" * 48,
    "QR_SECRET_KEY": "q" * 48,
    "SMTP_HOST": "smtp.example.com",
    "EMAIL_SENDER": "noreply@example.com",
    "FRONTEND_URL": "https://app.example.com",
    "CORS_ALLOW_ORIGINS": ["https://app.example.com"],
}


def test_simulated_mode_accepts_the_confirming_simulator():
    settings = Settings(
        _env_file=None,
        **DEV,
        PAYMENTS_MODE="simulated",
        PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS=5,
    )

    assert settings.PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS == 5


def test_simulated_mode_accepts_no_confirm_delay():
    settings = Settings(_env_file=None, **DEV, PAYMENTS_MODE="simulated")

    assert settings.PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS == 0


def test_production_accepts_the_confirming_simulator_in_simulated_mode():
    settings = Settings(
        _env_file=None,
        **PROD,
        PAYMENTS_MODE="simulated",
        PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS=5,
    )

    assert settings.PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS == 5


@pytest.mark.parametrize("mode", ["off", "live"])
def test_confirming_simulator_requires_simulated_mode(mode):
    overrides = {
        "PAYMENTS_MODE": mode,
        "PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS": 5,
    }
    if mode == "live":
        overrides["MBWAY_KEY"] = "MBW-123456"
        overrides["MBWAY_CALLBACK_KEY"] = "c" * 40

    with pytest.raises(
        ValidationError, match="PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS"
    ):
        Settings(_env_file=None, **DEV, **overrides)
