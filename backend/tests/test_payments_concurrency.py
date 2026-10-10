import os
import threading

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.domains.payments.gateway import (
    MBWayPayment,
    SimulatedMBWayGateway,
)
from app.domains.payments.models import (
    TicketTier,
    Transaction,
    TransactionStatus,
)
from app.domains.payments.schemas import PaymentInitiateRequest
from app.domains.payments.service import TicketSoldOutError, initiate_payment
from app.domains.users.models import User
from tests.helpers import seed_ticket_tiers

requires_postgres = pytest.mark.skipif(
    not (os.environ.get("TEST_DATABASE_URL") or "").startswith("postgresql"),
    reason="row-level locking requires PostgreSQL",
)


class BlockingGateway:
    """A gateway that parks the caller inside create_payment until released."""

    name = "blocking"

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()

    def create_payment(self, *, reference, amount_cents, phone, email) -> MBWayPayment:
        self.entered.set()
        assert self.release.wait(timeout=10)
        return MBWayPayment(provider_reference="BLOCK-1")

    def get_status(self, *, reference, provider_reference) -> TransactionStatus:
        return TransactionStatus.PENDING


def _payload() -> PaymentInitiateRequest:
    return PaymentInitiateRequest(ticket_tier=TicketTier.GERAL, phone="912345678")


def _make_user(db_session: Session, email: str) -> User:
    user = User(
        name="Ana Silva",
        email=email,
        password_hash=hash_password("Password123!"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _count_transactions(test_engine, ticket_id: int) -> int:
    with Session(bind=test_engine) as session:
        return session.scalar(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.ticket_id == ticket_id)
        )


@requires_postgres
def test_concurrent_initiates_do_not_oversell(db_session, test_engine):
    ticket = seed_ticket_tiers(db_session)[TicketTier.GERAL]
    ticket.inventory_limit = 1
    user = _make_user(db_session, "ana@example.com")
    db_session.commit()
    ticket_id, user_id = ticket.id, user.id

    blocking = BlockingGateway()
    failures: list[BaseException] = []

    def first() -> None:
        session = Session(bind=test_engine)
        try:
            initiate_payment(session, session.get(User, user_id), _payload(), blocking)
        except BaseException as exc:  # pragma: no cover - surfaced below
            failures.append(exc)
        finally:
            session.close()

    thread = threading.Thread(target=first)
    thread.start()
    try:
        assert blocking.entered.wait(timeout=10), "first initiate never started"
        with Session(bind=test_engine) as session:
            with pytest.raises(TicketSoldOutError):
                initiate_payment(
                    session,
                    session.get(User, user_id),
                    _payload(),
                    SimulatedMBWayGateway(),
                )
    finally:
        blocking.release.set()
        thread.join(timeout=10)

    assert failures == []
    assert _count_transactions(test_engine, ticket_id) == 1


@requires_postgres
def test_stock_check_and_reservation_are_atomic(db_session, test_engine):
    ticket = seed_ticket_tiers(db_session)[TicketTier.GERAL]
    ticket.inventory_limit = 1
    user = _make_user(db_session, "ana@example.com")
    db_session.commit()
    ticket_id, user_id = ticket.id, user.id

    session_a = Session(bind=test_engine)
    first_commit = threading.Event()
    release = threading.Event()
    commits = {"n": 0}

    @event.listens_for(session_a, "before_commit")
    def _hold_first_commit(session) -> None:
        commits["n"] += 1
        if commits["n"] == 1:
            first_commit.set()
            assert release.wait(timeout=10)

    a_outcome: dict[str, object] = {}

    def first() -> None:
        try:
            initiate_payment(
                session_a,
                session_a.get(User, user_id),
                _payload(),
                SimulatedMBWayGateway(),
            )
            a_outcome["ok"] = True
        except BaseException as exc:  # pragma: no cover - surfaced below
            a_outcome["error"] = exc
        finally:
            session_a.close()

    b_done = threading.Event()
    b_outcome: dict[str, object] = {}

    def second() -> None:
        session = Session(bind=test_engine)
        try:
            initiate_payment(
                session,
                session.get(User, user_id),
                _payload(),
                SimulatedMBWayGateway(),
            )
            b_outcome["ok"] = True
        except BaseException as exc:  # pragma: no cover - surfaced below
            b_outcome["error"] = exc
        finally:
            session.close()
            b_done.set()

    thread_a = threading.Thread(target=first)
    thread_a.start()
    assert first_commit.wait(timeout=10), "first transaction never reached commit"

    thread_b = threading.Thread(target=second)
    thread_b.start()
    try:
        assert not b_done.wait(timeout=0.5), (
            "second request did not wait for the ticket lock while the first "
            "held it mid-transaction"
        )
    finally:
        release.set()
        thread_a.join(timeout=10)
        thread_b.join(timeout=10)

    assert a_outcome.get("ok") is True, a_outcome.get("error")
    assert isinstance(b_outcome.get("error"), TicketSoldOutError), b_outcome
    assert _count_transactions(test_engine, ticket_id) == 1
