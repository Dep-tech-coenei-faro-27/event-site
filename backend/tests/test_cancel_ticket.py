# ruff: noqa: F811  (the pipeline fixtures are imported from the e2e tests)
"""Cancelling a ticket frees its seat (the payment becomes ``refunded``)."""

import pytest
from sqlalchemy import select

from app.domains.payments.models import Transaction, TransactionStatus
from app.domains.payments.service import cancel_ticket
from app.domains.tickets.models import PaymentStatus, Ticket
from app.domains.tickets.service import TicketNotFoundError
from tests.test_payment_pipeline import (  # noqa: F401
    _run_all,
    requires_postgres,
    world,
)


def _bought(world, name="ana", *, limit=None):
    world.seed(limit=limit)
    client = world.user(name)
    reference = world.buy(client).json()["reference"]
    world.pays(client, reference)
    with world.session() as db:
        ticket_id = db.scalar(
            select(Ticket.id).where(Ticket.transaction_reference == reference)
        )
    return client, reference, ticket_id


def _cancel(world, ticket_id):
    with world.session() as db:
        return cancel_ticket(db, ticket_id)


def test_cancelling_frees_the_seat_for_the_next_buyer(world):
    ana, reference, ticket_id = _bought(world, limit=1)
    assert world.buy(world.user("rui")).status_code == 409  # sold out

    _cancel(world, ticket_id)

    assert world.status(reference) is TransactionStatus.REFUNDED
    assert world.buy(world.user("eva")).status_code == 201
    world.invariants(limit=1)


def test_the_person_can_buy_again_and_gets_a_new_qr(world):
    ana, _, ticket_id = _bought(world)
    old_qr = ana.get("/api/users/me").json()["qr_code"]
    _cancel(world, ticket_id)
    assert ana.get("/api/users/me").json()["qr_code"] is None

    second = world.buy(ana)
    assert second.status_code == 201
    world.pays(ana, second.json()["reference"])

    new_qr = ana.get("/api/users/me").json()["qr_code"]
    assert new_qr and new_qr != old_qr
    world.invariants()


def test_cancelling_twice_changes_nothing(world):
    _, reference, ticket_id = _bought(world)

    first, second = _cancel(world, ticket_id), _cancel(world, ticket_id)

    assert first.payment_status is second.payment_status is PaymentStatus.CANCELLED
    assert world.status(reference) is TransactionStatus.REFUNDED


def test_a_repeated_callback_does_not_bring_back_a_refunded_payment(world):
    ana, reference, ticket_id = _bought(world, limit=1)
    _cancel(world, ticket_id)

    for _ in range(3):
        assert world.callback(ana, reference).status_code == 200

    assert world.status(reference) is TransactionStatus.REFUNDED
    assert ana.get("/api/users/me").json()["qr_code"] is None
    assert world.buy(world.user("rui")).status_code == 201  # the seat stays free


def test_the_owner_sees_the_refunded_state(world):
    ana, reference, ticket_id = _bought(world)
    _cancel(world, ticket_id)

    assert world.poll(ana, reference).json()["status"] == "refunded"


def test_cancelling_an_unknown_ticket_fails(world):
    world.seed()
    with world.session() as db:
        with pytest.raises(TicketNotFoundError):
            cancel_ticket(db, 999999)


@requires_postgres
def test_cancelling_while_the_callback_is_redelivered_does_not_deadlock(world):
    world.seed()
    for index in range(15):
        client = world.user(f"person{index:02d}")
        reference = world.buy(client).json()["reference"]
        world.pays(client, reference)
        with world.session() as db:
            ticket_id = db.scalar(
                select(Ticket.id).where(Ticket.transaction_reference == reference)
            )
        results = _run_all(
            [
                lambda i=ticket_id: _cancel(world, i),
                lambda c=client, r=reference: world.callback(c, r),
                lambda c=client, r=reference: world.poll(c, r),
            ]
        )
        assert results[1].status_code == 200
        with world.session() as db:
            row = db.scalar(
                select(Transaction).where(Transaction.reference == reference)
            )
            assert row.status is TransactionStatus.REFUNDED
    world.invariants()
