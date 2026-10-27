import hmac
import logging
import secrets
import threading
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import String, cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email.models import EmailOutbox
from app.core.email.outbox import enqueue_email
from app.core.email.templates import (
    TICKET_EMAIL_SUBJECT,
    TICKET_QR_CID,
    build_ticket_email,
)
from app.core.qr import render_qr_png
from app.domains.payments.events import notify
from app.domains.payments.gateway import (
    AlreadyRefundedError,
    CancellingGateway,
    LookupGateway,
    MBWayGateway,
    PaymentGatewayError,
    RefundingGateway,
    UnrecognisedStatusError,
    stripe_status,
)
from app.domains.payments.models import (
    TicketTier,
    TicketTierPrice,
    Transaction,
    TransactionStatus,
)
from app.domains.payments.schemas import (
    PaymentInitiateRequest,
    TicketTierRead,
    TransactionRead,
)
from app.domains.payments.tiers import TIER_SPECS
from app.domains.tickets.models import PaymentStatus, Ticket
from app.domains.tickets.service import (
    PaymentNotConfirmedError,
    TicketNotFoundError,
    issue_ticket_for_paid_transaction,
)
from app.domains.users.models import StudentVerificationStatus, User

logger = logging.getLogger(__name__)

REFERENCE_PREFIX = "ENEI-"
REFERENCE_LENGTH = 15


class PaymentError(RuntimeError):
    status_code = 400


class TicketOfficeClosedError(PaymentError):
    status_code = 503


class TicketUnavailableError(PaymentError):
    status_code = 409


class TicketSoldOutError(PaymentError):
    status_code = 409


class StudentVerificationRequiredError(PaymentError):
    status_code = 403


class AlreadyHasTicketError(PaymentError):
    status_code = 409


class InvalidCallbackKeyError(PaymentError):
    status_code = 403


class CallbackTransactionNotFoundError(PaymentError):
    status_code = 404


class CallbackAmountMismatchError(PaymentError):
    status_code = 400


class NothingToRefundError(PaymentError):
    """The payment was not paid, or does not exist."""

    status_code = 409


class RefundNotSupportedError(PaymentError):
    """The payment was made through a provider that cannot refund through its API."""

    status_code = 409


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _callback_key_matches(provided: str | None) -> bool:
    """Constant-time check of the ifthenpay anti-phishing key."""
    expected = settings.MBWAY_CALLBACK_KEY
    if not provided or not expected:
        return False
    return hmac.compare_digest(provided, expected)


def _callback_amount_matches(raw_amount: str | None, amount_cents: int) -> bool:
    if raw_amount is None:
        return False
    try:
        return Decimal(raw_amount) * 100 == amount_cents
    except (InvalidOperation, ValueError):
        return False


def generate_reference(db: Session) -> str:
    """A short, human-readable, unique payment reference (max 15 chars)."""
    for _ in range(10):
        # "ENEI-" + 10 hex chars == 15 characters, matching the UI mockup.
        reference = REFERENCE_PREFIX + secrets.token_hex(5).upper()
        if REFERENCE_LENGTH != len(reference):
            raise RuntimeError("reference length must stay at 15 characters")
        exists = db.scalar(
            select(Transaction.id).where(Transaction.reference == reference)
        )
        if exists is None:
            return reference
    raise RuntimeError("could not generate a unique payment reference")


def _reserved_quantity(db: Session, tier: TicketTierPrice) -> int:
    """Seats taken: paid ones, and the ones reserved for a payment that is waiting.

    A waiting payment keeps its seat for as long as it is ``pending``, however long
    that takes: the seat is released only when the provider says the payment is over
    (paid payments stay counted, failed and expired ones are not). That is what
    makes it impossible to sell a seat that someone is about to pay for.
    """
    holds = db.scalar(
        select(func.coalesce(func.sum(Transaction.quantity), 0)).where(
            Transaction.ticket_tier_id == tier.id,
            Transaction.status.in_(
                (TransactionStatus.CONFIRMED, TransactionStatus.PENDING)
            ),
        )
    )
    return int(holds or 0)


def _refuse_if_user_already_buying(db: Session, user: User) -> None:
    """Refuse a second purchase: a ticket already exists, or a payment is in flight.

    Without this, a person who starts two payments and pays both is charged twice
    but can only hold one ticket (the unique index on ``tickets``), and the second
    confirmation fails after the money has moved.
    """
    has_ticket = db.scalar(
        select(Ticket.id)
        .where(
            Ticket.user_id == user.id, Ticket.payment_status != PaymentStatus.CANCELLED
        )
        .limit(1)
    )
    has_open_payment = db.scalar(
        select(Transaction.id)
        .where(
            Transaction.user_id == user.id,
            Transaction.status == TransactionStatus.PENDING,
        )
        .limit(1)
    )
    if has_ticket is not None or has_open_payment is not None:
        db.rollback()
        raise AlreadyHasTicketError(
            "You already have a ticket or a payment in progress"
        )


