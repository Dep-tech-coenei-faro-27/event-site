# ruff: noqa: F811  (the pipeline fixtures are imported from the e2e tests)
"""The early-bird price ends by itself: on its date, or at the ticket limit."""

import os
import threading
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domains.payments.gateway import SimulatedMBWayGateway
from app.domains.payments.models import (
    TicketTier,
    TicketTierPrice,
    Transaction,
    TransactionStatus,
)
from app.domains.payments.schemas import PaymentInitiateRequest
from app.domains.payments.service import initiate_payment
from app.domains.users.models import User
from tests.helpers import seed_ticket_tiers
from tests.test_payment_pipeline import world  # noqa: F401

TIERS = "/api/payment/tiers"


def _early_bird(world, monkeypatch, *, ends_in_days=30, limit=300):
    """Passe geral at 50 € with 60 € as the regular price, the end far away."""
    world.seed()
    with world.session() as db:
        geral = db.scalar(
            select(TicketTierPrice).where(TicketTierPrice.tier == TicketTier.GERAL)
        )
        geral.normal_price_cents = 6000
        db.commit()
    monkeypatch.setattr(
        settings, "EARLY_BIRD_ENDS_AT", datetime.now(UTC) + timedelta(days=ends_in_days)
    )
    monkeypatch.setattr(settings, "EARLY_BIRD_TICKET_LIMIT", limit)


def _stored(world):
    """``(price_cents, normal_price_cents)`` of the passe geral, as stored."""
    with world.session() as db:
        row = db.scalar(
            select(TicketTierPrice).where(TicketTierPrice.tier == TicketTier.GERAL)
        )
        return row.price_cents, row.normal_price_cents


def _geral(world):
    rows = {row["tier"]: row for row in world.anonymous().get(TIERS).json()}
    return rows["geral"]


def test_while_it_lasts_the_early_bird_price_is_charged(world, monkeypatch):
    _early_bird(world, monkeypatch)
    ana = world.user("ana")

    geral = _geral(world)
    reference = world.buy(ana).json()["reference"]

    assert (geral["price_cents"], geral["normal_price_cents"]) == (5000, 6000)
    assert world.tx(reference).amount_cents == 5000


def test_after_its_date_the_normal_price_is_charged_and_shown(world, monkeypatch):
    _early_bird(world, monkeypatch, ends_in_days=-1)
    ana = world.user("ana")

    geral = _geral(world)
    reference = world.buy(ana).json()["reference"]

    assert (geral["price_cents"], geral["normal_price_cents"]) == (6000, None)
    assert world.tx(reference).amount_cents == 6000


def test_the_early_price_is_never_given_to_more_people_than_the_limit(
    world, monkeypatch
):
    """Places are held by payments that are still waiting, not only by paid ones."""
    _early_bird(world, monkeypatch, limit=2)
    people = [world.user(name) for name in ("ana", "rui", "eva")]

    references = [world.buy(person).json()["reference"] for person in people]

    assert [world.tx(r).amount_cents for r in references] == [5000, 5000, 6000]
    assert _geral(world)["price_cents"] == 6000


def test_at_the_ticket_limit_the_normal_price_takes_over(world, monkeypatch):
    _early_bird(world, monkeypatch, limit=1)
    ana, rui = world.user("ana"), world.user("rui")

    reference = world.buy(ana).json()["reference"]
    world.pays(ana, reference)

    geral = _geral(world)
    second = world.buy(rui).json()["reference"]

    assert (geral["price_cents"], geral["normal_price_cents"]) == (6000, None)
    assert world.tx(second).amount_cents == 6000
    assert world.tx(reference).amount_cents == 5000  # the first one keeps its price


def test_the_end_is_permanent_a_failed_payment_does_not_bring_the_early_price_back(
    world, monkeypatch
):
    _early_bird(world, monkeypatch, limit=1)
    ana = world.user("ana")
    reference = world.buy(ana).json()["reference"]
    assert _geral(world)["price_cents"] == 6000  # the only early place is taken

    with world.session() as db:
        row = db.scalar(select(Transaction).where(Transaction.reference == reference))
        row.status = TransactionStatus.FAILED
        db.commit()

    assert _geral(world) == {
        **_geral(world),
        "price_cents": 6000,
        "normal_price_cents": None,
    }
    assert _stored(world) == (6000, None)


def test_a_modality_without_a_normal_price_never_changes(world, monkeypatch):
    _early_bird(world, monkeypatch, ends_in_days=-1)

    rows = {row["tier"]: row for row in world.anonymous().get(TIERS).json()}

    assert rows["acesso"]["price_cents"] == 2000
    assert rows["acesso"]["normal_price_cents"] is None


