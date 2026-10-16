# ruff: noqa: F811  (the pipeline fixtures are imported from the e2e tests)
"""GET /api/payment/tiers: what the checkout needs to show prices and availability."""

from sqlalchemy import select

from app.core.config import settings
from app.domains.payments.models import TicketTierPrice, TransactionStatus
from tests.test_payment_pipeline import world  # noqa: F401

URL = "/api/payment/tiers"


def _by_tier(response):
    return {row["tier"]: row for row in response.json()}


def test_the_tiers_are_public_and_carry_price_and_availability(world):
    world.seed()

    response = world.anonymous().get(URL)

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert [row["tier"] for row in response.json()] == [
        "acesso",
        "refeicoes",
        "completo",
        "geral",
    ]
    geral = _by_tier(response)["geral"]
    assert geral == {
        "tier": "geral",
        "name": "Passe geral",
        "price_cents": 5000,
        "currency": "EUR",
        "is_student": False,
        "sale_open": True,
        "available": True,
    }
    assert _by_tier(response)["acesso"]["is_student"] is True


def test_the_number_of_seats_left_is_not_exposed(world):
    world.seed(limit=5)

    row = _by_tier(world.anonymous().get(URL))["geral"]

    assert "inventory_limit" not in row and "remaining" not in row


def test_a_modality_without_a_price_is_closed(world):
    world.seed()
    with world.session() as db:
        tier = db.scalar(select(TicketTierPrice).where(TicketTierPrice.tier == "geral"))
        tier.price_cents = None
        db.commit()

    row = _by_tier(world.anonymous().get(URL))["geral"]

    assert row["price_cents"] is None
    assert row["sale_open"] is False and row["available"] is False


def test_everything_is_closed_while_payments_are_off(world, monkeypatch):
    world.seed()
    monkeypatch.setattr(settings, "PAYMENTS_MODE", "off")

    rows = world.anonymous().get(URL).json()

    assert all(not row["sale_open"] and not row["available"] for row in rows)
    assert all(row["price_cents"] is not None for row in rows)  # still shown


def test_a_seat_reserved_for_a_waiting_payment_makes_it_unavailable(world):
    world.seed(limit=1)
    ana = world.user("ana")
    reference = world.buy(ana).json()["reference"]

    assert _by_tier(world.anonymous().get(URL))["geral"]["available"] is False

    world.provider.set_status(reference, TransactionStatus.EXPIRED)
    world.poll(ana, reference)
    assert _by_tier(world.anonymous().get(URL))["geral"]["available"] is True


def test_a_modality_with_seats_left_stays_available(world):
    world.seed(limit=3)
    world.buy(world.user("ana"))

    assert _by_tier(world.anonymous().get(URL))["geral"]["available"] is True


def test_other_modalities_are_not_affected_by_one_selling_out(world):
    world.seed(limit=1)
    world.buy(world.user("ana"))

    rows = _by_tier(world.anonymous().get(URL))

    assert rows["geral"]["available"] is False
    assert rows["acesso"]["available"] is True  # no limit set on it


def test_the_tiers_are_rate_limited_per_ip(world, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_PAYMENT_TIERS_PER_IP_PER_MINUTE", 3)
    world.seed()
    client = world.anonymous()

    codes = [client.get(URL).status_code for _ in range(5)]

    assert codes == [200, 200, 200, 429, 429]
    assert int(client.get(URL).headers["Retry-After"]) >= 1
