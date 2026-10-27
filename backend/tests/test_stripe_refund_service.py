"""Ending a Stripe payment that waits too long, and refunding payments and tickets."""

import re
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.domains.payments import refund as refund_cli
from app.domains.payments.gateway import (
    AlreadyRefundedError,
    MBWayPayment,
    PaymentGatewayError,
)
from app.domains.payments.models import (
    TicketTier,
    Transaction,
    TransactionStatus,
)
from app.domains.payments.schemas import PaymentInitiateRequest
from app.domains.payments.service import (
    AlreadyHasTicketError,
    NothingToRefundError,
    RefundNotSupportedError,
    TicketSoldOutError,
    _recover_provider_reference,
    confirm_transaction,
    get_transaction,
    initiate_payment,
    payment_description,
    refund_payment,
    refundable_references,
)
from app.domains.tickets.models import PaymentStatus, Ticket
from tests.helpers import authenticate, seed_ticket_tiers

INTENT = "pi_3USkViKnHPoxsDHG1o4JvnxP"
GERAL = TicketTier.GERAL


class StripeLike:
    """What the service needs of Stripe, with answers the tests choose."""

    name = "stripe"

    def __init__(self):
        self.status = TransactionStatus.PENDING
        self.cancel_outcome = TransactionStatus.EXPIRED
        self.cancel_error: Exception | None = None
        self.refund_error: Exception | None = None
        self.cancel_calls: list[tuple] = []
        self.refund_calls: list[dict] = []
        self.created = 0
        self.found: str | None = None
        self.find_error: Exception | None = None
        self.find_calls: list[str] = []

    def find_payment(self, *, reference):
        self.find_calls.append(reference)
        if self.find_error is not None:
            raise self.find_error
        return self.found

    def create_payment(self, *, reference, amount_cents, phone, email, description):
        self.created += 1
        return MBWayPayment(provider_reference=f"pi_new{self.created}")

    def get_status(self, *, reference, provider_reference):
        return self.status

    def cancel_payment(self, *, reference, provider_reference):
        self.cancel_calls.append((reference, provider_reference))
        if self.cancel_error is not None:
            raise self.cancel_error
        return self.cancel_outcome

    def refund(self, *, reference, provider_reference, amount_cents, description):
        self.refund_calls.append(
            {
                "reference": reference,
                "provider_reference": provider_reference,
                "amount_cents": amount_cents,
                "description": description,
            }
        )
        if self.refund_error is not None:
            raise self.refund_error
        return "re_3USkVi"


class PlainGateway:
    """A provider with neither a refund nor a cancel (ifthenpay is one)."""

    name = "ifthenpay"

    def __init__(self):
        self.status = TransactionStatus.PENDING

    def get_status(self, *, reference, provider_reference):
        return self.status


@pytest.fixture
def stripe():
    return StripeLike()


