# ruff: noqa: F811  (the pipeline fixtures are imported from the e2e tests)
"""SALES_OPEN_AT: the ticket office opens at a set time, whatever the prices say."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.domains.payments.models import TransactionStatus
from app.domains.payments.service import sales_have_opened
from tests.test_payment_pipeline import world  # noqa: F401

TIERS = "/api/payment/tiers"


def _opens_in(monkeypatch, **delta):
    opens_at = datetime.now(UTC) + timedelta(**delta)
    monkeypatch.setattr(settings, "SALES_OPEN_AT", opens_at)
    return opens_at


# --- the setting ---------------------------------------------------------------
def test_no_date_means_sales_are_open_as_before(monkeypatch):
    monkeypatch.setattr(settings, "SALES_OPEN_AT", None)

    assert sales_have_opened() is True


def test_before_during_and_after_the_opening_time(monkeypatch):
    opens_at = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
    monkeypatch.setattr(settings, "SALES_OPEN_AT", opens_at)

    assert sales_have_opened(opens_at - timedelta(seconds=1)) is False
    assert sales_have_opened(opens_at) is True
    assert sales_have_opened(opens_at + timedelta(hours=1)) is True


def test_the_date_is_read_from_the_environment_with_its_timezone(monkeypatch):
    monkeypatch.setenv("SALES_OPEN_AT", "2026-11-02T09:00:00+00:00")

    value = Settings().SALES_OPEN_AT

    assert value == datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


def test_the_time_in_lisbon_is_the_same_instant(monkeypatch):
    monkeypatch.setenv("SALES_OPEN_AT", "2026-07-02T10:00:00+01:00")

    assert Settings().SALES_OPEN_AT == datetime(2026, 7, 2, 9, 0, tzinfo=UTC)


def test_an_empty_variable_means_no_date(monkeypatch):
    monkeypatch.setenv("SALES_OPEN_AT", "")

    assert Settings().SALES_OPEN_AT is None


@pytest.mark.parametrize(
    "bad", ["2026-11-02T09:00:00", "2026-11-02", "tomorrow", "13/11/2026"]
)
def test_a_date_without_timezone_or_unreadable_stops_the_start(monkeypatch, bad):
    monkeypatch.setenv("SALES_OPEN_AT", bad)

    with pytest.raises(ValidationError):
        Settings()


# --- the tiers listing ---------------------------------------------------------
def test_before_the_opening_every_modality_is_closed_and_says_when(world, monkeypatch):
    world.seed()
    opens_at = _opens_in(monkeypatch, days=3)

    rows = world.anonymous().get(TIERS).json()

    assert rows and all(not r["sale_open"] and not r["available"] for r in rows)
    assert all(r["price_cents"] is not None for r in rows)  # prices stay visible
    assert all(datetime.fromisoformat(r["opens_at"]) == opens_at for r in rows), rows[
        0
    ]["opens_at"]


def test_after_the_opening_everything_is_open_and_the_date_goes_away(
    world, monkeypatch
):
    world.seed()
    _opens_in(monkeypatch, hours=-1)

    rows = world.anonymous().get(TIERS).json()

    assert all(r["sale_open"] and r["opens_at"] is None for r in rows)


# --- buying --------------------------------------------------------------------
def test_buying_before_the_opening_answers_503_and_reserves_nothing(world, monkeypatch):
    world.seed(limit=1)
    ana = world.user("ana")
    _opens_in(monkeypatch, days=1)

    response = world.buy(ana)

    assert response.status_code == 503
    assert response.json()["detail"] == "Ticket sales are not open yet"
    assert world.tickets_of("ana@example.com") == []
    # the only seat is still free once the office opens
    _opens_in(monkeypatch, seconds=-1)
    assert world.buy(ana).status_code == 201


def test_the_same_request_works_once_the_date_has_passed(world, monkeypatch):
    world.seed()
    ana = world.user("ana")
    _opens_in(monkeypatch, hours=-2)

    assert world.buy(ana).status_code == 201


def test_a_payment_made_before_the_date_still_becomes_a_ticket(world, monkeypatch):
    """Someone who paid while the office was open (the real test payment on Friday)
    keeps the ticket if the date is later set into the future: the callback and the
    status checks do not look at SALES_OPEN_AT."""
    world.seed()
    ana = world.user("ana")
    monkeypatch.setattr(settings, "SALES_OPEN_AT", None)
    reference = world.buy(ana).json()["reference"]

    _opens_in(monkeypatch, days=2)  # the date moves into the future meanwhile
    world.pays(world.anonymous(), reference)

    assert world.status(reference) is TransactionStatus.CONFIRMED
    assert len(world.tickets_of("ana@example.com")) == 1
    assert world.poll(ana, reference).status_code == 200


def test_the_emergency_button_still_beats_an_open_date(world, monkeypatch):
    world.seed()
    _opens_in(monkeypatch, hours=-2)
    monkeypatch.setattr(settings, "PAYMENTS_MODE", "off")

    rows = world.anonymous().get(TIERS).json()

    assert rows and all(not r["sale_open"] and r["opens_at"] is None for r in rows)