def _settle_pending(
    db: Session, transaction: Transaction, status: TransactionStatus
) -> None:
    """Move a pending transaction to ``failed`` or ``expired``.

    The row is locked and read again first: a callback may have confirmed the
    payment while we were talking to the provider, and a confirmed payment must
    never be overwritten by a stale ``expired`` or ``failed``.
    """
    db.refresh(transaction, with_for_update=True)
    if transaction.status is TransactionStatus.PENDING:
        transaction.status = status
    db.commit()
    db.refresh(transaction)
    notify(transaction.reference, transaction.status)


ABANDONED_CHECKS_PER_REQUEST = 10
# Shorter than the week a sent email stays in the queue (see delete_old_emails).
TICKET_EMAIL_SWEEP_DAYS = 3


def _free_abandoned_seats(
    db: Session, tier_name: TicketTier, gateway: MBWayGateway
) -> None:
    """Before refusing a sale for lack of stock, settle the payments nobody follows.

    A waiting payment holds its seat until the provider ends it. One that was
    abandoned (the person closed the page) is only settled when someone asks the
    provider, so when the modality looks full we ask about the oldest overdue ones
    first. Done outside any lock, a few at a time.
    """
    tier = db.scalar(select(TicketTierPrice).where(TicketTierPrice.tier == tier_name))
    if tier is None or tier.inventory_limit is None:
        return
    if tier.inventory_limit - _reserved_quantity(db, tier) >= 1:
        return
    overdue = db.scalars(
        select(Transaction)
        .where(
            Transaction.ticket_tier_id == tier.id,
            Transaction.status == TransactionStatus.PENDING,
            Transaction.expires_at <= datetime.now(UTC),
        )
        .order_by(Transaction.expires_at)
        .limit(ABANDONED_CHECKS_PER_REQUEST)
    ).all()
    for old in overdue:
        _sync_provider_status(db, old, gateway)


def payment_description(tier: TicketTier) -> str:
    """What the provider shows for the payment: ``ENEI - <product name>``.

    The Stripe account is shared with other events, so every charge has to say
    which event and which product it is for.
    """
    return f"ENEI - {TIER_SPECS[tier].name}"


def initiate_payment(
    db: Session,
    user: User,
    payload: PaymentInitiateRequest,
    gateway: MBWayGateway,
) -> tuple[Transaction, TicketTierPrice]:
    # A payment of this person that is past its deadline may already be over (or
    # paid) at the provider. Ask before deciding anything, outside any lock.
    user_id = user.id
    stale = db.scalars(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.status == TransactionStatus.PENDING,
            Transaction.expires_at <= datetime.now(UTC),
        )
    ).all()
    for old in stale:
        _sync_provider_status(db, old, gateway)
    _free_abandoned_seats(db, payload.ticket_tier, gateway)

    # One ticket per person. The user row is locked first so two simultaneous requests
    # from the same person cannot both pass the check below; the order (user, then
    # tier) is the same everywhere, so it cannot deadlock.
    db.scalar(select(User.id).where(User.id == user.id).with_for_update())
    _refuse_if_user_already_buying(db, user)

    # Lock the tier row so that the stock check and the reservation are a single
    # atomic step. Without it, two concurrent buyers of a limited tier can both read
    # the same remaining quantity and oversell the tier.
    tier = db.scalar(
        select(TicketTierPrice)
        .where(TicketTierPrice.tier == payload.ticket_tier)
        .with_for_update()
    )
    if tier is None:
        db.rollback()
        raise TicketUnavailableError("Ticket tier is not available")

    if tier.price_cents is None:
        db.rollback()
        raise TicketOfficeClosedError("Ticket sales are not open yet")

    if tier.is_student and (
        user.student_verification_status is not StudentVerificationStatus.VERIFIED
    ):
        db.rollback()
        raise StudentVerificationRequiredError(
            "Student verification is required to buy this ticket"
        )

    now = datetime.now(UTC)
    if tier.inventory_limit is not None:
        remaining = tier.inventory_limit - _reserved_quantity(db, tier)
        if remaining < payload.quantity:
            db.rollback()
            raise TicketSoldOutError("This ticket tier is sold out")

    amount_cents = tier.price_cents * payload.quantity
    transaction = Transaction(
        reference=generate_reference(db),
        user_id=user.id,
        ticket_tier_id=tier.id,
        amount_cents=amount_cents,
        quantity=payload.quantity,
        status=TransactionStatus.PENDING,
        phone=payload.phone,
        nif=payload.nif,
        provider=gateway.name,
        expires_at=now + timedelta(seconds=settings.MBWAY_PAYMENT_TIMEOUT_SECONDS),
    )
    db.add(transaction)
    # Persist the reservation before talking to the provider: the seat is held
    # while the user confirms, and the row lock is released without waiting on the
    # network call.
    db.commit()
    db.refresh(transaction)
    # The refresh opened a new read: end it so no connection waits on the provider
    # (with a slow one every request held its connection and the pool ran out).
    db.commit()

    try:
        payment = gateway.create_payment(
            reference=transaction.reference,
            amount_cents=amount_cents,
            phone=payload.phone,
            email=payload.email or user.email,
            description=payment_description(payload.ticket_tier),
        )
    except PaymentGatewayError:
        _settle_pending(db, transaction, TransactionStatus.FAILED)
        raise

    transaction.provider_reference = payment.provider_reference
    db.commit()
    db.refresh(transaction)
    return transaction, tier