@pytest.fixture(autouse=True)
def grace(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_CANCEL_GRACE_SECONDS", 120)


@pytest.fixture
def shop(auth_client, email_sender, db_session):
    user = authenticate(auth_client, email_sender, db_session)
    tiers = seed_ticket_tiers(db_session)
    return user, tiers


def make_payment(
    db_session,
    shop,
    reference,
    *,
    status=TransactionStatus.PENDING,
    overdue_by=0,
    provider="stripe",
    provider_reference=INTENT,
    user=None,
    amount_cents=2500,
    tier=GERAL,
):
    user_, tiers = shop
    transaction = Transaction(
        reference=reference,
        user_id=(user or user_).id,
        ticket_tier_id=tiers[tier].id,
        amount_cents=amount_cents,
        quantity=1,
        status=status,
        phone="912345678",
        provider=provider,
        provider_reference=provider_reference,
        expires_at=datetime.now(UTC) - timedelta(seconds=overdue_by),
    )
    db_session.add(transaction)
    db_session.commit()
    return transaction


def paid_with_ticket(db_session, shop, reference, **kwargs):
    """A payment confirmed through ``confirm_transaction``: it has its ticket."""
    transaction = make_payment(db_session, shop, reference, **kwargs)
    confirm_transaction(db_session, transaction)
    db_session.refresh(transaction)
    assert transaction.status is TransactionStatus.CONFIRMED
    return transaction


def ticket_of(db_session, reference):
    db_session.expire_all()
    return db_session.scalar(
        select(Ticket).where(Ticket.transaction_reference == reference)
    )


def reload(db_session, transaction):
    db_session.expire_all()
    return db_session.scalar(
        select(Transaction).where(Transaction.reference == transaction.reference)
    )


# --- a payment that still waits after its deadline ----------------------------


def test_stripe_still_waiting_past_the_deadline_and_the_grace_is_cancelled(
    db_session, shop, stripe
):
    transaction = make_payment(db_session, shop, "ENEI-0000000001", overdue_by=121)

    result = get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert result.status is TransactionStatus.EXPIRED
    assert stripe.cancel_calls == [(transaction.reference, INTENT)]


def test_within_the_grace_the_payment_is_left_alone(db_session, shop, stripe):
    transaction = make_payment(db_session, shop, "ENEI-0000000001", overdue_by=60)

    result = get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert result.status is TransactionStatus.PENDING
    assert stripe.cancel_calls == []


def test_before_the_deadline_nothing_is_cancelled(db_session, shop, stripe):
    transaction = make_payment(db_session, shop, "ENEI-0000000001", overdue_by=-30)

    get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert stripe.cancel_calls == []


def test_a_zero_grace_cancels_as_soon_as_the_deadline_passes(
    db_session, shop, stripe, monkeypatch
):
    monkeypatch.setattr(settings, "STRIPE_CANCEL_GRACE_SECONDS", 0)
    transaction = make_payment(db_session, shop, "ENEI-0000000001", overdue_by=1)

    result = get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert result.status is TransactionStatus.EXPIRED


def test_approved_at_the_very_moment_it_is_paid_and_gets_its_ticket(
    db_session, shop, stripe
):
    stripe.cancel_outcome = TransactionStatus.CONFIRMED
    transaction = make_payment(db_session, shop, "ENEI-0000000001", overdue_by=500)

    result = get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert result.status is TransactionStatus.CONFIRMED
    assert ticket_of(db_session, transaction.reference).payment_status is (
        PaymentStatus.PAID
    )


def test_when_stripe_cannot_be_reached_the_payment_stays_as_it_was(
    db_session, shop, stripe
):
    stripe.cancel_error = PaymentGatewayError("stripe unreachable")
    transaction = make_payment(db_session, shop, "ENEI-0000000001", overdue_by=500)

    result = get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert result.status is TransactionStatus.PENDING
    assert len(stripe.cancel_calls) == 1


def test_a_payment_stripe_has_already_ended_is_not_cancelled_again(
    db_session, shop, stripe
):
    stripe.status = TransactionStatus.EXPIRED
    transaction = make_payment(db_session, shop, "ENEI-0000000001", overdue_by=500)

    result = get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert result.status is TransactionStatus.EXPIRED
    assert stripe.cancel_calls == []


def test_a_paid_payment_is_confirmed_by_the_poll_and_never_cancelled(
    db_session, shop, stripe
):
    stripe.status = TransactionStatus.CONFIRMED
    transaction = make_payment(db_session, shop, "ENEI-0000000001", overdue_by=500)

    result = get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert result.status is TransactionStatus.CONFIRMED
    assert stripe.cancel_calls == []


def test_another_provider_is_never_cancelled_through_stripe(db_session, shop, stripe):
    transaction = make_payment(
        db_session, shop, "ENEI-0000000001", overdue_by=500, provider="ifthenpay"
    )

    result = get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert result.status is TransactionStatus.PENDING
    assert stripe.cancel_calls == []


def test_a_gateway_that_cannot_cancel_keeps_the_old_behaviour(db_session, shop):
    transaction = make_payment(db_session, shop, "ENEI-0000000001", overdue_by=500)

    result = get_transaction(db_session, shop[0], transaction.reference, PlainGateway())

    assert result.status is TransactionStatus.PENDING


def test_without_a_provider_reference_there_is_nothing_to_cancel(
    db_session, shop, stripe
):
    transaction = make_payment(
        db_session, shop, "ENEI-0000000001", overdue_by=500, provider_reference=None
    )

    get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert stripe.cancel_calls == []


def test_the_seat_of_a_payment_nobody_follows_is_freed_for_the_next_buyer(
    auth_client, email_sender, db_session, shop, stripe
):
    _, tiers = shop
    settings.TICKET_STOCK_LIMIT = 1
    db_session.commit()
    make_payment(db_session, shop, "ENEI-0000000001", overdue_by=500)
    other = authenticate(auth_client, email_sender, db_session, email="bia@example.com")
    request = PaymentInitiateRequest(ticket_tier=GERAL, phone="912345678")

    transaction, _ = initiate_payment(db_session, other, request, stripe)

    assert transaction.status is TransactionStatus.PENDING
    first = db_session.scalar(
        select(Transaction).where(Transaction.reference == "ENEI-0000000001")
    )
    db_session.refresh(first)
    assert first.status is TransactionStatus.EXPIRED


def test_a_full_modality_with_a_fresh_waiting_payment_stays_sold_out(
    auth_client, email_sender, db_session, shop, stripe
):
    _, tiers = shop
    settings.TICKET_STOCK_LIMIT = 1
    db_session.commit()
    make_payment(db_session, shop, "ENEI-0000000001", overdue_by=10)
    other = authenticate(auth_client, email_sender, db_session, email="bia@example.com")

    with pytest.raises(TicketSoldOutError):
        initiate_payment(
            db_session,
            other,
            PaymentInitiateRequest(ticket_tier=GERAL, phone="912345678"),
            stripe,
        )

    assert stripe.cancel_calls == []


# --- a payment whose id we never saved ------------------------------------------


def test_a_payment_with_no_stripe_id_is_found_and_confirmed_by_the_poll(
    db_session, shop, stripe
):
    """The answer to the creation was lost, the person approved: no webhook needed."""
    stripe.found = INTENT
    stripe.status = TransactionStatus.CONFIRMED
    transaction = make_payment(
        db_session, shop, "ENEI-0000000020", provider_reference=None
    )

    result = get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert result.status is TransactionStatus.CONFIRMED
    assert result.provider_reference == INTENT
    assert ticket_of(db_session, transaction.reference) is not None
    assert stripe.find_calls == [transaction.reference]


def test_a_found_payment_still_waiting_keeps_its_seat_and_gets_its_id(
    db_session, shop, stripe
):
    stripe.found = INTENT
    transaction = make_payment(
        db_session, shop, "ENEI-0000000020", provider_reference=None
    )

    result = get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert result.status is TransactionStatus.PENDING
    assert result.provider_reference == INTENT


def test_a_found_payment_past_its_deadline_is_then_cancelled_like_any_other(
    db_session, shop, stripe
):
    stripe.found = INTENT
    transaction = make_payment(
        db_session,
        shop,
        "ENEI-0000000020",
        provider_reference=None,
        overdue_by=500,
    )

    result = get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert result.status is TransactionStatus.EXPIRED
    assert stripe.cancel_calls == [(transaction.reference, INTENT)]


def test_not_found_yet_changes_nothing(db_session, shop, stripe):
    transaction = make_payment(
        db_session, shop, "ENEI-0000000020", provider_reference=None
    )

    result = get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert result.status is TransactionStatus.PENDING
    assert result.provider_reference is None


def test_a_failed_search_changes_nothing(db_session, shop, stripe):
    stripe.find_error = PaymentGatewayError("stripe unreachable")
    transaction = make_payment(
        db_session, shop, "ENEI-0000000020", provider_reference=None
    )

    result = get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert result.status is TransactionStatus.PENDING
    assert result.provider_reference is None


def test_a_payment_that_already_has_its_id_is_never_searched(db_session, shop, stripe):
    transaction = make_payment(db_session, shop, "ENEI-0000000020")

    get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert stripe.find_calls == []


def test_another_provider_is_never_searched_at_stripe(db_session, shop, stripe):
    stripe.found = INTENT
    transaction = make_payment(
        db_session,
        shop,
        "ENEI-0000000020",
        provider="ifthenpay",
        provider_reference=None,
    )

    get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert stripe.find_calls == []
    assert reload(db_session, transaction).provider_reference is None


def test_a_gateway_that_cannot_search_keeps_the_old_behaviour(db_session, shop):
    transaction = make_payment(
        db_session, shop, "ENEI-0000000020", provider_reference=None
    )

    result = get_transaction(db_session, shop[0], transaction.reference, PlainGateway())

    assert result.status is TransactionStatus.PENDING


def test_the_search_is_throttled_like_any_other_question_to_the_provider(
    db_session, shop, stripe, monkeypatch
):
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER_MIN_INTERVAL_SECONDS", 60)
    transaction = make_payment(
        db_session, shop, "ENEI-0000000020", provider_reference=None
    )

    get_transaction(db_session, shop[0], transaction.reference, stripe)
    get_transaction(db_session, shop[0], transaction.reference, stripe)

    assert len(stripe.find_calls) == 1


def test_an_id_that_arrived_meanwhile_is_not_overwritten(db_session, shop, stripe):
    """The webhook saved the id between the search and our write: keep theirs."""
    stripe.found = "pi_3SomeOtherIntentxxxxxx"
    transaction = make_payment(
        db_session, shop, "ENEI-0000000020", provider_reference=INTENT
    )

    assert (
        _recover_provider_reference(db_session, transaction.reference, stripe) is None
    )
    assert reload(db_session, transaction).provider_reference == INTENT


# --- refunds ---------------------------------------------------------------


def test_a_refund_due_is_refunded_through_the_provider(db_session, shop, stripe):
    transaction = make_payment(
        db_session, shop, "ENEI-0000000002", status=TransactionStatus.REFUND_DUE
    )

    result = refund_payment(db_session, transaction.reference, stripe)

    assert result.status is TransactionStatus.REFUNDED
    assert stripe.refund_calls == [
        {
            "reference": "ENEI-0000000002",
            "provider_reference": INTENT,
            "amount_cents": 2500,
            "description": "ENEI - Passe geral",
        }
    ]


@pytest.mark.parametrize("tier", list(TicketTier))
def test_the_refund_says_which_event_and_product_it_is_for(
    db_session, shop, stripe, tier
):
    """Same text as the payment: ``ENEI - <product name>`` for every modality."""
    transaction = make_payment(
        db_session,
        shop,
        "ENEI-0000000002",
        status=TransactionStatus.REFUND_DUE,
        tier=tier,
    )

    refund_payment(db_session, transaction.reference, stripe)

    assert stripe.refund_calls[0]["description"] == payment_description(tier)


def test_a_refund_due_never_touches_the_ticket_of_another_payment(
    db_session, shop, stripe
):
    kept = paid_with_ticket(
        db_session, shop, "ENEI-0000000003", provider_reference="pi_a"
    )
    make_payment(
        db_session,
        shop,
        "ENEI-0000000004",
        status=TransactionStatus.REFUND_DUE,
        provider_reference="pi_b",
    )

    refund_payment(db_session, "ENEI-0000000004", stripe)

    assert ticket_of(db_session, kept.reference).payment_status is PaymentStatus.PAID
    assert reload(db_session, kept).status is TransactionStatus.CONFIRMED


def test_refunding_a_paid_ticket_cancels_it_and_frees_its_seat(
    db_session, shop, stripe
):
    transaction = paid_with_ticket(db_session, shop, "ENEI-0000000005")

    result = refund_payment(db_session, transaction.reference, stripe)

    assert result.status is TransactionStatus.REFUNDED
    ticket = ticket_of(db_session, transaction.reference)
    assert ticket.payment_status is PaymentStatus.CANCELLED
    assert [call["amount_cents"] for call in stripe.refund_calls] == [2500]


def test_the_person_can_buy_again_after_the_refund_of_their_ticket(
    db_session, shop, stripe
):
    user, _ = shop
    transaction = paid_with_ticket(db_session, shop, "ENEI-0000000005")
    with pytest.raises(AlreadyHasTicketError):
        initiate_payment(
            db_session,
            user,
            PaymentInitiateRequest(ticket_tier=GERAL, phone="912345678"),
            stripe,
        )

    refund_payment(db_session, transaction.reference, stripe)

    again, _ = initiate_payment(
        db_session,
        user,
        PaymentInitiateRequest(ticket_tier=GERAL, phone="912345678"),
        stripe,
    )
    assert again.status is TransactionStatus.PENDING


def test_repeating_a_refund_changes_nothing_and_never_asks_the_provider_again(
    db_session, shop, stripe
):
    transaction = make_payment(
        db_session, shop, "ENEI-0000000002", status=TransactionStatus.REFUND_DUE
    )
    refund_payment(db_session, transaction.reference, stripe)

    again = refund_payment(db_session, transaction.reference, stripe)

    assert again.status is TransactionStatus.REFUNDED
    assert len(stripe.refund_calls) == 1


def test_a_payment_the_provider_already_refunded_is_closed_here_too(
    db_session, shop, stripe
):
    stripe.refund_error = AlreadyRefundedError("already refunded")
    transaction = paid_with_ticket(db_session, shop, "ENEI-0000000005")

    result = refund_payment(db_session, transaction.reference, stripe)

    assert result.status is TransactionStatus.REFUNDED
    assert (
        ticket_of(db_session, transaction.reference).payment_status
        is PaymentStatus.CANCELLED
    )


def test_when_the_provider_fails_nothing_changes_and_it_can_be_run_again(
    db_session, shop, stripe
):
    stripe.refund_error = PaymentGatewayError("stripe unreachable")
    transaction = paid_with_ticket(db_session, shop, "ENEI-0000000005")

    with pytest.raises(PaymentGatewayError):
        refund_payment(db_session, transaction.reference, stripe)

    assert reload(db_session, transaction).status is TransactionStatus.CONFIRMED
    assert (
        ticket_of(db_session, transaction.reference).payment_status
        is PaymentStatus.PAID
    )
    stripe.refund_error = None
    assert (
        refund_payment(db_session, transaction.reference, stripe).status
        is TransactionStatus.REFUNDED
    )


@pytest.mark.parametrize(
    "status",
    [
        TransactionStatus.PENDING,
        TransactionStatus.FAILED,
        TransactionStatus.EXPIRED,
    ],
)
def test_a_payment_that_was_never_paid_has_nothing_to_refund(
    db_session, shop, stripe, status
):
    transaction = make_payment(db_session, shop, "ENEI-0000000006", status=status)

    with pytest.raises(NothingToRefundError):
        refund_payment(db_session, transaction.reference, stripe)

    assert stripe.refund_calls == []
    assert reload(db_session, transaction).status is status


def test_an_unknown_reference_has_nothing_to_refund(db_session, shop, stripe):
    with pytest.raises(NothingToRefundError):
        refund_payment(db_session, "ENEI-9999999999", stripe)


def test_a_payment_of_another_provider_is_never_refunded_through_this_one(
    db_session, shop, stripe
):
    transaction = make_payment(
        db_session,
        shop,
        "ENEI-0000000007",
        status=TransactionStatus.REFUND_DUE,
        provider="ifthenpay",
    )

    with pytest.raises(RefundNotSupportedError):
        refund_payment(db_session, transaction.reference, stripe)

    assert stripe.refund_calls == []
    assert reload(db_session, transaction).status is TransactionStatus.REFUND_DUE


def test_a_provider_without_a_refund_api_is_left_to_be_done_by_hand(db_session, shop):
    transaction = make_payment(
        db_session,
        shop,
        "ENEI-0000000007",
        status=TransactionStatus.REFUND_DUE,
        provider="ifthenpay",
    )

    with pytest.raises(RefundNotSupportedError, match="provider's own panel"):
        refund_payment(db_session, transaction.reference, PlainGateway())


def test_a_payment_without_a_provider_reference_cannot_be_refunded_here(
    db_session, shop, stripe
):
    transaction = make_payment(
        db_session,
        shop,
        "ENEI-0000000008",
        status=TransactionStatus.REFUND_DUE,
        provider_reference=None,
    )

    with pytest.raises(RefundNotSupportedError):
        refund_payment(db_session, transaction.reference, stripe)


def test_the_payments_waiting_for_a_refund_are_listed_oldest_first(
    db_session, shop, stripe
):
    make_payment(
        db_session,
        shop,
        "ENEI-0000000010",
        status=TransactionStatus.REFUND_DUE,
        provider_reference="pi_1",
    )
    make_payment(
        db_session,
        shop,
        "ENEI-0000000011",
        status=TransactionStatus.REFUNDED,
        provider_reference="pi_2",
    )
    make_payment(
        db_session,
        shop,
        "ENEI-0000000012",
        status=TransactionStatus.CONFIRMED,
        provider_reference="pi_3",
    )

    assert refundable_references(db_session) == ["ENEI-0000000010"]


# --- the command -----------------------------------------------------------


@pytest.fixture
def command(monkeypatch, test_engine, stripe):
    monkeypatch.setattr(
        refund_cli,
        "SessionLocal",
        sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False),
    )
    monkeypatch.setattr(refund_cli, "get_mbway_gateway", lambda: stripe)
    return refund_cli.main


