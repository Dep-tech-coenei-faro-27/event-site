# ruff: noqa: F811  (the pipeline fixtures are imported from the e2e tests)
"""The provider is asked about a payment at most once per interval.

Many people polling every two seconds must not turn into as many calls to the
provider. The callback is unaffected: it confirms a payment at once.
"""

import pytest

from app.core.config import settings
from app.domains.payments import service
from app.domains.payments.models import TransactionStatus
from tests.test_payment_pipeline import (  # noqa: F401
    _run_all,
    requires_postgres,
    world,
)


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch):
    fake = Clock()
    monkeypatch.setattr(service, "_clock", fake)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER_MIN_INTERVAL_SECONDS", 5)
    service._asked_at.clear()
    yield fake
    service._asked_at.clear()


def test_polling_asks_the_provider_at_most_once_per_interval(world, clock):
    world.seed()
    ana = world.user("ana")
    reference = world.buy(ana).json()["reference"]
    world.provider.status_calls = 0

    for _ in range(6):
        assert world.poll(ana, reference).json()["status"] == "pending"
    assert world.provider.status_calls == 1

    clock.now += 5
    world.poll(ana, reference)
    assert world.provider.status_calls == 2


def test_a_payment_paid_in_between_is_found_at_the_next_allowed_question(world, clock):
    world.seed()
    ana = world.user("ana")
    reference = world.buy(ana).json()["reference"]
    assert world.poll(ana, reference).json()["status"] == "pending"
    world.provider.set_status(reference, TransactionStatus.CONFIRMED)

    assert world.poll(ana, reference).json()["status"] == "pending"  # not asked yet
    clock.now += 5
    assert world.poll(ana, reference).json()["status"] == "confirmed"


def test_the_callback_is_never_throttled(world, clock):
    world.seed()
    ana = world.user("ana")
    reference = world.buy(ana).json()["reference"]
    world.poll(ana, reference)

    assert world.pays(ana, reference).status_code == 200

    assert world.poll(ana, reference).json()["status"] == "confirmed"


def test_each_payment_has_its_own_interval(world, clock):
    world.seed()
    ana, rui = world.user("ana"), world.user("rui")
    first = world.buy(ana).json()["reference"]
    second = world.buy(rui).json()["reference"]
    world.provider.status_calls = 0

    world.poll(ana, first)
    world.poll(rui, second)
    world.poll(ana, first)

    assert world.provider.status_calls == 2


def test_an_interval_of_zero_asks_every_time(world, clock, monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER_MIN_INTERVAL_SECONDS", 0)
    world.seed()
    ana = world.user("ana")
    reference = world.buy(ana).json()["reference"]
    world.provider.status_calls = 0

    for _ in range(4):
        world.poll(ana, reference)

    assert world.provider.status_calls == 4


@requires_postgres
def test_a_sold_out_rush_does_not_become_a_storm_of_provider_calls(world, clock):
    """60 hopeful buyers for 10 overdue payments used to cost 600 calls."""
    world.seed(limit=10)
    owners = [world.user(f"b{i:03d}") for i in range(10)]
    references = [world.buy(c).json()["reference"] for c in owners]
    for reference in references:
        world.age(reference, minutes=10)
    hopeful = [world.user(f"h{i:03d}") for i in range(60)]
    world.provider.status_calls = 0

    results = _run_all([lambda c=c: world.buy(c) for c in hopeful])

    assert {r.status_code for r in results} == {409}  # the provider still waits
    assert world.provider.status_calls <= 10, world.provider.status_calls
