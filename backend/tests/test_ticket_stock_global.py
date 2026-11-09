"""The seats for sale are one number for all modalities (TICKET_STOCK_LIMIT)."""

import os
import threading

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.core.security import hash_password
from app.domains.payments import set_price as set_price_cli
from app.domains.payments.gateway import SimulatedMBWayGateway
from app.domains.payments.models import TicketTier, Transaction, TransactionStatus
from app.domains.payments.schemas import PaymentInitiateRequest
from app.domains.payments.service import (
    TicketSoldOutError,
    confirm_transaction,
    initiate_payment,
    list_ticket_tiers,
)
from app.domains.tickets.models import PaymentStatus, Ticket
from app.domains.users.models import StudentVerificationStatus, User
from tests.helpers import seed_ticket_tiers

requires_postgres = pytest.mark.skipif(
    not (os.environ.get("TEST_DATABASE_URL") or "").startswith("postgresql"),
    reason="row-level locking requires PostgreSQL",
)

GERAL = TicketTier.GERAL
COMPLETO = TicketTier.COMPLETO
ACESSO = TicketTier.ACESSO


def make_user(db_session: Session, n: int) -> User:
    user = User(
        name=f"Pessoa {n}",
        email=f"pessoa{n}@example.com",
        password_hash=hash_password("Password123!"),
        # Some modalities are for students only: every buyer here may buy any of them.
        student_verification_status=StudentVerificationStatus.VERIFIED,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def buy(db_session: Session, user: User, tier: TicketTier) -> Transaction:
    payload = PaymentInitiateRequest(ticket_tier=tier, phone="912345678")
    transaction, _ = initiate_payment(
        db_session, user, payload, SimulatedMBWayGateway()
    )
    return transaction


@pytest.fixture
def shop(db_session):
    seed_ticket_tiers(db_session)
    return db_session


def test_the_default_is_600_seats():
    assert Settings.model_fields["TICKET_STOCK_LIMIT"].default == 600


def test_the_seats_are_shared_by_every_modality(shop):
    settings.TICKET_STOCK_LIMIT = 2

    buy(shop, make_user(shop, 1), GERAL)
    buy(shop, make_user(shop, 2), COMPLETO)

    with pytest.raises(TicketSoldOutError):
        buy(shop, make_user(shop, 3), ACESSO)
    with pytest.raises(TicketSoldOutError):
        buy(shop, make_user(shop, 4), GERAL)


def test_a_modality_has_no_limit_of_its_own(shop):
    settings.TICKET_STOCK_LIMIT = 5

    for n in range(1, 6):
        buy(shop, make_user(shop, n), GERAL)  # five of the same one: no per-tier cap

    with pytest.raises(TicketSoldOutError):
        buy(shop, make_user(shop, 6), COMPLETO)


@pytest.mark.parametrize(
    "freed",
    [
        TransactionStatus.FAILED,
        TransactionStatus.EXPIRED,
        TransactionStatus.REFUNDED,
        TransactionStatus.REFUND_DUE,
    ],
)
def test_a_payment_that_is_over_gives_its_seat_back_to_any_modality(shop, freed):
    settings.TICKET_STOCK_LIMIT = 1
    first = buy(shop, make_user(shop, 1), GERAL)
    with pytest.raises(TicketSoldOutError):
        buy(shop, make_user(shop, 2), COMPLETO)

    first.status = freed
    shop.commit()

    assert buy(shop, make_user(shop, 3), COMPLETO).status is TransactionStatus.PENDING


def test_a_paid_payment_keeps_its_seat(shop):
    settings.TICKET_STOCK_LIMIT = 1
    first = buy(shop, make_user(shop, 1), GERAL)
    confirm_transaction(shop, first)

    with pytest.raises(TicketSoldOutError):
        buy(shop, make_user(shop, 2), COMPLETO)


def test_a_limit_of_zero_sells_nothing(shop):
    settings.TICKET_STOCK_LIMIT = 0

    with pytest.raises(TicketSoldOutError):
        buy(shop, make_user(shop, 1), GERAL)
    assert all(not row.available for row in list_ticket_tiers(shop))


def test_the_modalities_are_available_while_there_are_seats_and_not_after(shop):
    settings.TICKET_STOCK_LIMIT = 2
    assert all(row.available for row in list_ticket_tiers(shop))

    buy(shop, make_user(shop, 1), GERAL)
    assert all(row.available for row in list_ticket_tiers(shop))

    buy(shop, make_user(shop, 2), GERAL)
    rows = list_ticket_tiers(shop)
    assert all(not row.available for row in rows)
    assert all(row.sale_open for row in rows)  # still on sale and priced, just full


def test_tickets_that_were_not_sold_on_the_site_do_not_take_a_seat(shop):
    """The organisation's and guests' tickets have no payment on the site."""
    settings.TICKET_STOCK_LIMIT = 1
    guest = make_user(shop, 9)
    shop.add(
        Ticket(
            user_id=guest.id,
            transaction_reference="GUEST-0001",
            payment_status=PaymentStatus.PAID,
        )
    )
    shop.commit()

    assert buy(shop, make_user(shop, 1), GERAL).status is TransactionStatus.PENDING


def test_a_late_payment_for_the_last_seat_of_another_modality_is_kept_for_a_refund(
    shop,
):
    settings.TICKET_STOCK_LIMIT = 1
    late = buy(shop, make_user(shop, 1), GERAL)
    late.status = TransactionStatus.EXPIRED  # it ran out, the seat was given back
    shop.commit()
    buy_other = buy(shop, make_user(shop, 2), COMPLETO)
    confirm_transaction(shop, buy_other)  # somebody else took the seat

    confirm_transaction(shop, late)  # ...and now the first one is paid after all

    shop.refresh(late)
    assert late.status is TransactionStatus.REFUND_DUE


def test_the_command_has_no_stock_option_any_more(capsys):
    with pytest.raises(SystemExit):
        set_price_cli.main(["geral", "3500", "--stock", "5"])

    assert "--stock" in capsys.readouterr().err


@requires_postgres
def test_simultaneous_buyers_of_different_modalities_never_oversell(
    db_session, test_engine
):
    seed_ticket_tiers(db_session)
    settings.TICKET_STOCK_LIMIT = 3
    users = [make_user(db_session, n).id for n in range(1, 13)]
    tiers = [GERAL, COMPLETO, ACESSO]
    barrier = threading.Barrier(len(users))
    outcomes: list[str] = []
    errors: list[BaseException] = []

    def run(user_id: int, tier: TicketTier) -> None:
        with Session(bind=test_engine) as session:
            try:
                barrier.wait(timeout=10)
                payload = PaymentInitiateRequest(ticket_tier=tier, phone="912345678")
                initiate_payment(
                    session,
                    session.get(User, user_id),
                    payload,
                    SimulatedMBWayGateway(),
                )
                outcomes.append("sold")
            except TicketSoldOutError:
                outcomes.append("sold out")
            except BaseException as exc:  # pragma: no cover - surfaced below
                errors.append(exc)

    threads = [
        threading.Thread(target=run, args=(user_id, tiers[i % len(tiers)]))
        for i, user_id in enumerate(users)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert errors == []
    with Session(bind=test_engine) as session:
        held = session.scalar(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.status == TransactionStatus.PENDING)
        )
    assert outcomes.count("sold") == 3
    assert outcomes.count("sold out") == 9
    assert held == 3