def test_the_command_refunds_one_payment(db_session, shop, stripe, command, capsys):
    transaction = paid_with_ticket(db_session, shop, "ENEI-0000000005")

    assert command([transaction.reference]) == 0

    out = capsys.readouterr().out
    assert "ENEI-0000000005: refunded (25.00 EUR)" in out
    assert reload(db_session, transaction).status is TransactionStatus.REFUNDED
    assert ticket_of(db_session, transaction.reference).payment_status is (
        PaymentStatus.CANCELLED
    )


def test_the_command_run_twice_refunds_once(db_session, shop, stripe, command):
    transaction = paid_with_ticket(db_session, shop, "ENEI-0000000005")

    assert command([transaction.reference]) == 0
    assert command([transaction.reference]) == 0

    assert len(stripe.refund_calls) == 1


def test_due_goes_through_every_payment_waiting_and_only_those(
    db_session, shop, stripe, command, capsys
):
    make_payment(
        db_session,
        shop,
        "ENEI-0000000010",
        status=TransactionStatus.REFUND_DUE,
        provider_reference="pi_1",
    )
    make_payment(
        db_session,
        shop,
        "ENEI-0000000011",
        status=TransactionStatus.REFUND_DUE,
        provider_reference="pi_2",
    )
    paid = paid_with_ticket(
        db_session, shop, "ENEI-0000000012", provider_reference="pi_3"
    )

    assert command(["--due"]) == 0

    assert sorted(call["reference"] for call in stripe.refund_calls) == [
        "ENEI-0000000010",
        "ENEI-0000000011",
    ]
    assert reload(db_session, paid).status is TransactionStatus.CONFIRMED