def test_one_place_short_of_the_limit_is_still_the_early_bird(world, monkeypatch):
    _early_bird(world, monkeypatch, limit=2)
    ana, rui = world.user("ana"), world.user("rui")
    world.pays(ana, world.buy(ana).json()["reference"])
    assert _geral(world)["price_cents"] == 5000

    world.pays(rui, world.buy(rui).json()["reference"])

    assert _geral(world)["price_cents"] == 6000


def test_a_refunded_ticket_does_not_bring_the_early_price_back(world, monkeypatch):
    _early_bird(world, monkeypatch, limit=1)
    ana = world.user("ana")
    reference = world.buy(ana).json()["reference"]
    world.pays(ana, reference)
    assert _geral(world)["price_cents"] == 6000

    with world.session() as db:
        row = db.scalar(select(Transaction).where(Transaction.reference == reference))
        row.status = TransactionStatus.REFUNDED
        db.commit()

    assert _geral(world)["price_cents"] == 6000
    assert _stored(world) == (6000, None)


def test_without_a_date_only_the_limit_ends_the_early_bird(world, monkeypatch):
    _early_bird(world, monkeypatch)
    monkeypatch.setattr(settings, "EARLY_BIRD_ENDS_AT", None)

    assert _geral(world)["price_cents"] == 5000


def test_the_price_the_buyer_saw_is_accepted_while_it_is_still_the_price(
    world, monkeypatch
):
    _early_bird(world, monkeypatch)
    ana = world.user("ana")

    response = world.buy(ana, expected_price_cents=5000)

    assert response.status_code == 201
    assert response.json()["amount_cents"] == 5000


def test_a_buyer_who_saw_the_early_bird_price_is_not_charged_the_normal_one(
    world, monkeypatch
):
    """The early bird ended while the checkout was open with the old price on it."""
    _early_bird(world, monkeypatch, ends_in_days=-1)
    ana = world.user("ana")

    refused = world.buy(ana, expected_price_cents=5000)

    assert refused.status_code == 409
    assert refused.json()["detail"] == "The price of this ticket changed"
    with world.session() as db:
        assert db.scalar(select(func.count()).select_from(Transaction)) == 0
    # After reading the new price the same person can go on, and pays that price.
    assert _geral(world)["price_cents"] == 6000
    accepted = world.buy(ana, expected_price_cents=6000)
    assert accepted.status_code == 201
    assert accepted.json()["amount_cents"] == 6000


def test_the_price_check_is_optional_and_never_a_free_price(world, monkeypatch):
    _early_bird(world, monkeypatch, ends_in_days=-1)
    ana, rui = world.user("ana"), world.user("rui")

    without = world.buy(ana)
    nonsense = world.buy(rui, expected_price_cents=0)

    assert without.status_code == 201 and without.json()["amount_cents"] == 6000
    assert nonsense.status_code == 422


def test_a_sold_out_or_student_refusal_is_not_hidden_behind_the_price(
    world, monkeypatch
):
    _early_bird(world, monkeypatch, ends_in_days=-1)
    ana = world.user("ana", student=False)

    student_tier = world.buy(ana, tier="acesso", expected_price_cents=1)

    assert student_tier.status_code == 403


def test_the_purchase_that_takes_the_last_early_place_writes_the_regular_prices(
    world, monkeypatch
):
    _early_bird(world, monkeypatch, limit=2)
    ana, rui = world.user("ana"), world.user("rui")

    world.buy(ana)
    assert _stored(world) == (5000, 6000)  # one place left: still the early bird
    world.buy(rui)

    assert _stored(world) == (6000, None)


def test_after_the_date_the_first_purchase_writes_the_regular_prices(
    world, monkeypatch
):
    _early_bird(world, monkeypatch, ends_in_days=-1)
    assert _stored(world) == (5000, 6000)  # reading the prices writes nothing
    _geral(world)
    assert _stored(world) == (5000, 6000)

    world.buy(world.user("ana"))

    assert _stored(world) == (6000, None)


def test_a_refused_purchase_is_priced_at_the_regular_price_and_the_next_one_writes_it(
    world, monkeypatch
):
    """A refusal rolls the write back; the price the buyer meets is the regular one."""
    _early_bird(world, monkeypatch, ends_in_days=-1)
    ana, rui = world.user("ana"), world.user("rui")

    refused = world.buy(ana, expected_price_cents=5000)
    assert refused.status_code == 409
    assert _geral(world)["price_cents"] == 6000  # what the site shows and charges
    assert _stored(world) == (5000, 6000)  # a refusal writes nothing

    assert world.buy(rui, expected_price_cents=6000).status_code == 201

    assert _stored(world) == (6000, None)