def _holds_another_active_ticket(db: Session, transaction: Transaction) -> bool:
    return (
        db.scalar(
            select(Ticket.id)
            .where(
                Ticket.user_id == transaction.user_id,
                Ticket.payment_status != PaymentStatus.CANCELLED,
                Ticket.transaction_reference != transaction.reference,
            )
            .limit(1)
        )
        is not None
    )


def _has_room(db: Session, transaction: Transaction) -> bool:
    """Whether a payment that is not ``pending`` any more can still get its seat.

    A waiting payment always has its seat, so this is only asked for one that was
    marked ``failed`` or ``expired`` and is then paid after all (the provider
    answered in the meantime, or its creation reported an error that was not one).
    The seat was released, so the stock is checked again with the modality row
    locked, like ``initiate_payment`` does: we never sell what we do not have.
    """
    if transaction.status is TransactionStatus.PENDING:
        return True
    tier = db.scalar(
        select(TicketTierPrice)
        .where(TicketTierPrice.id == transaction.ticket_tier_id)
        .with_for_update()
    )
    if tier is None or tier.inventory_limit is None:
        return True
    return tier.inventory_limit - _reserved_quantity(db, tier) >= transaction.quantity


def _record_refund_due(
    db: Session, transaction: Transaction, reason: str
) -> Transaction:
    """The money arrived but there is no ticket to give: the payment is refunded.

    A last resort that should not happen: a waiting payment holds its seat and
    blocks a second payment of the same person. It can still follow an unexpected
    sequence (a payment marked ``failed`` that is paid after all, with the modality
    sold out meanwhile, or the person already holding a ticket). The payment is kept
    as ``refund_due``, which holds no stock, and logged loudly. List them with the
    query in ``docs/deploy.md``.
    """
    transaction.status = TransactionStatus.REFUND_DUE
    transaction.confirmed_at = transaction.confirmed_at or datetime.now(UTC)
    db.commit()
    db.refresh(transaction)
    notify(transaction.reference, transaction.status)
    logger.error(
        "Payment %s needs a refund: %s. Refund it by hand.",
        transaction.reference,
        reason,
    )
    return transaction


def confirm_transaction(db: Session, transaction: Transaction) -> Transaction:
    """Record a successful payment and issue its ticket.

    Single source of truth for "the payment went through": both the provider
    callback and the status poll go through here, so the ticket is issued no
    matter how the confirmation arrives. Idempotent: a repeated call returns the
    same transaction and never duplicates the ticket.

    The transaction row stays locked until the ticket is committed, so two
    confirmations of the same payment (poll and poll, or poll and callback) run one
    after the other. The status and the ticket are saved together. No ticket is
    issued, and the payment is kept for a refund, when the person already holds a
    ticket from another payment or when a late payment finds the modality sold out.
    """
    db.refresh(transaction, with_for_update=True)
    if transaction.status in (TransactionStatus.REFUND_DUE, TransactionStatus.REFUNDED):
        return transaction  # already decided: a repeated callback changes nothing

    if _holds_another_active_ticket(db, transaction):
        return _record_refund_due(db, transaction, "the person already has a ticket")

    if transaction.status is not TransactionStatus.CONFIRMED:
        if not _has_room(db, transaction):
            return _record_refund_due(db, transaction, "the modality sold out")
        transaction.status = TransactionStatus.CONFIRMED
        transaction.confirmed_at = datetime.now(UTC)

    try:
        ticket = issue_ticket_for_paid_transaction(
            db,
            user_id=transaction.user_id,
            transaction_reference=transaction.reference,
            ticket_tier=ticket_tier_of(db, transaction),
        )
    except IntegrityError:
        # Lost a race: either the same payment was confirmed by someone else in
        # the meantime, or the person's other payment got its ticket first.
        db.rollback()
        db.refresh(transaction)
        issued = db.scalar(
            select(Ticket.id).where(
                Ticket.transaction_reference == transaction.reference
            )
        )
        if issued is not None:
            return transaction
        if _holds_another_active_ticket(db, transaction):
            return _record_refund_due(
                db, transaction, "the person already has a ticket"
            )
        raise
    except PaymentNotConfirmedError:
        # The ticket of this payment was cancelled (a refund). A repeated callback
        # must not bring it back, and ifthenpay must stop retrying.
        db.commit()
        logger.warning(
            "Payment %s confirmed again but its ticket is cancelled; left as is",
            transaction.reference,
        )
        db.refresh(transaction)
        return transaction
    # Saves the status when the ticket already existed and nothing else committed.
    db.commit()
    db.refresh(transaction)
    _queue_ticket_email_best_effort(db, transaction, ticket)
    notify(transaction.reference, transaction.status)
    return transaction