def test_due_with_nothing_waiting_says_so(db_session, shop, stripe, command, capsys):
    assert command(["--due"]) == 0

    assert "Nothing waiting for a refund." in capsys.readouterr().out


def test_a_failure_is_reported_exits_with_an_error_and_goes_on_with_the_rest(
    db_session, shop, stripe, command, capsys
):
    make_payment(
        db_session,
        shop,
        "ENEI-0000000010",
        status=TransactionStatus.REFUND_DUE,
        provider_reference="pi_1",
    )
    make_payment(
        db_session,
        shop,
        "ENEI-0000000011",
        status=TransactionStatus.REFUND_DUE,
        provider_reference="pi_2",
    )
    original = stripe.refund

    def flaky(*, reference, provider_reference, amount_cents, description):
        if reference == "ENEI-0000000010":
            raise PaymentGatewayError("stripe unreachable")
        return original(
            reference=reference,
            provider_reference=provider_reference,
            amount_cents=amount_cents,
            description=description,
        )

    stripe.refund = flaky

    assert command(["--due"]) == 1

    out = capsys.readouterr().out
    assert "ENEI-0000000010: NOT refunded" in out
    assert "ENEI-0000000011: refunded" in out


def test_quiet_prints_nothing_when_nothing_waits(
    db_session, shop, stripe, command, capsys
):
    assert command(["--due", "--quiet"]) == 0

    assert capsys.readouterr().out == ""