def test_the_stored_prices_do_not_change_again_after_the_end(world, monkeypatch):
    _early_bird(world, monkeypatch, ends_in_days=-1)
    ana, rui = world.user("ana"), world.user("rui")
    world.buy(ana)
    assert _stored(world) == (6000, None)

    second = world.buy(rui)

    assert second.status_code == 201 and second.json()["amount_cents"] == 6000
    assert _stored(world) == (6000, None)
    rows = {row["tier"]: row for row in world.anonymous().get(TIERS).json()}
    assert rows["acesso"]["price_cents"] == 2000  # no regular price saved: untouched


def test_before_the_end_nothing_is_written(world, monkeypatch):
    _early_bird(world, monkeypatch)
    ana = world.user("ana")

    world.buy(ana)
    _geral(world)

    assert _stored(world) == (5000, 6000)


def test_many_buyers_at_once_never_get_more_early_places_than_the_limit(
    db_session, test_engine, monkeypatch
):
    """Real row locks (PostgreSQL): 12 people start to pay together, 5 early places."""
    if not (os.environ.get("TEST_DATABASE_URL") or "").startswith("postgresql"):
        pytest.skip("row-level locking requires PostgreSQL")

    seed_ticket_tiers(db_session)
    geral = db_session.scalar(
        select(TicketTierPrice).where(TicketTierPrice.tier == TicketTier.GERAL)
    )
    geral.normal_price_cents = 6000
    ids = []
    for n in range(12):
        user = User(name=f"P{n}", email=f"p{n}@example.com", password_hash="x")
        db_session.add(user)
        db_session.flush()
        ids.append(user.id)
    db_session.commit()
    monkeypatch.setattr(settings, "EARLY_BIRD_ENDS_AT", None)
    monkeypatch.setattr(settings, "EARLY_BIRD_TICKET_LIMIT", 5)
    monkeypatch.setattr(settings, "TICKET_STOCK_LIMIT", 100)

    outcomes: dict[int, object] = {}
    start = threading.Barrier(len(ids))

    def buy(user_id):
        with Session(bind=test_engine) as session:
            start.wait(timeout=10)
            try:
                transaction, _ = initiate_payment(
                    session,
                    session.get(User, user_id),
                    PaymentInitiateRequest(
                        ticket_tier=TicketTier.GERAL, phone="912345678"
                    ),
                    SimulatedMBWayGateway(),
                )
                outcomes[user_id] = transaction.amount_cents
            except BaseException as exc:  # surfaced below
                outcomes[user_id] = exc

    threads = [threading.Thread(target=buy, args=(i,)) for i in ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    errors = [v for v in outcomes.values() if isinstance(v, BaseException)]
    assert errors == []
    amounts = sorted(outcomes.values())
    assert amounts == [5000] * 5 + [6000] * 7
    with Session(bind=test_engine) as session:
        row = session.scalar(
            select(TicketTierPrice).where(TicketTierPrice.tier == TicketTier.GERAL)
        )
        assert (row.price_cents, row.normal_price_cents) == (6000, None)


def test_a_checkout_nobody_finished_does_not_use_up_an_early_place(world, monkeypatch):
    """The end is permanent, so a payment past its deadline must not count.

    Two early places. Ana starts to pay and walks away; once her four minutes are
    over her place is free again, so Rui and Eva still get the early price.
    """
    _early_bird(world, monkeypatch, limit=2)
    ana, rui, eva = world.user("ana"), world.user("rui"), world.user("eva")
    abandoned = world.buy(ana).json()["reference"]
    world.age(abandoned, minutes=5)  # her time is over and she never paid
    assert _stored(world) == (5000, 6000)

    first = world.buy(rui).json()["reference"]
    second = world.buy(eva).json()["reference"]

    assert [world.tx(r).amount_cents for r in (abandoned, first, second)] == [5000] * 3
    assert _stored(world) == (6000, None)  # Rui and Eva took the two places


def test_a_payment_still_inside_its_time_does_hold_its_place(world, monkeypatch):
    _early_bird(world, monkeypatch, limit=2)
    ana, rui, eva = world.user("ana"), world.user("rui"), world.user("eva")

    prices = [
        world.tx(world.buy(p).json()["reference"]).amount_cents for p in (ana, rui, eva)
    ]

    assert prices == [5000, 5000, 6000]
