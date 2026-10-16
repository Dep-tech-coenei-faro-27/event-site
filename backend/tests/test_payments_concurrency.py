import os
import threading
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
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
from app.domains.payments.service import (
    AlreadyHasTicketError,
    TicketSoldOutError,
    confirm_transaction,
    get_transaction,
    handle_payment_callback,
    initiate_payment,
)
from app.domains.tickets.models import Ticket
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
            .where(Transaction.ticket_tier_id == ticket_id)
        )


@requires_postgres
def test_concurrent_initiates_do_not_oversell(db_session, test_engine):
    ticket = seed_ticket_tiers(db_session)[TicketTier.GERAL]
    ticket.inventory_limit = 1
    user = _make_user(db_session, "ana@example.com")
    other = _make_user(db_session, "rui@example.com")
    db_session.commit()
    ticket_id, user_id, other_id = ticket.id, user.id, other.id

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
                    session.get(User, other_id),
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
    other = _make_user(db_session, "rui@example.com")
    db_session.commit()
    ticket_id, user_id, other_id = ticket.id, user.id, other.id

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
                session.get(User, other_id),
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


@requires_postgres
def test_the_same_person_cannot_start_two_payments_at_the_same_time(
    db_session, test_engine
):
    seed_ticket_tiers(db_session)
    user = _make_user(db_session, "ana@example.com")
    db_session.commit()
    user_id = user.id

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
            "the second request did not wait for the user lock while the first "
            "held it mid-transaction"
        )
    finally:
        release.set()
        thread_a.join(timeout=10)
        thread_b.join(timeout=10)

    assert a_outcome.get("ok") is True, a_outcome.get("error")
    assert isinstance(b_outcome.get("error"), AlreadyHasTicketError), b_outcome
    with Session(bind=test_engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Transaction)
                .where(Transaction.user_id == user_id)
            )
            == 1
        )


@requires_postgres
def test_deleting_a_user_with_transactions_is_blocked(db_session):
    ticket = seed_ticket_tiers(db_session)[TicketTier.GERAL]
    user = _make_user(db_session, "ana@example.com")
    db_session.add(
        Transaction(
            reference="ENEI-RESTRICT0",
            user_id=user.id,
            ticket_tier_id=ticket.id,
            amount_cents=5000,
            quantity=1,
            status=TransactionStatus.PENDING,
            phone="912345678",
            provider="seed",
            expires_at=datetime.now(UTC) + timedelta(minutes=4),
        )
    )
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(delete(User).where(User.id == user.id))
        db_session.commit()
    db_session.rollback()


def _run_together(test_engine, actions) -> list[BaseException]:
    """Run each action in its own session and thread, released at the same moment."""
    barrier = threading.Barrier(len(actions))
    failures: list[BaseException] = []

    def worker(action) -> None:
        session = Session(bind=test_engine)
        try:
            barrier.wait(timeout=10)
            action(session)
        except BaseException as exc:  # surfaced by the caller
            failures.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=worker, args=(action,)) for action in actions]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return failures


def _count_tickets(test_engine, user_id: int) -> int:
    with Session(bind=test_engine) as session:
        return session.scalar(
            select(func.count()).select_from(Ticket).where(Ticket.user_id == user_id)
        )


@requires_postgres
def test_two_confirmations_of_the_same_payment_issue_one_ticket(
    db_session, test_engine
):
    """A status poll and a callback (or two polls) can arrive together."""
    seed_ticket_tiers(db_session)
    user = _make_user(db_session, "ana@example.com")
    transaction, _ = initiate_payment(
        db_session, user, _payload(), SimulatedMBWayGateway()
    )
    transaction_id, user_id = transaction.id, user.id
    integrity_errors: list[object] = []

    def count_integrity_errors(context) -> None:
        if isinstance(context.original_exception, Exception) and (
            "unique" in str(context.original_exception).lower()
        ):
            integrity_errors.append(context.original_exception)

    event.listen(test_engine, "handle_error", count_integrity_errors)

    def confirm(session: Session) -> None:
        confirm_transaction(session, session.get(Transaction, transaction_id))

    try:
        assert _run_together(test_engine, [confirm, confirm]) == []
    finally:
        event.remove(test_engine, "handle_error", count_integrity_errors)
    assert _count_tickets(test_engine, user_id) == 1
    # The row lock makes the second confirmation wait instead of colliding.
    assert integrity_errors == []


@requires_postgres
def test_a_poll_does_not_overwrite_a_payment_confirmed_while_it_waited(
    db_session, test_engine, monkeypatch
):
    """The poll asks the provider, which says "expired"; meanwhile the callback
    confirms the payment. The poll must not then write ``expired`` over it."""
    monkeypatch.setattr(settings, "MBWAY_CALLBACK_KEY", "callback-key")
    seed_ticket_tiers(db_session)
    user = _make_user(db_session, "ana@example.com")
    transaction, _ = initiate_payment(
        db_session, user, _payload(), SimulatedMBWayGateway()
    )
    transaction_id, reference, user_id = transaction.id, transaction.reference, user.id
    amount = str(transaction.amount_cents / 100)

    class CallbackWhileAsking:
        name = "racing"

        def get_status(self, *, reference, provider_reference) -> TransactionStatus:
            with Session(bind=test_engine) as other:
                handle_payment_callback(
                    other, key="callback-key", reference=reference, amount=amount
                )
            return TransactionStatus.EXPIRED

    with Session(bind=test_engine) as poll:
        seen = get_transaction(
            poll, poll.get(User, user_id), reference, CallbackWhileAsking()
        )
        assert seen.status is TransactionStatus.CONFIRMED

    with Session(bind=test_engine) as check:
        stored = check.scalar(
            select(Transaction.status).where(Transaction.id == transaction_id)
        )
    assert stored is TransactionStatus.CONFIRMED
    assert _count_tickets(test_engine, user_id) == 1


@requires_postgres
def test_two_payments_of_the_same_person_confirmed_together_issue_one_ticket(
    db_session, test_engine
):
    """The first attempt ran out locally, a second was started, and both get paid."""
    seed_ticket_tiers(db_session)
    user = _make_user(db_session, "ana@example.com")
    first, _ = initiate_payment(db_session, user, _payload(), SimulatedMBWayGateway())
    first.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()
    second, _ = initiate_payment(db_session, user, _payload(), SimulatedMBWayGateway())
    ids, user_id = [first.id, second.id], user.id

    def confirm(transaction_id: int):
        def action(session: Session) -> None:
            confirm_transaction(session, session.get(Transaction, transaction_id))

        return action

    assert _run_together(test_engine, [confirm(i) for i in ids]) == []
    assert _count_tickets(test_engine, user_id) == 1
    with Session(bind=test_engine) as session:
        statuses = session.scalars(
            select(Transaction.status).where(Transaction.id.in_(ids))
        ).all()
    assert sorted(statuses, key=str) == [
        TransactionStatus.CONFIRMED,
        TransactionStatus.REFUND_DUE,
    ]