def _queue_ticket_email_best_effort(
    db: Session, transaction: Transaction, ticket: Ticket
) -> None:
    """Queue the ticket email without ever failing the confirmation.

    By now the payment is confirmed and the ticket issued and committed: a failure
    of the queue, of the QR image or of the modality name must not turn into a 500
    (ifthenpay would keep retrying and the status poll would fail). The error is
    logged and ``queue_missing_ticket_emails`` queues the email on its next run.
    """
    try:
        _queue_ticket_email(db, transaction, ticket)
    except Exception:
        db.rollback()
        logger.exception(
            "Could not queue the ticket email of payment %s; the sweep will retry",
            transaction.reference,
        )
        db.refresh(transaction)


def queue_missing_ticket_emails(
    db: Session, *, paid_within_days: int = TICKET_EMAIL_SWEEP_DAYS
) -> int:
    """Queue the email of recent paid tickets that have none; returns how many.

    Safe to run any time: the dedupe key stops a second email for the same ticket.
    Only tickets paid in the last ``paid_within_days`` are considered, because the
    queue deletes sent emails after a week and an older ticket would otherwise get
    its email again.
    """
    since = datetime.now(UTC) - timedelta(days=paid_within_days)
    queued = select(EmailOutbox.dedupe_key).where(EmailOutbox.dedupe_key.is_not(None))
    tickets = db.scalars(
        select(Ticket).where(
            Ticket.payment_status == PaymentStatus.PAID,
            Ticket.qr_payload.is_not(None),
            Ticket.paid_at >= since,
            ("ticket:" + cast(Ticket.id, String)).not_in(queued),
        )
    ).all()
    count = 0
    for ticket in tickets:
        transaction = db.scalar(
            select(Transaction).where(
                Transaction.reference == ticket.transaction_reference
            )
        )
        if transaction is None:
            continue
        try:
            _queue_ticket_email(db, transaction, ticket)
            count += 1
        except Exception:
            db.rollback()
            logger.exception("Sweep could not queue the email of ticket %s", ticket.id)
    return count


def _queue_ticket_email(db: Session, transaction: Transaction, ticket: Ticket) -> None:
    """Queue the email with the ticket QR, once per ticket.

    The dedupe key makes a repeated callback or poll a no-op. The ticket row is
    locked first: the transaction lock is gone once the ticket is
    committed, and two confirmations of the same payment must not both try to queue
    the email at once.
    """
    db.scalar(select(Ticket.id).where(Ticket.id == ticket.id).with_for_update())
    user = db.get(User, transaction.user_id)
    tier_name = TIER_SPECS[ticket_tier_of(db, transaction)].name
    html, text = build_ticket_email(user.name, tier_name, transaction.reference)
    enqueue_email(
        db,
        user.email,
        TICKET_EMAIL_SUBJECT,
        html,
        text_body=text,
        inline_images={TICKET_QR_CID: render_qr_png(ticket.qr_payload)},
        dedupe_key=f"ticket:{ticket.id}",
    )


_asked_at: dict[str, float] = {}
_asked_lock = threading.Lock()
_clock = time.monotonic  # replaced in tests


def _should_ask_provider(key: str) -> bool:
    """Whether the provider may be asked about ``key`` now.

    At most one question per payment every ``PAYMENT_PROVIDER_MIN_INTERVAL_SECONDS``.
    The memory is per process (the backend runs one), so with more processes each
    would ask on its own. Skipping a question never changes a payment: it stays as it
    is until the next one, or until the callback arrives.
    """
    interval = settings.PAYMENT_PROVIDER_MIN_INTERVAL_SECONDS
    if interval <= 0:
        return True
    now = _clock()
    with _asked_lock:
        last = _asked_at.get(key)
        if last is not None and now - last < interval:
            return False
        _asked_at[key] = now
        if len(_asked_at) > 4096:  # forget what is long past
            for old_key, asked in list(_asked_at.items()):
                if now - asked > 10 * interval:
                    del _asked_at[old_key]
    return True