def test_quiet_puts_the_time_on_every_line_and_still_refunds(
    db_session, shop, stripe, command, capsys
):
    make_payment(
        db_session, shop, "ENEI-0000000010", status=TransactionStatus.REFUND_DUE
    )

    assert command(["--due", "--quiet"]) == 0

    out = capsys.readouterr().out.strip()
    assert re.fullmatch(
        r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ ENEI-0000000010: refunded \(25\.00 EUR\)", out
    )
    assert len(stripe.refund_calls) == 1


def test_quiet_still_reports_a_failure_and_exits_with_an_error(
    db_session, shop, stripe, command, capsys
):
    stripe.refund_error = PaymentGatewayError("stripe unreachable")
    make_payment(
        db_session, shop, "ENEI-0000000010", status=TransactionStatus.REFUND_DUE
    )

    assert command(["--due", "--quiet"]) == 1

    out = capsys.readouterr().out
    assert "ENEI-0000000010: NOT refunded" in out
    assert out.startswith("20")  # the time


def test_without_quiet_the_output_has_no_time(
    db_session, shop, stripe, command, capsys
):
    make_payment(
        db_session, shop, "ENEI-0000000010", status=TransactionStatus.REFUND_DUE
    )

    command(["--due"])

    assert capsys.readouterr().out.startswith("ENEI-0000000010: refunded")


def test_a_payment_that_is_not_a_refund_due_is_never_taken_by_the_schedule(
    db_session, shop, stripe, command
):
    """``--due`` is the only thing a schedule runs: a paid ticket is never refunded."""
    paid = paid_with_ticket(
        db_session, shop, "ENEI-0000000012", provider_reference="pi_3"
    )

    assert command(["--due", "--quiet"]) == 0

    assert stripe.refund_calls == []
    assert reload(db_session, paid).status is TransactionStatus.CONFIRMED


def test_the_command_needs_a_reference_or_due_and_not_both(command):
    with pytest.raises(SystemExit):
        command([])
    with pytest.raises(SystemExit):
        command(["ENEI-0000000001", "--due"])


def test_the_output_never_names_the_person(db_session, shop, stripe, command, capsys):
    transaction = paid_with_ticket(db_session, shop, "ENEI-0000000005")

    command([transaction.reference])

    out = capsys.readouterr().out
    assert "ana@example.com" not in out
    assert "912345678" not in out