def _sync_provider_status(
    db: Session, transaction: Transaction, gateway: MBWayGateway
) -> None:
    """Ask the provider for the real state of a pending payment and persist it.

    The provider is the source of truth: a confirmed payment must reach the
    frontend even if the local ``expires_at`` window already passed, and a
    failed/expired one must not stay ``pending``. A payment the provider still
    reports as waiting stays ``pending`` and keeps its seat, even past its local
    deadline (``expires_at`` is the time the person has to approve, not the moment
    the seat is released). When the gateway is unreachable the answer is unknown, so
    the payment also stays ``pending`` and the poll keeps working. A payment the
    provider cannot resolve (no reference, or an unreadable answer) is expired a long
    time after its deadline so that it does not hold its seat for ever.
    """
    reference = transaction.reference
    provider = transaction.provider
    provider_reference = transaction.provider_reference
    expires_at = _as_utc(transaction.expires_at)
    # Release the pooled database connection before the network call: a slow
    # provider must not keep a connection busy while we wait for its answer.
    db.commit()

    if not provider_reference and provider == "stripe":
        provider_reference = _recover_provider_reference(db, reference, gateway)

    if provider_reference and not _should_ask_provider(reference):
        return  # asked a moment ago: nothing can have changed that the callback misses

    # "Unresolved" means the provider could not tell us: we never saved its reference,
    # or it answered something we cannot read. (An unreachable provider is not
    # unresolved: it is an outage, and the payments stay as they are.)
    unresolved = False
    provider_status = TransactionStatus.PENDING
    if not provider_reference:
        unresolved = True
        logger.warning("Payment %s has no provider reference to ask about", reference)
    else:
        try:
            provider_status = gateway.get_status(
                reference=reference,
                provider_reference=provider_reference,
            )
        except UnrecognisedStatusError:
            unresolved = True
        except PaymentGatewayError:
            logger.warning(
                "MB WAY status poll failed for %s; keeping stored status",
                reference,
            )

    if provider_status is TransactionStatus.PENDING:
        if _cancel_if_overdue(
            db,
            transaction,
            gateway,
            reference=reference,
            provider=provider,
            provider_reference=provider_reference,
            expires_at=expires_at,
        ):
            return
        # Still waiting, whatever the local deadline says: only the provider can end
        # a payment, and until then it keeps its seat. The one exception is a payment
        # the provider cannot resolve for a long time: it would hold its seat for ever.
        limit = timedelta(seconds=settings.MBWAY_UNRESOLVED_MAX_WAIT_SECONDS)
        if unresolved and expires_at + limit < datetime.now(UTC):
            logger.error(
                "Payment %s could not be resolved with the provider for over %s s "
                "after its deadline: expired. If it was paid, it needs a look.",
                reference,
                settings.MBWAY_UNRESOLVED_MAX_WAIT_SECONDS,
            )
            _settle_pending(db, transaction, TransactionStatus.EXPIRED)
        return
    if provider_status is TransactionStatus.CONFIRMED:
        confirm_transaction(db, transaction)
        return

    _settle_pending(db, transaction, provider_status)


def _recover_provider_reference(
    db: Session, reference: str, gateway: MBWayGateway
) -> str | None:
    """Find a Stripe payment whose id we never saved, and save it.

    It happens when Stripe created the payment but the answer got lost (a timeout):
    the person may well approve it. Without the id the payment cannot be read,
    cancelled or refunded, so it is looked up by its reference. The search can lag
    a little behind a new payment: "not found yet" changes nothing and the next look
    tries again. Asked at most as often as any other question to the provider.
    """
    if not isinstance(gateway, LookupGateway) or not _should_ask_provider(
        f"find:{reference}"
    ):
        return None
    try:
        found = gateway.find_payment(reference=reference)
    except PaymentGatewayError:
        logger.warning("Payment %s could not be looked up at Stripe", reference)
        return None
    if found is None:
        return None
    transaction = db.scalar(
        select(Transaction).where(Transaction.reference == reference).with_for_update()
    )
    if transaction is None or transaction.provider_reference not in (None, found):
        db.rollback()
        return None
    if transaction.provider_reference is None:
        transaction.provider_reference = found
        logger.warning(
            "Payment %s had no Stripe id (the answer to its creation was lost): "
            "found it by its reference",
            reference,
        )
    db.commit()
    return found


def _cancel_if_overdue(
    db: Session,
    transaction: Transaction,
    gateway: MBWayGateway,
    *,
    reference: str,
    provider: str,
    provider_reference: str | None,
    expires_at: datetime,
) -> bool:
    """End, at Stripe, a payment that still waits past its deadline plus a grace.

    Stripe ends the MB WAY wait by itself; this is the backstop for when it does not,
    so that a payment cannot hold its seat, or be approved, for ever. A payment the
    person approved at that very moment is confirmed, never expired. When Stripe
    cannot be asked the payment stays as it is. Returns whether it was settled.
    """
    if (
        provider != "stripe"
        or not provider_reference
        or not isinstance(gateway, CancellingGateway)
    ):
        return False
    grace = timedelta(seconds=settings.STRIPE_CANCEL_GRACE_SECONDS)
    if datetime.now(UTC) < expires_at + grace:
        return False
    try:
        outcome = gateway.cancel_payment(
            reference=reference, provider_reference=provider_reference
        )
    except PaymentGatewayError:
        logger.warning(
            "Stripe payment %s is past its deadline and could not be cancelled; "
            "keeping stored status",
            reference,
        )
        return False
    if outcome is TransactionStatus.CONFIRMED:
        confirm_transaction(db, transaction)
    else:
        logger.info("Stripe payment %s cancelled after its deadline", reference)
        _settle_pending(db, transaction, TransactionStatus.EXPIRED)
    return True


def refresh_pending_payment(db: Session, reference: str, gateway: MBWayGateway) -> None:
    """Ask the provider about a payment somebody is waiting for and persist the answer.

    Used by the live status stream: when the provider reports a change the payment is
    updated (and the streams are told) without anyone polling. Throttled like a poll.
    """
    transaction = db.scalar(
        select(Transaction).where(Transaction.reference == reference)
    )
    if transaction is not None and transaction.status is TransactionStatus.PENDING:
        _sync_provider_status(db, transaction, gateway)


def cancel_ticket(db: Session, ticket_id: int) -> Ticket:
    """Cancel a ticket and free its seat: the payment becomes ``refunded``.

    The caller refunds the money (the gateway, or by hand). The person can buy again,
    and the seat counts as free for the next buyer. Idempotent. The transaction is
    locked before the ticket, the same order as ``confirm_transaction``, so a
    repeated callback arriving at the same time cannot deadlock with it.
    """
    reference = db.scalar(
        select(Ticket.transaction_reference).where(Ticket.id == ticket_id)
    )
    if reference is None:
        raise TicketNotFoundError(f"Ticket {ticket_id} not found")
    transaction = db.scalar(
        select(Transaction).where(Transaction.reference == reference).with_for_update()
    )
    ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update())
    if ticket.payment_status is not PaymentStatus.CANCELLED:
        ticket.payment_status = PaymentStatus.CANCELLED
        if (
            transaction is not None
            and transaction.status is TransactionStatus.CONFIRMED
        ):
            transaction.status = TransactionStatus.REFUNDED
        db.commit()
        db.refresh(ticket)
        if transaction is not None:
            notify(transaction.reference, transaction.status)
    return ticket


def refund_payment(db: Session, reference: str, gateway: MBWayGateway) -> Transaction:
    """Give the money of a payment back and close it: ``refunded``.

    For a ``refund_due`` (it arrived and there is no ticket to give) and for a
    ``confirmed`` payment whose ticket is being cancelled: the ticket of THIS payment
    is cancelled and its seat freed (a ticket of the same person from another payment
    is never touched). Repeating it changes nothing: a payment already ``refunded``
    returns at once, and the provider gets an idempotency key, so even a failure
    between the refund and the database leaves nothing to redo but run it again.
    The log has the reference and the amount, never anything about the person.
    """
    transaction = db.scalar(
        select(Transaction).where(Transaction.reference == reference)
    )
    if transaction is None:
        raise NothingToRefundError("Unknown transaction reference")
    if transaction.status is TransactionStatus.REFUNDED:
        return transaction
    if transaction.status not in (
        TransactionStatus.REFUND_DUE,
        TransactionStatus.CONFIRMED,
    ):
        raise NothingToRefundError(
            f"A {transaction.status.value} payment has nothing to refund"
        )
    provider_reference = transaction.provider_reference
    amount_cents = transaction.amount_cents
    description = payment_description(ticket_tier_of(db, transaction))
    if (
        transaction.provider != gateway.name
        or not provider_reference
        or not isinstance(gateway, RefundingGateway)
    ):
        raise RefundNotSupportedError(
            f"A {transaction.provider} payment cannot be refunded here: "
            "refund it in the provider's own panel"
        )
    # No lock during the network call: the refund is idempotent, so nobody is hurt if
    # something else touches the row meanwhile.
    db.commit()
    try:
        refund_id = gateway.refund(
            reference=reference,
            provider_reference=provider_reference,
            amount_cents=amount_cents,
            description=description,
        )
    except AlreadyRefundedError:
        refund_id = "already refunded at the provider"

    db.refresh(transaction, with_for_update=True)
    if transaction.status is not TransactionStatus.REFUNDED:
        ticket_id = db.scalar(
            select(Ticket.id).where(
                Ticket.transaction_reference == reference,
                Ticket.payment_status != PaymentStatus.CANCELLED,
            )
        )
        if ticket_id is not None and transaction.status is TransactionStatus.CONFIRMED:
            cancel_ticket(db, ticket_id)  # also makes the payment ``refunded``
        if transaction.status is not TransactionStatus.REFUNDED:
            transaction.status = TransactionStatus.REFUNDED
            db.commit()
        db.refresh(transaction)
        notify(reference, transaction.status)
    logger.info(
        "Payment %s refunded (%d cents, refund %s)", reference, amount_cents, refund_id
    )
    return transaction


def refundable_references(db: Session) -> list[str]:
    """The payments waiting for a refund, oldest first."""
    return list(
        db.scalars(
            select(Transaction.reference)
            .where(Transaction.status == TransactionStatus.REFUND_DUE)
            .order_by(Transaction.confirmed_at, Transaction.id)
        )
    )


def handle_payment_callback(
    db: Session,
    *,
    key: str | None,
    reference: str | None,
    amount: str | None,
) -> Transaction:
    """Apply an ifthenpay payment callback to a transaction.

    Trust only callbacks that carry our anti-phishing key, and only confirm a
    payment whose value matches what was charged. ifthenpay only calls this when
    the money has been paid, so a callback for a transaction that already
    ``failed`` or ``expired`` locally is a late payment: it is confirmed like any
    other (the person paid and gets the ticket) and logged, unless the modality sold
    out meanwhile or the person already has a ticket: ``confirm_transaction`` then
    keeps the payment as ``refund_due`` for a manual refund. Idempotent: a repeated
    callback returns the same transaction and never duplicates the ticket.
    """
    if not _callback_key_matches(key):
        raise InvalidCallbackKeyError("Invalid callback key")

    if not reference:
        raise CallbackTransactionNotFoundError("Missing transaction reference")

    transaction = db.scalar(
        select(Transaction).where(Transaction.reference == reference).with_for_update()
    )
    if transaction is None:
        raise CallbackTransactionNotFoundError("Unknown transaction reference")

    if transaction.provider == "stripe":
        # A Stripe payment is only ever confirmed by reading it from Stripe: the
        # ifthenpay key must not be able to settle it, whatever is configured.
        raise CallbackTransactionNotFoundError("Unknown transaction reference")

    if not _callback_amount_matches(amount, transaction.amount_cents):
        raise CallbackAmountMismatchError(
            "Callback amount does not match the transaction"
        )

    if transaction.status in (TransactionStatus.FAILED, TransactionStatus.EXPIRED):
        logger.warning(
            "Late MB WAY payment for %s: the transaction was %s locally",
            transaction.reference,
            transaction.status.value,
        )

    return confirm_transaction(db, transaction)


_STRIPE_PAYMENT_EVENTS = {
    "payment_intent.succeeded",
    "payment_intent.payment_failed",
    "payment_intent.canceled",
}


def handle_stripe_event(db: Session, event: dict) -> None:
    """Apply a Stripe webhook event (already checked for its signature).

    Only the three PaymentIntent events matter; anything else is ignored so Stripe
    gets its 200 and stops sending it. The event says which payment it is about
    through the reference we put in the PaymentIntent's metadata, and it only counts
    when that payment is one of ours made through Stripe. ``succeeded`` confirms like
    the status poll (and, like the ifthenpay callback, also a payment we had already
    given up on: ``confirm_transaction`` then issues the ticket or keeps it for a
    refund); it needs the amount Stripe received to be what we charged, in euros.
    ``payment_failed`` and ``canceled`` only end a payment that is still waiting.
    Idempotent: Stripe repeats events, and a repeat changes nothing.
    """
    kind = event.get("type")
    intent = (event.get("data") or {}).get("object")
    if kind not in _STRIPE_PAYMENT_EVENTS or not isinstance(intent, dict):
        return
    reference = (intent.get("metadata") or {}).get("reference")
    intent_id = intent.get("id")
    if not isinstance(reference, str) or not isinstance(intent_id, str):
        return

    transaction = db.scalar(
        select(Transaction).where(Transaction.reference == reference).with_for_update()
    )
    # A payment whose answer from Stripe came back before we saved its id has no
    # provider reference yet: the signed reference identifies it.
    if (
        transaction is None
        or transaction.provider != "stripe"
        or transaction.provider_reference not in (None, intent_id)
    ):
        db.rollback()
        logger.warning("Stripe event %s ignored: not one of our payments", kind)
        return
    if transaction.provider_reference is None:
        transaction.provider_reference = intent_id
        db.flush()  # the helpers below refresh the row and would drop an unsaved change

    if kind == "payment_intent.succeeded":
        received = intent.get("amount_received")
        if intent.get("currency") != "eur" or received != transaction.amount_cents:
            db.rollback()
            logger.error(
                "Stripe payment %s succeeded for another amount than charged "
                "(%r %r instead of %d EUR cents): not confirmed, needs a look",
                transaction.reference,
                received,
                intent.get("currency"),
                transaction.amount_cents,
            )
            return
        if transaction.status in (TransactionStatus.FAILED, TransactionStatus.EXPIRED):
            logger.warning(
                "Late Stripe payment for %s: the transaction was %s locally",
                transaction.reference,
                transaction.status.value,
            )
        confirm_transaction(db, transaction)
        return

    try:
        ended = stripe_status(intent)
    except UnrecognisedStatusError:
        db.rollback()
        return
    if ended in (TransactionStatus.FAILED, TransactionStatus.EXPIRED):
        _settle_pending(db, transaction, ended)
    else:
        db.rollback()


def get_transaction(
    db: Session, user: User, reference: str, gateway: MBWayGateway
) -> Transaction | None:
    transaction = db.scalar(
        select(Transaction).where(
            Transaction.reference == reference,
            Transaction.user_id == user.id,
        )
    )
    if transaction is None:
        return None

    if transaction.status is TransactionStatus.PENDING:
        _sync_provider_status(db, transaction, gateway)

    return transaction


def account_payment_overview(db: Session, user: User) -> dict:
    """What the account page needs to know about the person's purchase.

    The active ticket (with its modality), the payment that is waiting, and a payment
    that arrived without a ticket and will be refunded. Each is ``None`` if absent.
    """
    ticket = db.execute(
        select(Ticket, TicketTierPrice)
        .join(Transaction, Transaction.reference == Ticket.transaction_reference)
        .join(TicketTierPrice, TicketTierPrice.id == Transaction.ticket_tier_id)
        .where(
            Ticket.user_id == user.id,
            Ticket.payment_status == PaymentStatus.PAID,
        )
        .order_by(Ticket.id.desc())
        .limit(1)
    ).first()
    waiting = db.execute(
        select(Transaction, TicketTierPrice)
        .join(TicketTierPrice, TicketTierPrice.id == Transaction.ticket_tier_id)
        .where(
            Transaction.user_id == user.id,
            Transaction.status == TransactionStatus.PENDING,
        )
        .order_by(Transaction.id.desc())
        .limit(1)
    ).first()
    refund = db.scalar(
        select(Transaction)
        .where(
            Transaction.user_id == user.id,
            Transaction.status == TransactionStatus.REFUND_DUE,
        )
        .order_by(Transaction.id.desc())
        .limit(1)
    )
    return {
        "ticket": None
        if ticket is None
        else {
            "reference": ticket[0].transaction_reference,
            "tier": ticket[1].tier.value,
            "tier_name": ticket[1].name,
            "holder_name": user.name,
            "paid_at": ticket[0].paid_at,
        },
        "pending_payment": None
        if waiting is None
        else {
            "reference": waiting[0].reference,
            "tier": waiting[1].tier.value,
            "tier_name": waiting[1].name,
            "amount_cents": waiting[0].amount_cents,
            "expires_at": waiting[0].expires_at,
        },
        "refund_due": None
        if refund is None
        else {"reference": refund.reference, "amount_cents": refund.amount_cents},
    }


def list_ticket_tiers(db: Session) -> list[TicketTierRead]:
    """The modalities with their price and whether each can be bought right now.

    ``sale_open`` is false while payments are off or the modality has no price.
    ``available`` is also false when every seat is taken or reserved for a payment
    that is waiting. Read-only: it does not ask the provider about anything.
    """
    order = {tier: index for index, tier in enumerate(TicketTier)}
    rows = sorted(db.scalars(select(TicketTierPrice)), key=lambda r: order[r.tier])
    payments_on = settings.PAYMENTS_MODE != "off"
    result = []
    for row in rows:
        sale_open = payments_on and row.price_cents is not None
        has_room = row.inventory_limit is None or (
            row.inventory_limit - _reserved_quantity(db, row) >= 1
        )
        result.append(
            TicketTierRead(
                tier=row.tier,
                name=row.name,
                price_cents=row.price_cents,
                is_student=row.is_student,
                sale_open=sale_open,
                available=sale_open and has_room,
            )
        )
    return result


def ticket_tier_of(db: Session, transaction: Transaction) -> TicketTier:
    return db.scalar(
        select(TicketTierPrice.tier).where(
            TicketTierPrice.id == transaction.ticket_tier_id
        )
    )


def to_read(db: Session, transaction: Transaction) -> TransactionRead:
    tier = ticket_tier_of(db, transaction)
    return TransactionRead(
        reference=transaction.reference,
        ticket_tier=tier,
        status=transaction.status,
        amount_cents=transaction.amount_cents,
        quantity=transaction.quantity,
        phone=transaction.phone,
        expires_at=transaction.expires_at,
        confirmed_at=transaction.confirmed_at,
        created_at=transaction.created_at,
    )
